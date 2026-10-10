# File: views/wizard_pages.py
# Purpose: Wizard UI pages for the lawsuit application
# Encoding: UTF-8

import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QRadioButton, QButtonGroup, QTextEdit, QGroupBox, QHBoxLayout, QPushButton, QScrollArea, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QRegularExpressionValidator

# Phone input accepts only digits and the common grouping/prefix characters so
# that obviously invalid text (letters, brackets, etc.) cannot be entered. The
# precise digit-count check happens in PartyPage.validate_parties() so that a
# legitimate landline or extension is not rejected outright.
_PHONE_INPUT_PATTERN = QRegularExpression(r"^[0-9+\-() ]{0,20}$")

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用民事立案文书助手")

        layout = QVBoxLayout()
        desc = ("本工具将引导您生成规范的民事起诉状。\n\n"
                "【本地离线说明】\n"
                "版本号：v1.0.0（离线版）\n"
                "内置参考信息日期：2026年3月\n\n"
                "软件特点：\n"
                "- 本地运行：案件信息仅在本机处理，生成 Word 文书时不联网上传\n"
                "- 启动时检测默认网络路由并给出提示，该提示只是辅助提醒，不等同于系统级网络隔离\n"
                "- 生成完成后对内存中的敏感字段执行尽力清理（Python 无法保证彻底、不可恢复地销毁）\n\n"
                "点击“下一步”开始填写。")
        label = QLabel(desc)
        label.setWordWrap(True)
        layout.addWidget(label)

        warning_label = QLabel("【重要提示】劳动报酬/工资追索案件，在直接起诉前通常需先经过劳动仲裁程序。本工具生成的起诉状可直接用于劳动仲裁或法院诉讼。")
        warning_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 10px; background-color: #FFF3E0; border: 1px solid #FF9800;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        self.setLayout(layout)

        # 添加一键填写模板按钮
        from PySide6.QtWidgets import QPushButton
        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        layout.addWidget(self.fill_btn)

class CaseSelectionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第 0 步：选择案件类型")

        layout = QVBoxLayout()
        label = QLabel("请选择您要生成的起诉状案由：")
        layout.addWidget(label)

        from PySide6.QtWidgets import QComboBox
        self.case_combo = QComboBox()
        self.case_combo.addItem("民间借贷纠纷", "loan")
        self.case_combo.addItem("买卖合同纠纷", "contract")
        self.case_combo.addItem("物业服务合同纠纷", "property")
        self.case_combo.addItem("劳动报酬/工资追索", "labor")
        self.case_combo.addItem("离婚纠纷", "divorce")

        layout.addWidget(self.case_combo)

        warning_label = QLabel("注意：请根据实际情况选择案由，不同案由需要填写的表单不同。")
        warning_label.setStyleSheet("color: gray;")
        layout.addWidget(warning_label)

        self.setLayout(layout)

        self.labor_warning_shown = False

        from utils.labor_security import LaborProcedureGuard
        self.labor_guard = LaborProcedureGuard()
        self.case_combo.currentTextChanged.connect(self._on_case_type_changed)

        self.registerField("case_type", self.case_combo, "currentData")

    def _on_case_type_changed(self, text):
        case_data = self.case_combo.currentData()
        if case_data == "labor" and not self.labor_warning_shown:
            from PySide6.QtWidgets import QMessageBox
            msg = self.labor_guard.get_warning_text()
            QMessageBox.warning(self, "法律程序风险提示", msg)
            self.labor_warning_shown = True
            return True
        return False

class PartyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第一步：填写当事人信息")

        main_layout = QVBoxLayout()

        # Live validation / guidance message for the party list.
        self.msg_label = QLabel("")
        self.msg_label.setStyleSheet("color: #B00020;")
        self.msg_label.setWordWrap(True)
        main_layout.addWidget(self.msg_label)

        # Setup Scroll Area for dynamic lists
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        # Containers for dynamic fields
        self.plaintiff_widgets = []
        self.defendant_widgets = []

        # Store credit_code_edit and legal_rep_edit as instance variables
        self.credit_code_edit = None
        self.legal_rep_edit = None

        # Store current case type
        self.current_case_type = None

        # Flag to prevent multiple initialization
        self.is_initialized = False

        # Add Plaintiff Button
        self.add_p_btn = QPushButton("[+] 添加原告")
        self.add_p_btn.clicked.connect(lambda: self.add_party_ui(0))
        self.scroll_layout.addWidget(self.add_p_btn)

        # Add Defendant Button
        self.add_d_btn = QPushButton("[+] 添加被告")
        self.add_d_btn.clicked.connect(lambda: self.add_party_ui(1))
        self.scroll_layout.addWidget(self.add_d_btn)

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

    def initializePage(self):
        """Called when the page is shown, recreate UI based on selected case type"""
        case_type = self.field("case_type")

        # Only recreate UI if case type has changed or not initialized yet
        if self.is_initialized and self.current_case_type == case_type:
            return

        # Clear existing widgets if they exist
        for widget in self.plaintiff_widgets:
            widget["group"].deleteLater()
        for widget in self.defendant_widgets:
            widget["group"].deleteLater()

        self.plaintiff_widgets.clear()
        self.defendant_widgets.clear()

        # Update current case type
        self.current_case_type = case_type
        self.is_initialized = True

        # Initialize with at least 1 plaintiff and 1 defendant
        self.add_party_ui(0)
        self.add_party_ui(1)

    def add_party_ui(self, party_type):
        is_plaintiff = (party_type == 0)
        title = "原告信息" if is_plaintiff else "被告信息"
        group = QGroupBox(title)
        layout = QFormLayout()

        name_edit = QLineEdit()
        id_edit = QLineEdit()
        addr_edit = QLineEdit()
        phone_edit = QLineEdit()

        from PySide6.QtWidgets import QCheckBox, QLabel
        is_company_check = QCheckBox("是企业法人（物业公司/公司等）")
        is_company_check.setChecked(False)

        # Company-specific widgets are always created so that a corporate party
        # works for every case type and the extraction code never touches a
        # ``None`` widget. They stay hidden until the checkbox is ticked.
        case_type = self.field("case_type")
        is_property_case = (case_type == "property")

        credit_code_edit = QLineEdit()
        credit_code_edit.setPlaceholderText("统一社会信用代码")
        credit_code_edit.setVisible(False)

        legal_rep_edit = QLineEdit()
        legal_rep_edit.setPlaceholderText("法定代表人姓名")
        legal_rep_edit.setVisible(False)

        is_company_check.toggled.connect(lambda checked: self._toggle_company_fields(checked, credit_code_edit, legal_rep_edit))

        layout.addRow("姓名/名称:", name_edit)
        layout.addRow("身份证号/统一社会信用代码:", id_edit)
        layout.addRow("住址/住所地:", addr_edit)
        layout.addRow("电话:", phone_edit)

        phone_validator = QRegularExpressionValidator(_PHONE_INPUT_PATTERN)
        phone_edit.setValidator(phone_validator)

        # Keep the live guidance and the wizard "Next" button state in sync.
        name_edit.textChanged.connect(lambda _text: self._refresh_validation_message())
        phone_edit.textChanged.connect(lambda _text: self._refresh_validation_message())
        credit_code_edit.textChanged.connect(lambda _text: self._refresh_validation_message())

        # Only create addr_hint for property cases
        if is_property_case and not is_plaintiff:
            from PySide6.QtWidgets import QLabel
            addr_hint = QLabel("提示：若被告搬家，请填写现居住满一年的地址，以便法院送达。")
            addr_hint.setStyleSheet("color: #FF9800; font-size: 11px;")
            layout.addRow("", addr_hint)

        layout.addRow("", is_company_check)
        if credit_code_edit is not None:
            layout.addRow("统一社会信用代码:", credit_code_edit)
        if legal_rep_edit is not None:
            layout.addRow("法定代表人:", legal_rep_edit)

        group.setLayout(layout)

        # Insert before the add buttons or stretch
        if is_plaintiff:
            idx = len(self.plaintiff_widgets)
            # Remove previous group if it exists to allow dynamic add/remove
            # For simplicity in this demo, we just append
            insert_idx = self.scroll_layout.indexOf(self.add_p_btn)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.plaintiff_widgets.append({
                "group": group,
                "name": name_edit,
                "id": id_edit,
                "addr": addr_edit,
                "phone": phone_edit,
                "is_company": is_company_check,
                "credit_code": credit_code_edit,
                "legal_rep": legal_rep_edit
            })
        else:
            idx = len(self.defendant_widgets)
            insert_idx = self.scroll_layout.indexOf(self.add_d_btn)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.defendant_widgets.append({
                "group": group,
                "name": name_edit,
                "id": id_edit,
                "addr": addr_edit,
                "phone": phone_edit,
                "is_company": is_company_check,
                "credit_code": credit_code_edit,
                "legal_rep": legal_rep_edit
            })

        self._refresh_validation_message()

    def _toggle_company_fields(self, checked, credit_code_edit, legal_rep_edit):
        if credit_code_edit is not None:
            credit_code_edit.setVisible(checked)
        if legal_rep_edit is not None:
            legal_rep_edit.setVisible(checked)
        self._refresh_validation_message()

    @staticmethod
    def _widget_text(widget):
        """Safely read a widget's text, returning ``""`` for missing widgets."""
        return widget.text() if widget is not None else ""

    def _iter_parties(self):
        """Yield ``(kind, index, widgets)`` for every plaintiff and defendant."""
        for idx, w in enumerate(self.plaintiff_widgets, 1):
            yield "原告", idx, w
        for idx, w in enumerate(self.defendant_widgets, 1):
            yield "被告", idx, w

    def _has_named_party(self, widgets):
        return any(self._widget_text(w["name"]).strip() for w in widgets)

    def isComplete(self):
        """Require at least one named plaintiff and one named defendant.

        This prevents the export flow from silently dropping incomplete parties
        and producing a document that only reflects part of the case.
        """
        return (
            self._has_named_party(self.plaintiff_widgets)
            and self._has_named_party(self.defendant_widgets)
        )

    def validate_parties(self):
        """Return a list of human-readable party-input issues.

        Missing required parties come first; softer format warnings (phone or
        unified social credit code) follow. The intention is to warn, not to
        reject legitimately optional or unavailable information.
        """
        issues = []

        if not self._has_named_party(self.plaintiff_widgets):
            issues.append("请至少填写一名原告的姓名/名称。")
        if not self._has_named_party(self.defendant_widgets):
            issues.append("请至少填写一名被告的姓名/名称。")

        for kind, idx, w in self._iter_parties():
            name = self._widget_text(w["name"]).strip()
            if not name:
                issues.append(f"{kind}{idx}的姓名/名称不能为空。")
                continue

            phone = self._widget_text(w["phone"]).strip()
            if phone:
                digits = re.sub(r"\D", "", phone)
                if not 7 <= len(digits) <= 15:
                    issues.append(f"{kind}{idx}“{name}”的电话号码位数可能不正确，建议核对（仅提示，不阻止生成）。")

            if w["is_company"].isChecked():
                code = self._widget_text(w["credit_code"]).strip()
                if code and not re.fullmatch(r"[0-9A-HJ-NPQRTUWXY]{18}", code):
                    issues.append(f"{kind}{idx}“{name}”的统一社会信用代码格式可能不正确，建议核对（仅提示，不阻止生成）。")

        return issues

    def _refresh_validation_message(self):
        issues = self.validate_parties()
        self.msg_label.setText("\n".join(issues))
        # Notify the wizard so the "Next" button reflects the current state.
        self.completeChanged.emit()

    def get_party_data(self):
        """Extract all party data to pass to presenter.

        Company-specific widgets are always present, but extraction is written
        defensively so that an absent widget can never raise.
        """
        def build(widgets):
            result = []
            for w in widgets:
                result.append({
                    "name": self._widget_text(w["name"]),
                    "id_number": self._widget_text(w["id"]),
                    "address": self._widget_text(w["addr"]),
                    "phone": self._widget_text(w["phone"]),
                    "is_company": w["is_company"].isChecked(),
                    "credit_code": self._widget_text(w["credit_code"]),
                    "legal_representative": self._widget_text(w["legal_rep"]),
                })
            return result

        return {
            "plaintiffs": build(self.plaintiff_widgets),
            "defendants": build(self.defendant_widgets),
        }

class ContractClaimPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第二步：填写事实与理由 (买卖合同)")

        layout = QFormLayout()

        self.contract_date = QLineEdit()
        self.contract_date.setPlaceholderText("如: 2023年1月1日")

        self.contract_name = QLineEdit()
        self.contract_name.setPlaceholderText("如: 产品购销合同")

        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("如: 10台联想电脑")

        self.total_amount = QLineEdit()
        self.total_amount.setPlaceholderText("如: 50000")

        self.delivery_date = QLineEdit()
        self.delivery_date.setPlaceholderText("如: 2023年2月1日")

        # Delivery status is tri-state: an explicit "未确认" option is selected by
        # default so an untouched control means UNKNOWN, never "delivered".
        self.is_delivered_group = QButtonGroup(self)
        self.del_yes = QRadioButton("已交货")
        self.del_no = QRadioButton("未交货")
        self.del_unknown = QRadioButton("未确认")
        self.is_delivered_group.addButton(self.del_yes, 1)
        self.is_delivered_group.addButton(self.del_no, 0)
        self.is_delivered_group.addButton(self.del_unknown, 2)
        self.del_unknown.setChecked(True)
        del_layout = QHBoxLayout()
        del_layout.addWidget(self.del_yes)
        del_layout.addWidget(self.del_no)
        del_layout.addWidget(self.del_unknown)

        # Receipt status is tri-state as well. The negative option is a neutral
        # "未签收": a missing signature is not proof of an intentional refusal.
        self.is_signed_group = QButtonGroup(self)
        self.sign_yes = QRadioButton("已签收")
        self.sign_no = QRadioButton("未签收")
        self.sign_unknown = QRadioButton("未确认")
        self.is_signed_group.addButton(self.sign_yes, 1)
        self.is_signed_group.addButton(self.sign_no, 0)
        self.is_signed_group.addButton(self.sign_unknown, 2)
        self.sign_unknown.setChecked(True)
        sign_layout = QHBoxLayout()
        sign_layout.addWidget(self.sign_yes)
        sign_layout.addWidget(self.sign_no)
        sign_layout.addWidget(self.sign_unknown)

        self.unpaid_amount = QLineEdit()
        self.unpaid_amount.setPlaceholderText("如: 30000")

        self.penalty_amount = QLineEdit()
        self.penalty_amount.setPlaceholderText("如: 5000 (留空表示无)")

        self.penalty_warning = QLabel("")
        self.penalty_warning.setStyleSheet("color: red;")
        self.penalty_amount.textChanged.connect(self.update_penalty_warning)

        self.overdue_start = QLineEdit()
        self.overdue_start.setPlaceholderText("逾期起算日(YYYY-MM-DD)")

        self.overdue_end = QLineEdit()
        self.overdue_end.setPlaceholderText("起诉日/截止日(YYYY-MM-DD，留空默认今天)")

        self.lpr_value = QLineEdit("3.45")
        self.lpr_value.setPlaceholderText("LPR(%)，手动维护")

        self.lpr_multiple = QLineEdit("4")
        self.lpr_multiple.setPlaceholderText("倍数，如 4")

        self.calc_daily_btn = QPushButton("按日万五折算")
        self.calc_daily_btn.clicked.connect(self.calc_penalty_daily_5_per_10k)

        self.calc_lpr_btn = QPushButton("按 LPR×倍数折算")
        self.calc_lpr_btn.clicked.connect(self.calc_penalty_by_lpr_multiple)

        calc_btn_layout = QHBoxLayout()
        calc_btn_layout.addWidget(self.calc_daily_btn)
        calc_btn_layout.addWidget(self.calc_lpr_btn)
        calc_btn_widget = QWidget()
        calc_btn_widget.setLayout(calc_btn_layout)

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 广州市天河区人民法院")

        # On-page explanation for the conditional (scenario-dependent) requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setStyleSheet("color: #B00020;")
        self.cond_hint.setWordWrap(True)

        layout.addRow("合同签订日期:", self.contract_date)
        layout.addRow("合同名称:", self.contract_name)
        layout.addRow("产品名称及数量:", self.product_name)
        layout.addRow("合同总金额(元):", self.total_amount)
        layout.addRow("交货日期:", self.delivery_date)
        layout.addRow("交货状态:", del_layout)
        layout.addRow("签收状态:", sign_layout)
        layout.addRow("", self.cond_hint)
        layout.addRow("尚欠货款本金(元):", self.unpaid_amount)
        layout.addRow("违约金/逾期利息(元):", self.penalty_amount)
        layout.addRow("", self.penalty_warning)
        layout.addRow("违约金计算起算:", self.overdue_start)
        layout.addRow("违约金计算截止:", self.overdue_end)
        layout.addRow("LPR(%)：", self.lpr_value)
        layout.addRow("LPR倍数：", self.lpr_multiple)
        layout.addRow("", calc_btn_widget)
        layout.addRow("建议管辖法院:", self.court_name)

        self.setLayout(layout)

        self.registerField("c_contract_date*", self.contract_date)
        self.registerField("c_contract_name*", self.contract_name)
        self.registerField("c_product_name*", self.product_name)
        self.registerField("c_total_amount*", self.total_amount)
        # The delivery date is required only when the user explicitly confirms
        # that the goods were delivered (enforced by isComplete() below), so it
        # is registered without the mandatory "*" marker.
        self.registerField("c_delivery_date", self.delivery_date)
        self.registerField("c_unpaid_amount*", self.unpaid_amount)
        self.registerField("c_penalty_amount", self.penalty_amount)
        self.registerField("c_court_name*", self.court_name)
        self.registerField("c_overdue_start", self.overdue_start)
        self.registerField("c_overdue_end", self.overdue_end)
        self.registerField("c_lpr_value", self.lpr_value)
        self.registerField("c_lpr_multiple", self.lpr_multiple)

        # Keep the Next-button state in sync with the conditional requirement.
        self.delivery_date.textChanged.connect(lambda *_: self._refresh_conditional())
        self.is_delivered_group.buttonToggled.connect(lambda *_: self._refresh_conditional())

    def _conditional_issue(self):
        """Return a message when a scenario-specific requirement is unmet."""
        if self.get_flags()["is_delivered"] is True and not self.delivery_date.text().strip():
            return "已选择“已交货”，请填写交货日期，或改选“未确认”/“未交货”。"
        return ""

    def _refresh_conditional(self):
        self.cond_hint.setText(self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        # Preserve the base mandatory-field behaviour for every other field.
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    @staticmethod
    def _tri_state(group, yes_id=1, no_id=0):
        """Map a radio group to ``True`` / ``False`` / ``None`` (unconfirmed)."""
        checked = group.checkedId()
        if checked == yes_id:
            return True
        if checked == no_id:
            return False
        return None

    def get_flags(self):
        """Return tri-state delivery/receipt flags.

        ``None`` means the fact has not been confirmed by the user; it must never
        be coerced into ``False`` or ``True`` downstream.
        """
        return {
            "is_delivered": self._tri_state(self.is_delivered_group),
            "is_signed": self._tri_state(self.is_signed_group),
        }

    def update_penalty_warning(self):
        text = self.penalty_amount.text().strip()
        if not text:
            self.penalty_warning.setText("")
            return
        try:
            float(text)
        except ValueError:
            self.penalty_warning.setText("违约金/逾期利息应为数字，请核对。")
            return
        # No fixed ratio is asserted as a legal ceiling; whether a penalty is
        # excessive is decided by the court in light of the contract and actual
        # loss, so only a neutral manual-review reminder is shown.
        self.penalty_warning.setText(
            "提示：违约金（或逾期付款利息）是否过高、可否调整，由法院结合合同约定与实际损失判断，"
            "本工具不作绝对判断，请在提交前人工核对。"
        )

    def _parse_date(self, text):
        import datetime
        s = (text or "").strip()
        if not s:
            return None
        parts = s.split("-")
        if len(parts) != 3:
            return None
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))

    def _get_overdue_days(self):
        import datetime
        d1 = self._parse_date(self.overdue_start.text())
        d2 = self._parse_date(self.overdue_end.text()) or datetime.date.today()
        if not d1:
            return None, None, None
        days = (d2 - d1).days
        return d1, d2, days

    def calc_penalty_daily_5_per_10k(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            unpaid = float(self.unpaid_amount.text().strip())
            d1, d2, days = self._get_overdue_days()
            if days is None or days <= 0:
                QMessageBox.warning(self, "提示", "请填写正确的逾期起算日，且截止日应晚于起算日。")
                return
            penalty = unpaid * 0.0005 * days
            self.penalty_amount.setText(f"{penalty:.2f}")
            self.update_penalty_warning()
        except Exception:
            QMessageBox.warning(self, "提示", "请先填写有效的“尚欠货款本金(元)”与日期(YYYY-MM-DD)。")

    def calc_penalty_by_lpr_multiple(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            unpaid = float(self.unpaid_amount.text().strip())
            lpr = float(self.lpr_value.text().strip())
            mult = float(self.lpr_multiple.text().strip())
            d1, d2, days = self._get_overdue_days()
            if days is None or days <= 0:
                QMessageBox.warning(self, "提示", "请填写正确的逾期起算日，且截止日应晚于起算日。")
                return
            annual_rate = (lpr * mult) / 100.0
            penalty = unpaid * annual_rate * (days / 365.0)
            self.penalty_amount.setText(f"{penalty:.2f}")
            self.update_penalty_warning()
        except Exception:
            QMessageBox.warning(self, "提示", "请先填写有效的本金、LPR、倍数与日期(YYYY-MM-DD)。")

class LoanClaimPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第二步：填写事实与理由")

        layout = QFormLayout()

        self.loan_date = QLineEdit()
        self.loan_date.setPlaceholderText("如: 2023年1月1日")

        self.loan_reason = QLineEdit()
        self.loan_reason.setPlaceholderText("如: 资金周转 / 装修房屋")

        self.principal = QLineEdit()
        self.principal.setPlaceholderText("如: 50000")

        self.payment_method = QLineEdit()
        self.payment_method.setPlaceholderText("如: 银行转账、微信、支付宝、现金")

        self.rate = QLineEdit()
        self.rate.setPlaceholderText("如: 14.6 (留空表示无利息约定)")

        self.start_date = QLineEdit()
        self.start_date.setPlaceholderText("如: 2023年5月1日")

        # IOU status is tri-state: the default "未确认" means no IOU fact may be
        # asserted until the user explicitly selects 有借条 or 无借条.
        self.has_iou_group = QButtonGroup(self)
        self.iou_yes = QRadioButton("有借条")
        self.iou_no = QRadioButton("无借条")
        self.iou_unknown = QRadioButton("未确认")
        self.has_iou_group.addButton(self.iou_yes, 1)
        self.has_iou_group.addButton(self.iou_no, 0)
        self.has_iou_group.addButton(self.iou_unknown, 2)
        self.iou_unknown.setChecked(True)
        iou_layout = QHBoxLayout()
        iou_layout.addWidget(self.iou_yes)
        iou_layout.addWidget(self.iou_no)
        iou_layout.addWidget(self.iou_unknown)

        self.demand_date = QLineEdit()
        self.demand_date.setPlaceholderText("如: 2023年10月至今")

        self.demand_method = QLineEdit()
        self.demand_method.setPlaceholderText("如: 微信、电话、上门")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 广州市天河区人民法院")

        # Validation warning label
        self.rate_warning = QLabel("")
        self.rate_warning.setStyleSheet("color: red;")
        self.rate.textChanged.connect(self.validate_rate)

        # On-page explanation for the conditional demand-information requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setStyleSheet("color: #B00020;")
        self.cond_hint.setWordWrap(True)

        layout.addRow("借款发生日期:", self.loan_date)
        layout.addRow("借款理由:", self.loan_reason)
        layout.addRow("借款本金(元):", self.principal)
        layout.addRow("交付方式:", self.payment_method)
        layout.addRow("是否有借条:", iou_layout)
        layout.addRow("约定年利率(%):", self.rate)
        layout.addRow("", self.rate_warning)
        layout.addRow("利息起算日:", self.start_date)
        layout.addRow("催款时间:", self.demand_date)
        layout.addRow("催款方式:", self.demand_method)
        layout.addRow("", self.cond_hint)
        layout.addRow("建议管辖法院:", self.court_name)

        self.setLayout(layout)

        # Register fields
        self.registerField("loan_date*", self.loan_date)
        self.registerField("loan_reason*", self.loan_reason)
        self.registerField("principal*", self.principal)
        self.registerField("payment_method*", self.payment_method)
        self.registerField("rate", self.rate)
        self.registerField("start_date", self.start_date)
        # Demand information is optional (a plaintiff may never have demanded
        # repayment), so these are registered without the mandatory "*" marker.
        # A partial record is handled by isComplete() below.
        self.registerField("demand_date", self.demand_date)
        self.registerField("demand_method", self.demand_method)
        self.registerField("court_name*", self.court_name)

        # Keep the Next-button state in sync with the conditional requirement.
        self.demand_date.textChanged.connect(lambda *_: self._refresh_conditional())
        self.demand_method.textChanged.connect(lambda *_: self._refresh_conditional())

    def _conditional_issue(self):
        """Demand information must be either fully supplied or fully omitted."""
        date = self.demand_date.text().strip()
        method = self.demand_method.text().strip()
        if bool(date) != bool(method):
            return "催款时间与催款方式需同时填写，或同时留空（未催款的可以不填）。"
        return ""

    def _refresh_conditional(self):
        self.cond_hint.setText(self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validate_rate(self):
        text = self.rate.text().strip()
        if not text:
            self.rate_warning.setText("")
            return
        try:
            val = float(text)
        except ValueError:
            self.rate_warning.setText("请输入有效的数字")
            return
        if val < 0:
            self.rate_warning.setText("年利率不应为负数，请核对。")
        else:
            # No fixed universal ceiling is asserted here: the applicable limit
            # depends on the latest judicial guidance and the specific case, so
            # the tool only reminds the user to verify it manually.
            self.rate_warning.setText(
                "温馨提示：借款利率的可支持上限与适用规则会随最新司法口径、时间和地区变化，"
                "本工具不代为判断是否超限，请在提交前人工核对。"
            )

    def get_has_iou(self):
        """Return ``True`` / ``False`` / ``None`` (unconfirmed) IOU status."""
        checked = self.has_iou_group.checkedId()
        if checked == 1:
            return True
        if checked == 0:
            return False
        return None

class PropertyClaimPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第二步：填写事实与理由 (物业服务合同)")

        layout = QFormLayout()

        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px; font-weight: bold;")
        self.fill_btn.clicked.connect(self.fill_test_data)
        layout.addRow("", self.fill_btn)

        self.property_addr = QLineEdit()
        self.property_addr.setPlaceholderText("如: 幸福里小区 3 栋 1201 室")

        self.house_area = QLineEdit()
        self.house_area.setPlaceholderText("如: 115.5")

        self.fee_rate = QLineEdit()
        self.fee_rate.setPlaceholderText("如: 2.8")

        self.period_start = QLineEdit()
        self.period_start.setPlaceholderText("如: 2024-01-01 或 2024年1月1日")

        self.period_end = QLineEdit()
        self.period_end.setPlaceholderText("如: 2025-12-31 或 2025年12月31日")

        self.late_fee_logic = QLineEdit()
        self.late_fee_logic.setPlaceholderText("如: 按合同约定计算 / 暂计 500 元")

        self.demand_record = QTextEdit()
        self.demand_record.setMaximumHeight(80)
        self.demand_record.setPlaceholderText("如: 2025年6月多次张贴催缴通知并发送短信。")

        self.total_input = QLineEdit()
        self.total_input.setPlaceholderText("可选：用户自填总金额，用于比对提示")

        self.calc_label = QLabel("")
        self.calc_label.setStyleSheet("color: gray;")
        self.warn_label = QLabel("")
        self.warn_label.setStyleSheet("color: red;")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 上海市徐汇区人民法院")

        for w in [self.house_area, self.fee_rate, self.period_start, self.period_end, self.total_input]:
            w.textChanged.connect(self.update_calc)

        layout.addRow("物业地址/房号:", self.property_addr)
        layout.addRow("房屋面积(m²):", self.house_area)
        layout.addRow("计费标准(元/m²/月):", self.fee_rate)
        layout.addRow("欠费起始日期:", self.period_start)
        layout.addRow("欠费截止日期:", self.period_end)
        layout.addRow("违约金/滞纳金计算:", self.late_fee_logic)
        layout.addRow("催缴方式:", self.demand_record)
        layout.addRow("自填总金额(元):", self.total_input)
        layout.addRow("系统计算:", self.calc_label)
        layout.addRow("", self.warn_label)
        layout.addRow("建议管辖法院:", self.court_name)

        self.setLayout(layout)

        self.registerField("p_property_addr*", self.property_addr)
        self.registerField("p_house_area*", self.house_area)
        self.registerField("p_fee_rate*", self.fee_rate)
        self.registerField("p_period_start*", self.period_start)
        self.registerField("p_period_end*", self.period_end)
        self.registerField("p_late_fee_logic", self.late_fee_logic)
        self.registerField("p_demand_record", self.demand_record, "plainText")
        self.registerField("p_total_input", self.total_input)
        self.registerField("p_court_name*", self.court_name)

    def initializePage(self):
        super().initializePage()
        self.update_calc()

    def _parse_date(self, s):
        import datetime
        import re
        t = (s or "").strip()
        if not t:
            return None
        t2 = re.sub(r"[^\d]", "-", t).strip("-")
        parts = t2.split("-")
        if len(parts) < 3:
            return None
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))

    def _calc_months(self, d1, d2):
        if not d1 or not d2:
            return 0
        if d2 < d1:
            return 0
        return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1

    def update_calc(self):
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
        try:
            d1 = self._parse_date(self.period_start.text())
            d2 = self._parse_date(self.period_end.text())
            months = self._calc_months(d1, d2)
            area = Decimal(self.house_area.text().strip())
            rate = Decimal(self.fee_rate.text().strip())
            total = (area * rate * Decimal(str(months))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.calc_label.setText(f"月数={months}，总本金={total} 元")

            user_total_text = self.total_input.text().strip()
            if user_total_text:
                user_total = Decimal(user_total_text)
                if user_total != 0:
                    diff = (abs(user_total - total) / user_total)
                    if diff > Decimal("0.01"):
                        self.warn_label.setText("提示：自填总金额与系统计算误差超过 1%，建议核对。")
                    else:
                        self.warn_label.setText("")
                else:
                    self.warn_label.setText("")
            else:
                self.warn_label.setText("")
        except (InvalidOperation, ValueError):
            self.calc_label.setText("月数=0，总本金=0.00 元")
            self.warn_label.setText("")

    def fill_test_data(self):
        self.property_addr.setText("幸福里小区 3 栋 1201 室")
        self.house_area.setText("115.5")
        self.fee_rate.setText("2.8")
        self.period_start.setText("2024-01-01")
        self.period_end.setText("2025-12-31")
        self.late_fee_logic.setText("按合同约定计算")
        self.demand_record.setPlainText("2025年6月多次张贴催缴通知、发送短信。")
        self.total_input.setText("")
        self.court_name.setText("上海市徐汇区人民法院")
        self.update_calc()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "提示", "物业纠纷测试数据已填入。")

class EvidencePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第三步：证据清单 (选填)")

        layout = QVBoxLayout()
        self.desc_label = QLabel("请列出您准备提交的证据。")
        layout.addWidget(self.desc_label)

        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("[+] 添加证据")
        self.add_row_btn.clicked.connect(self.add_row)
        self.remove_row_btn = QPushButton("[-] 删除选中行")
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.remove_row_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        layout.addWidget(btn_widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["证据名称", "证明目的"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked | QTableWidget.EditTrigger.EditKeyPressed)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def initializePage(self):
        super().initializePage()
        try:
            from utils.evidence_library import EvidenceLibrary
            case_type = self.wizard().field("case_type")
            items = EvidenceLibrary.get_default_evidence(case_type)
            if case_type == "contract":
                self.desc_label.setText("买卖合同纠纷常见证据（可按需修改/增删）：")
            elif case_type == "loan":
                self.desc_label.setText("民间借贷纠纷常见证据（可按需修改/增删）：")
            elif case_type == "property":
                self.desc_label.setText("物业服务合同纠纷常见证据（可按需修改/增删）：")
            else:
                self.desc_label.setText("常见证据（可按需修改/增删）：")
            if self.table.rowCount() == 0:
                for name, target in items:
                    self.add_row(name, target)
        except Exception:
            return

    def add_row(self, name="", target=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(name)))
        self.table.setItem(row, 1, QTableWidgetItem(str(target)))

    def remove_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def get_evidence_items(self):
        items = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            target_item = self.table.item(r, 1)
            name = name_item.text().strip() if name_item else ""
            target = target_item.text().strip() if target_item else ""
            if name or target:
                items.append((name, target))
        return items

class LaborClaimPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第二步：填写事实与理由 (劳动报酬/工资追索)")

        layout = QFormLayout()

        self.emp_join_date = QLineEdit()
        self.emp_join_date.setPlaceholderText("如: 2023-01-15")

        self.job_title = QLineEdit()
        self.job_title.setPlaceholderText("如: 软件工程师")

        self.monthly_salary = QLineEdit()
        self.monthly_salary.setPlaceholderText("如: 8000")

        self.unpaid_months = QLineEdit()
        self.unpaid_months.setPlaceholderText("如: 2023年12月至2024年2月")

        self.emp_term_date = QLineEdit()
        self.emp_term_date.setPlaceholderText("如: 2024-03-20")

        self.overtime_hours = QLineEdit()
        self.overtime_hours.setPlaceholderText("如: 40 (选填)")

        self.overtime_pay = QLineEdit()
        self.overtime_pay.setPlaceholderText("如: 3500 (选填)")

        self.is_no_contract_group = QButtonGroup(self)
        self.no_contract_yes = QRadioButton("是")
        self.no_contract_no = QRadioButton("否")
        self.is_no_contract_group.addButton(self.no_contract_yes, 1)
        self.is_no_contract_group.addButton(self.no_contract_no, 0)
        self.no_contract_no.setChecked(True)
        no_contract_layout = QHBoxLayout()
        no_contract_layout.addWidget(self.no_contract_yes)
        no_contract_layout.addWidget(self.no_contract_no)

        self.social_sec_info = QLineEdit()
        self.social_sec_info.setPlaceholderText("如: 未按实际工资基数缴纳 (选填)")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        layout.addRow("入职日期:", self.emp_join_date)
        layout.addRow("岗位:", self.job_title)
        layout.addRow("月工资标准(元):", self.monthly_salary)
        layout.addRow("欠薪月份/区间:", self.unpaid_months)
        layout.addRow("离职/截止日期:", self.emp_term_date)
        layout.addRow("加班工时(小时，选填):", self.overtime_hours)
        layout.addRow("加班费(元，选填):", self.overtime_pay)
        layout.addRow("是否未签劳动合同:", no_contract_layout)
        layout.addRow("社保缴纳情况:", self.social_sec_info)
        layout.addRow("建议管辖法院:", self.court_name)

        self.setLayout(layout)

        self.registerField("l_emp_join_date*", self.emp_join_date)
        self.registerField("l_job_title*", self.job_title)
        self.registerField("l_monthly_salary*", self.monthly_salary)
        self.registerField("l_unpaid_months*", self.unpaid_months)
        self.registerField("l_emp_term_date*", self.emp_term_date)
        self.registerField("l_overtime_hours", self.overtime_hours)
        self.registerField("l_overtime_pay", self.overtime_pay)
        self.registerField("l_social_sec_info", self.social_sec_info)
        self.registerField("l_court_name*", self.court_name)

    def get_has_no_contract(self):
        return self.is_no_contract_group.checkedId() == 1

class DivorceClaimPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第二步：填写事实与理由 (离婚析产/抚养费纠纷)")

        layout = QFormLayout()

        self.marriage_date = QLineEdit()
        self.marriage_date.setPlaceholderText("如: 2018-05-20")

        self.child_name = QLineEdit()
        self.child_name.setPlaceholderText("如: 张三")

        self.child_birthday = QLineEdit()
        self.child_birthday.setPlaceholderText("如: 2020-01-01")

        self.custody_preference = QLineEdit()
        self.custody_preference.setPlaceholderText("如: 由原告抚养")

        self.support_monthly = QLineEdit()
        self.support_monthly.setPlaceholderText("如: 3000")

        self.divorce_reason = QLineEdit()
        self.divorce_reason.setPlaceholderText("如: 感情不和/长期分居")

        self.separation_start_date = QLineEdit()
        self.separation_start_date.setPlaceholderText("如: 2022-01-01")

        self.asset_description = QLineEdit()
        self.asset_description.setPlaceholderText("如: 房产归原告，车辆归被告")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        # On-page explanation for the conditional child-information requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setStyleSheet("color: #B00020;")
        self.cond_hint.setWordWrap(True)

        layout.addRow("登记结婚日期:", self.marriage_date)
        layout.addRow("子女姓名:", self.child_name)
        layout.addRow("子女出生日期:", self.child_birthday)
        layout.addRow("抚养权诉求:", self.custody_preference)
        layout.addRow("月抚养费金额(元):", self.support_monthly)
        layout.addRow("", self.cond_hint)
        layout.addRow("离婚原因:", self.divorce_reason)
        layout.addRow("分居起始日期:", self.separation_start_date)
        layout.addRow("财产分割方案:", self.asset_description)
        layout.addRow("建议管辖法院:", self.court_name)

        self.setLayout(layout)

        self.registerField("d_marriage_date*", self.marriage_date)
        # Child information is optional: a childless divorce must be reachable.
        # Child-related fields are only consistent together, which is enforced
        # by isComplete() below, so they are registered without "*".
        self.registerField("d_child_name", self.child_name)
        self.registerField("d_child_birthday", self.child_birthday)
        self.registerField("d_custody_preference", self.custody_preference)
        self.registerField("d_support_monthly", self.support_monthly)
        self.registerField("d_divorce_reason", self.divorce_reason)
        self.registerField("d_separation_start_date", self.separation_start_date)
        self.registerField("d_asset_description", self.asset_description)
        self.registerField("d_court_name*", self.court_name)

        # Keep the Next-button state in sync with the conditional requirement.
        for widget in (self.child_name, self.child_birthday, self.custody_preference,
                       self.support_monthly):
            widget.textChanged.connect(lambda *_: self._refresh_conditional())

    def _conditional_issue(self):
        """Child-related details require an identified child."""
        if self.child_name.text().strip():
            return ""
        orphans = []
        if self.child_birthday.text().strip():
            orphans.append("子女出生日期")
        if self.custody_preference.text().strip():
            orphans.append("抚养权诉求")
        if self.support_monthly.text().strip():
            orphans.append("月抚养费金额")
        if orphans:
            return ("已填写" + "、".join(orphans)
                    + "，请同时填写“子女姓名”，或清空上述子女相关字段"
                      "（无子女的离婚可以不填）。")
        return ""

    def _refresh_conditional(self):
        self.cond_hint.setText(self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

class ExportPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("第四步：完成与导出")
        # Ensure it acts as the final page
        self.setFinalPage(True)

        layout = QVBoxLayout()

        self.preview_btn = QPushButton("预览起诉状文本")
        self.preview_btn.clicked.connect(self.show_preview)
        layout.addWidget(self.preview_btn)

        label = QLabel("信息收集完毕！\n\n点击“完成”按钮，系统将为您生成标准的 Word 格式起诉状（及证据清单）并直接保存在您的桌面上。")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.secure_exit_btn = QPushButton("退出程序（不删除已生成文件）")
        self.secure_exit_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.secure_exit_btn.clicked.connect(self.secure_exit)
        layout.addWidget(self.secure_exit_btn)

        self.setLayout(layout)

    def show_preview(self):
        """Show a case-specific preview built from the same model as the export."""
        from PySide6.QtWidgets import QMessageBox

        wizard = self.wizard()
        case_type = wizard.field("case_type")

        case_labels = {
            "loan": "民间借贷纠纷",
            "contract": "买卖合同纠纷",
            "property": "物业服务合同纠纷",
            "labor": "劳动报酬/工资追索",
            "divorce": "离婚纠纷",
        }
        label = case_labels.get(case_type, "未知案由")

        try:
            from presenters.model_builder import build_case_model
            model = build_case_model(wizard)
            claims = model.render_claims()
            facts = model.render_facts()
        except Exception as exc:  # a preview failure must never crash the wizard
            QMessageBox.warning(self, "预览不可用", f"暂时无法生成“{label}”预览：\n{exc}")
            return

        claims_text = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))
        preview_text = (
            f"案由：{label}\n\n"
            f"【诉讼请求（预览）】\n{claims_text}\n\n"
            f"【事实与理由（预览）】\n{facts}"
        )
        QMessageBox.information(
            self,
            "起诉状预览（部分文本）",
            "以下预览由与最终文书相同的案件模型生成，仅展示诉讼请求与事实理由的文本，"
            "不含当事人排版、表格与页眉页脚：\n\n" + preview_text,
        )

    def secure_exit(self):
        """Close the wizard without claiming that files or memory were destroyed."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "退出",
            "程序将关闭。案件信息存在于本机内存与已生成的 Word 文件中；"
            "关闭程序不会自动删除已生成的文件，请按需自行妥善保存或销毁。",
        )
        self.wizard().close()
