# File: views/wizard_pages.py
# Purpose: Wizard UI pages for the lawsuit application
# Encoding: UTF-8

import os
import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QRadioButton, QButtonGroup, QTextEdit, QGroupBox, QHBoxLayout, QPushButton, QScrollArea, QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QPlainTextEdit, QFileDialog
from PySide6.QtGui import QBrush, QColor, QRegularExpressionValidator

from views.theme import (
    DANGER_BUTTON,
    DEMO_BADGE,
    ERROR_LABEL,
    INFO_LABEL,
    PRIMARY_BUTTON,
    REMINDER_LABEL,
    SECONDARY_BUTTON,
    SUCCESS_LABEL,
    WARNING_LABEL,
)


def _set_status(label, text):
    """Set a status label's text and hide it when empty.

    Status labels carry background/border styling, so an empty string would
    otherwise render as a stray coloured box.
    """
    label.setText(text)
    label.setVisible(bool(text))


def _dedup_messages(messages):
    """Remove duplicate messages while preserving order and non-empty values."""
    seen = set()
    result = []
    for msg in messages:
        msg = msg.strip()
        if msg and msg not in seen:
            seen.add(msg)
            result.append(msg)
    return result

# Phone input accepts only digits and the common grouping/prefix characters so
# that obviously invalid text (letters, brackets, etc.) cannot be entered. The
# precise digit-count check happens in PartyPage.validate_parties() so that a
# legitimate landline or extension is not rejected outright.
_PHONE_INPUT_PATTERN = QRegularExpression(r"^[0-9+\-() ]{0,20}$")

# Amount / percentage inputs (元, %, 倍数等) accept a non-negative decimal with up
# to two fraction digits. Empty is allowed so optional fields can stay blank; the
# mandatory check is enforced separately by the ``*`` field marker. Letters and
# leading signs are rejected at the text-entry level.
_DECIMAL_INPUT_PATTERN = QRegularExpression(r"^(?:\d{1,12}(?:\.\d{0,2})?)?$")


def _decimal_validator(line_edit):
    """Restrict ``line_edit`` to non-negative decimals (empty allowed)."""
    line_edit.setValidator(QRegularExpressionValidator(_DECIMAL_INPUT_PATTERN, line_edit))


def _section(root, title):
    """Append a titled group box to ``root`` and return its inner form layout."""
    box = QGroupBox(title)
    form = QFormLayout(box)
    root.addWidget(box)
    return form


def _set_form_accessibility(form, prefix=""):
    """Give labelled text inputs explicit, screen-reader-friendly names.

    Qt does not automatically expose a ``QFormLayout`` label as an accessible
    name.  Keeping this close to the form-building helpers means every input
    added through a labelled row receives both a name and a concise purpose,
    without relying on placeholder text (which disappears as soon as users
    start typing).
    """
    for row in range(form.rowCount()):
        label_item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        field_item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
        if label_item is None or field_item is None:
            continue
        label = label_item.widget()
        field = field_item.widget()
        if not isinstance(label, QLabel) or not isinstance(
            field, (QLineEdit, QTextEdit, QPlainTextEdit)
        ):
            continue
        label_text = label.text().replace(":", "").replace("：", "").strip()
        if not label_text:
            continue
        name = f"{prefix}{label_text}" if prefix else label_text
        field.setAccessibleName(name)
        field.setAccessibleDescription(f"填写{name}")


def _set_page_form_accessibility(page):
    """Apply the labelled-input convention to every form on a wizard page."""
    for form in page.findChildren(QFormLayout):
        _set_form_accessibility(form)


def _wrap_in_scroll(root_layout):
    """Wrap *root_layout* in a resizable QScrollArea and return the outer layout.

    Callers do ``self.setLayout(_wrap_in_scroll(root))`` instead of
    ``self.setLayout(root)`` so that long forms stay usable on small screens
    and high-DPI scaling factors.  The outer layout has zero margins so the
    scroll area fills the page exactly as the original layout did.
    """
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    content = QWidget()
    content.setLayout(root_layout)
    scroll.setWidget(content)
    outer = QVBoxLayout()
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(scroll)
    return outer


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用民事立案文书助手")

        layout = QVBoxLayout()

        desc = (
            "本工具引导您填写案情，一键生成民事立案所需的三份可编辑 Word 初稿："
            "民事起诉状、证据清单与送达地址确认书。\n\n"
            "【本地离线说明】\n"
            "- 本地运行：案件信息仅在本机处理，生成 Word 文书时不联网上传。\n"
            "- 启动时检测默认网络路由并给出提示，该提示只是辅助提醒，不等同于系统级网络隔离。\n"
            "- 生成完成后对内存中的敏感字段执行尽力清理（Python 无法保证彻底、不可恢复地销毁）。\n\n"
            "点击“下一步”开始填写。"
        )
        label = QLabel(desc)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Demo-mode badge, hidden in production.
        self.demo_badge = QLabel("演示模式")
        self.demo_badge.setObjectName(DEMO_BADGE)
        self.demo_badge.setVisible(False)
        layout.addWidget(self.demo_badge)

        layout.addStretch()

        # Test-data entry point, only shown in demo mode (see set_demo_mode).
        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setObjectName(PRIMARY_BUTTON)
        self.fill_btn.setVisible(False)
        layout.addWidget(self.fill_btn)

        self.setLayout(layout)

    def set_demo_mode(self, enabled):
        """Show or hide the demo-mode badge and test-data button."""
        self.fill_btn.setVisible(enabled)
        self.demo_badge.setVisible(enabled)

class CaseSelectionPage(QWizardPage):
    # One-line suitability notes shown under the dropdown for each choice.
    CASE_DESCRIPTIONS = {
        "loan": "适用于个人之间或自然人向他人出借资金的借款纠纷。",
        "contract": "适用于买卖双方就货款、交付、验收等问题发生的合同纠纷。",
        "property": "适用于业主与物业公司之间的物业费、服务合同纠纷。",
        "labor": "适用于工资、加班费等劳动报酬追索（注意仲裁前置）。",
        "divorce": "适用于离婚、子女抚养与财产分割等婚姻家庭纠纷。",
    }

    def __init__(self):
        super().__init__()
        self.setTitle("选择案件类型")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("请选择您要生成的起诉状案由："))

        from PySide6.QtWidgets import QComboBox
        self.case_combo = QComboBox()
        self.case_combo.setAccessibleName("案由选择")
        self.case_combo.setAccessibleDescription("选择起诉状的案件类型")
        self.case_combo.addItem("民间借贷纠纷", "loan")
        self.case_combo.addItem("买卖合同纠纷", "contract")
        self.case_combo.addItem("物业服务合同纠纷", "property")
        self.case_combo.addItem("劳动报酬/工资追索", "labor")
        self.case_combo.addItem("离婚纠纷", "divorce")
        layout.addWidget(self.case_combo)

        self.case_desc_label = QLabel("")
        self.case_desc_label.setObjectName(INFO_LABEL)
        self.case_desc_label.setWordWrap(True)
        layout.addWidget(self.case_desc_label)

        # Persistent labour-arbitration notice, shown only while "labor" is
        # selected (replaces the previous blocking dialog).
        self.labor_notice = QLabel("")
        self.labor_notice.setObjectName(REMINDER_LABEL)
        self.labor_notice.setWordWrap(True)
        self.labor_notice.setVisible(False)
        layout.addWidget(self.labor_notice)

        layout.addStretch()
        self.setLayout(layout)

        from utils.labor_security import LaborProcedureGuard
        self.labor_guard = LaborProcedureGuard()
        self.case_combo.currentTextChanged.connect(self._on_case_type_changed)
        self._refresh_case_context()

        self.registerField("case_type", self.case_combo, "currentData")

    def _on_case_type_changed(self, _text):
        self._refresh_case_context()

    def _refresh_case_context(self):
        case_data = self.case_combo.currentData()
        self.case_desc_label.setText(self.CASE_DESCRIPTIONS.get(case_data, ""))
        if case_data == "labor":
            self.labor_notice.setText(self.labor_guard.get_warning_text())
            self.labor_notice.setVisible(True)
        else:
            self.labor_notice.setText("")
            self.labor_notice.setVisible(False)

class PartyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("填写当事人信息")

        main_layout = QVBoxLayout()

        # Live validation / guidance message for the party list.
        self.msg_label = QLabel("")
        self.msg_label.setObjectName(ERROR_LABEL)
        self.msg_label.setWordWrap(True)
        self.msg_label.setVisible(False)
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

        # Progressive validation: nothing is flagged until the user interacts
        # (leaves a field or clicks Next); reset on each fresh entry.
        self._touched = False

        # Add Plaintiff Button
        self.add_p_btn = QPushButton("[+] 添加原告")
        self.add_p_btn.setAccessibleName("添加原告")
        self.add_p_btn.setAccessibleDescription("添加一名原告当事人卡片")
        self.add_p_btn.clicked.connect(lambda: self.add_party_ui(0))
        self.scroll_layout.addWidget(self.add_p_btn)

        # Add Defendant Button
        self.add_d_btn = QPushButton("[+] 添加被告")
        self.add_d_btn.setAccessibleName("添加被告")
        self.add_d_btn.setAccessibleDescription("添加一名被告当事人卡片")
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

        # Fresh entry: hide any previously shown errors until interaction.
        self._touched = False

        # Initialize with at least 1 plaintiff and 1 defendant
        self.add_party_ui(0)
        self.add_party_ui(1)
        self._rebuild_party_tab_order()

    def add_party_ui(self, party_type):
        is_plaintiff = (party_type == 0)
        kind = "原告" if is_plaintiff else "被告"
        number = (len(self.plaintiff_widgets) + 1) if is_plaintiff else (len(self.defendant_widgets) + 1)
        group = QGroupBox(f"{kind}{number}")
        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        name_edit = QLineEdit()
        id_edit = QLineEdit()
        addr_edit = QLineEdit()
        phone_edit = QLineEdit()

        from PySide6.QtWidgets import QCheckBox, QLabel
        is_company_check = QCheckBox("该当事人为单位/企业（非自然人）")
        is_company_check.setChecked(False)

        # Company-specific widgets are always created so that a corporate party
        # works for every case type and the extraction code never touches a
        # ``None`` widget. They stay hidden until the toggle is switched.
        credit_code_edit = QLineEdit()
        credit_code_edit.setPlaceholderText("统一社会信用代码")
        credit_code_edit.setVisible(False)

        legal_rep_edit = QLineEdit()
        legal_rep_edit.setPlaceholderText("法定代表人姓名")
        legal_rep_edit.setVisible(False)

        # "身份证号" is the personal identity field; resuming a company toggles
        # it away and reveals the credit-code/legal-representative fields, so no
        # duplicate identity row is ever shown.
        layout.addRow("姓名/名称:", name_edit)
        layout.addRow("身份证号:", id_edit)
        layout.addRow("统一社会信用代码:", credit_code_edit)
        layout.addRow("法定代表人:", legal_rep_edit)
        layout.addRow("住址/住所地:", addr_edit)
        layout.addRow("电话:", phone_edit)

        # QFormLayout owns separate label widgets. Hide and show those labels
        # together with their fields so switching party type never leaves a
        # dangling identity-field caption behind.
        id_label = layout.labelForField(id_edit)
        credit_code_label = layout.labelForField(credit_code_edit)
        legal_rep_label = layout.labelForField(legal_rep_edit)

        phone_validator = QRegularExpressionValidator(_PHONE_INPUT_PATTERN)
        phone_edit.setValidator(phone_validator)

        case_type = self.field("case_type")
        is_property_case = (case_type == "property")

        # Only create addr_hint for property cases
        if is_property_case and not is_plaintiff:
            addr_hint = QLabel("提示：若被告搬家，请填写现居住满一年的地址，以便法院送达。")
            addr_hint.setObjectName(REMINDER_LABEL)
            addr_hint.setWordWrap(True)
            layout.addRow(addr_hint)

        # 个人/企业 toggle, full-width. Toggling swaps the personal ID field for
        # the company credit-code/legal-representative fields.
        is_company_check.toggled.connect(
            lambda checked: self._toggle_company_fields(
                checked,
                id_edit,
                credit_code_edit,
                legal_rep_edit,
                id_label,
                credit_code_label,
                legal_rep_label,
            )
        )
        layout.addRow(is_company_check)

        # Per-card delete action.
        delete_btn = QPushButton("删除")
        delete_btn.setObjectName(DANGER_BUTTON)
        delete_btn.setAccessibleName(f"删除{kind}卡片")
        layout.addRow(delete_btn)

        group.setLayout(layout)

        widget = {
            "group": group,
            "name": name_edit,
            "id": id_edit,
            "addr": addr_edit,
            "phone": phone_edit,
            "is_company": is_company_check,
            "credit_code": credit_code_edit,
            "legal_rep": legal_rep_edit,
            "id_label": id_label,
            "credit_code_label": credit_code_label,
            "legal_rep_label": legal_rep_label,
            "delete_btn": delete_btn,
            "form": layout,
        }
        delete_btn.clicked.connect(lambda _=False, t=party_type, d=widget: self._remove_party(t, d))

        # Insert before the add buttons or stretch
        if is_plaintiff:
            insert_idx = self.scroll_layout.indexOf(self.add_p_btn)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.plaintiff_widgets.append(widget)
        else:
            insert_idx = self.scroll_layout.indexOf(self.add_d_btn)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.defendant_widgets.append(widget)

        # Apply the initial natural-person state to both fields and labels.
        self._toggle_company_fields(
            False,
            id_edit,
            credit_code_edit,
            legal_rep_edit,
            id_label,
            credit_code_label,
            legal_rep_label,
        )
        _set_form_accessibility(layout, f"{kind}{number}")

        # Keep the live guidance and the wizard "Next" button state in sync, and
        # mark the page as touched when the user leaves a field.
        for w in (name_edit, phone_edit, credit_code_edit, legal_rep_edit):
            w.textChanged.connect(lambda _text: self._refresh_validation_message())
            w.editingFinished.connect(self._on_field_edited)

        self._refresh_validation_message()
        self._rebuild_party_tab_order()

    def _toggle_company_fields(
        self,
        checked,
        id_edit,
        credit_code_edit,
        legal_rep_edit,
        id_label,
        credit_code_label,
        legal_rep_label,
    ):
        if id_edit is not None:
            id_edit.setVisible(not checked)
        if id_label is not None:
            id_label.setVisible(not checked)
        if credit_code_edit is not None:
            credit_code_edit.setVisible(checked)
        if credit_code_label is not None:
            credit_code_label.setVisible(checked)
        if legal_rep_edit is not None:
            legal_rep_edit.setVisible(checked)
        if legal_rep_label is not None:
            legal_rep_label.setVisible(checked)
        self._refresh_validation_message()

    def _renumber_parties(self):
        """Keep card numbers contiguous after additions/removals."""
        for idx, w in enumerate(self.plaintiff_widgets, 1):
            w["group"].setTitle(f"原告{idx}")
            _set_form_accessibility(w["form"], f"原告{idx}")
        for idx, w in enumerate(self.defendant_widgets, 1):
            w["group"].setTitle(f"被告{idx}")
            _set_form_accessibility(w["form"], f"被告{idx}")

    def _rebuild_party_tab_order(self):
        """Keep keyboard traversal aligned with the visible party-card order."""
        sequence = []
        for card in self.plaintiff_widgets:
            sequence.extend(
                card[key]
                for key in ("name", "id", "credit_code", "legal_rep", "addr", "phone",
                            "is_company", "delete_btn")
            )
        sequence.append(self.add_p_btn)
        for card in self.defendant_widgets:
            sequence.extend(
                card[key]
                for key in ("name", "id", "credit_code", "legal_rep", "addr", "phone",
                            "is_company", "delete_btn")
            )
        sequence.append(self.add_d_btn)
        for previous, following in zip(sequence, sequence[1:]):
            QWidget.setTabOrder(previous, following)

    def _remove_party(self, party_type, widget):
        widgets = self.plaintiff_widgets if party_type == 0 else self.defendant_widgets
        try:
            widgets.remove(widget)
        except ValueError:
            return
        widget["group"].deleteLater()
        self._renumber_parties()
        self._rebuild_party_tab_order()
        self._refresh_validation_message()

    def remove_party_ui(self, party_type, index):
        """Remove the party card at ``index`` (0-based) for tests and scripts."""
        widgets = self.plaintiff_widgets if party_type == 0 else self.defendant_widgets
        if 0 <= index < len(widgets):
            self._remove_party(party_type, widgets[index])

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

        ``validatePage`` additionally blocks an explicitly added empty card,
        preventing the model builder from silently skipping that party.
        """
        return (
            self._has_named_party(self.plaintiff_widgets)
            and self._has_named_party(self.defendant_widgets)
        )

    def validate_parties(self):
        """Return a list of human-readable party-input issues.

        Each empty party card yields exactly one "不能为空" message (no
        side-level duplicate), so the summary is de-duplicated. Softer format
        warnings (phone length or unified social credit code) follow and only
        advise — they never block generation.
        """
        issues = []

        # A side-level message only when a side has no card left at all (e.g.
        # every card was deleted). Otherwise per-card messages below cover it,
        # so a normal blank card never produces a duplicated side-level warning.
        if not self.plaintiff_widgets:
            issues.append("请至少填写一名原告的姓名/名称。")
        if not self.defendant_widgets:
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
        issues = _dedup_messages(self.validate_parties())
        # Progressive validation: nothing is shown until the page is touched.
        _set_status(self.msg_label, "\n".join(issues) if self._touched else "")
        # Notify the wizard so the "Next" button reflects the current state.
        self.completeChanged.emit()

    def _on_field_edited(self):
        """Mark the page touched when a field loses focus, then refresh errors."""
        self._touched = True
        self._refresh_validation_message()

    def _first_invalid_name_widget(self):
        """Return the first empty name field (the one that blocks the page)."""
        for w in self.plaintiff_widgets + self.defendant_widgets:
            if not self._widget_text(w["name"]).strip():
                return w["name"]
        return None

    def _has_missing_party_name(self):
        """Return whether any existing party card lacks its required name."""
        return any(
            not self._widget_text(w["name"]).strip()
            for w in self.plaintiff_widgets + self.defendant_widgets
        )

    def focus_first_invalid(self):
        """Move focus to the first blocking field; return whether it existed."""
        widget = self._first_invalid_name_widget()
        if widget is not None:
            widget.setFocus()
            return True
        return False

    def validatePage(self):
        """Run on Next: reveal errors, focus the first invalid field, and block
        navigation while the page is incomplete."""
        self._touched = True
        issues = _dedup_messages(self.validate_parties())
        _set_status(self.msg_label, "\n".join(issues))
        self.focus_first_invalid()
        # ``isComplete`` keeps the standard QWizard button state responsive
        # once each side has a named party. A deliberately added but blank
        # extra card must still block the transition here; otherwise the model
        # builder would silently skip it during export.
        return self.isComplete() and not self._has_missing_party_name()

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
        self.setTitle("填写案情与请求（买卖合同）")

        root = QVBoxLayout()

        # --- 一、合同基本事实 -------------------------------------------------
        basics = _section(root, "一、合同基本事实")

        self.contract_date = QLineEdit()
        self.contract_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-01")

        self.contract_name = QLineEdit()
        self.contract_name.setPlaceholderText("如: 产品购销合同")

        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("如: 10台联想电脑")

        self.total_amount = QLineEdit()
        self.total_amount.setPlaceholderText("单位：元，如 50000")
        _decimal_validator(self.total_amount)

        basics.addRow("合同签订日期:", self.contract_date)
        basics.addRow("合同名称:", self.contract_name)
        basics.addRow("产品名称及数量:", self.product_name)
        basics.addRow("合同总金额(元):", self.total_amount)

        # --- 二、履行与签收情况 ---------------------------------------------
        performance = _section(root, "二、履行与签收情况")

        self.delivery_date = QLineEdit()
        self.delivery_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-02-01（已交货时必填）")

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

        # On-page explanation for the conditional (scenario-dependent) requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setObjectName(WARNING_LABEL)
        self.cond_hint.setWordWrap(True)
        self.cond_hint.setVisible(False)

        performance.addRow("交货日期:", self.delivery_date)
        performance.addRow("交货状态:", del_layout)
        performance.addRow("签收状态:", sign_layout)
        performance.addRow("", self.cond_hint)

        # --- 三、尚欠货款与违约金/逾期利息 -----------------------------------
        amounts = _section(root, "三、尚欠货款与违约金/逾期利息")

        self.unpaid_amount = QLineEdit()
        self.unpaid_amount.setPlaceholderText("单位：元，如 30000")
        _decimal_validator(self.unpaid_amount)

        self.penalty_amount = QLineEdit()
        self.penalty_amount.setPlaceholderText("单位：元，如 5000（留空表示无）")
        _decimal_validator(self.penalty_amount)

        self.penalty_warning = QLabel("")
        self.penalty_warning.setObjectName(REMINDER_LABEL)
        self.penalty_warning.setWordWrap(True)
        self.penalty_warning.setVisible(False)
        self.penalty_amount.textChanged.connect(self.update_penalty_warning)

        self.overdue_start = QLineEdit()
        self.overdue_start.setPlaceholderText("格式 YYYY-MM-DD，如 2023-03-01")

        self.overdue_end = QLineEdit()
        self.overdue_end.setPlaceholderText("格式 YYYY-MM-DD（留空默认今天）")

        self.lpr_value = QLineEdit("3.45")
        self.lpr_value.setPlaceholderText("LPR(%)，手动维护")
        _decimal_validator(self.lpr_value)

        self.lpr_multiple = QLineEdit("4")
        self.lpr_multiple.setPlaceholderText("倍数，如 4")
        _decimal_validator(self.lpr_multiple)

        self.calc_daily_btn = QPushButton("按日万五折算（辅助）")
        self.calc_daily_btn.setObjectName(SECONDARY_BUTTON)
        self.calc_daily_btn.setAccessibleName("按日万五折算违约金")
        self.calc_daily_btn.clicked.connect(self.calc_penalty_daily_5_per_10k)

        self.calc_lpr_btn = QPushButton("按 LPR×倍数折算（辅助）")
        self.calc_lpr_btn.setObjectName(SECONDARY_BUTTON)
        self.calc_lpr_btn.setAccessibleName("按LPR倍数折算违约金")
        self.calc_lpr_btn.clicked.connect(self.calc_penalty_by_lpr_multiple)

        calc_btn_layout = QHBoxLayout()
        calc_btn_layout.addWidget(self.calc_daily_btn)
        calc_btn_layout.addWidget(self.calc_lpr_btn)
        calc_btn_layout.addStretch()
        calc_btn_widget = QWidget()
        calc_btn_widget.setLayout(calc_btn_layout)

        # Auxiliary explanation: the buttons only fill in the penalty box from the
        # supplied principal/date/LPR figures; the result stays user-editable and
        # is never a final legal conclusion.
        self.calc_help = QLabel(
            "辅助计算仅依据上方填写的本金、逾期起止日与 LPR 估算，结果自动填入"
            "“违约金/逾期利息”框，可手动修改；最终是否支持及其数额由法院认定。"
        )
        self.calc_help.setObjectName(INFO_LABEL)
        self.calc_help.setWordWrap(True)

        amounts.addRow("尚欠货款本金(元):", self.unpaid_amount)
        amounts.addRow("违约金/逾期利息(元):", self.penalty_amount)
        amounts.addRow("", self.penalty_warning)
        amounts.addRow("违约金计算起算:", self.overdue_start)
        amounts.addRow("违约金计算截止:", self.overdue_end)
        amounts.addRow("LPR(%)：", self.lpr_value)
        amounts.addRow("LPR倍数：", self.lpr_multiple)
        amounts.addRow("", calc_btn_widget)
        amounts.addRow(self.calc_help)

        # --- 四、建议管辖法院 ------------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 广州市天河区人民法院")
        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

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
        _set_status(self.cond_hint, self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        # Preserve the base mandatory-field behaviour for every other field.
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.cond_hint, issue)
            self.delivery_date.setFocus()
            return False
        return True

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
            _set_status(self.penalty_warning, "")
            return
        try:
            float(text)
        except ValueError:
            _set_status(self.penalty_warning, "违约金/逾期利息应为数字，请核对。")
            return
        # No fixed ratio is asserted as a legal ceiling; whether a penalty is
        # excessive is decided by the court in light of the contract and actual
        # loss, so only a neutral manual-review reminder is shown.
        _set_status(
            self.penalty_warning,
            "提示：违约金（或逾期付款利息）是否过高、可否调整，由法院结合合同约定与实际损失判断，"
            "本工具不作绝对判断，请在提交前人工核对。",
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
        self.setTitle("填写案情与请求（民间借贷）")

        root = QVBoxLayout()

        # --- 一、借款基本事实 -------------------------------------------------
        basics = _section(root, "一、借款基本事实")

        self.loan_date = QLineEdit()
        self.loan_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-01")

        self.loan_reason = QLineEdit()
        self.loan_reason.setPlaceholderText("如: 资金周转 / 装修房屋")

        self.payment_method = QLineEdit()
        self.payment_method.setPlaceholderText("如: 银行转账、微信、支付宝、现金")

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

        basics.addRow("借款发生日期:", self.loan_date)
        basics.addRow("借款理由:", self.loan_reason)
        basics.addRow("交付方式:", self.payment_method)
        basics.addRow("是否有借条:", iou_layout)

        # --- 二、借款金额与利息 ---------------------------------------------
        amounts = _section(root, "二、借款金额与利息")

        self.principal = QLineEdit()
        self.principal.setPlaceholderText("单位：元，如 50000")
        _decimal_validator(self.principal)

        self.rate = QLineEdit()
        self.rate.setPlaceholderText("单位：%（留空表示无利息约定），如 14.6")
        _decimal_validator(self.rate)

        # Validation warning label
        self.rate_warning = QLabel("")
        self.rate_warning.setObjectName(REMINDER_LABEL)
        self.rate_warning.setWordWrap(True)
        self.rate_warning.setVisible(False)
        self.rate.textChanged.connect(self.validate_rate)

        self.start_date = QLineEdit()
        self.start_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-05-01")

        amounts.addRow("借款本金(元):", self.principal)
        amounts.addRow("约定年利率(%):", self.rate)
        amounts.addRow("", self.rate_warning)
        amounts.addRow("利息起算日:", self.start_date)

        # --- 三、催款情况（选填） -------------------------------------------
        demand = _section(root, "三、催款情况（选填）")

        self.demand_date = QLineEdit()
        self.demand_date.setPlaceholderText("如: 2023年10月（未催款的可不填）")

        self.demand_method = QLineEdit()
        self.demand_method.setPlaceholderText("如: 微信、电话、上门")

        # On-page explanation for the conditional demand-information requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setObjectName(WARNING_LABEL)
        self.cond_hint.setWordWrap(True)
        self.cond_hint.setVisible(False)

        demand.addRow("催款时间:", self.demand_date)
        demand.addRow("催款方式:", self.demand_method)
        demand.addRow("", self.cond_hint)

        # --- 四、建议管辖法院 ------------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 广州市天河区人民法院")
        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

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
        _set_status(self.cond_hint, self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.cond_hint, issue)
            self.demand_date.setFocus()
            return False
        return True

    def validate_rate(self):
        text = self.rate.text().strip()
        if not text:
            _set_status(self.rate_warning, "")
            return
        try:
            val = float(text)
        except ValueError:
            _set_status(self.rate_warning, "请输入有效的数字")
            return
        if val < 0:
            _set_status(self.rate_warning, "年利率不应为负数，请核对。")
        else:
            # No fixed universal ceiling is asserted here: the applicable limit
            # depends on the latest judicial guidance and the specific case, so
            # the tool only reminds the user to verify it manually.
            _set_status(
                self.rate_warning,
                "温馨提示：借款利率的可支持上限与适用规则会随最新司法口径、时间和地区变化，"
                "本工具不代为判断是否超限，请在提交前人工核对。",
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
        self.setTitle("填写案情与请求（物业服务合同）")

        root = QVBoxLayout()

        # Demo-mode badge, hidden in production.
        self.demo_badge = QLabel("演示模式")
        self.demo_badge.setObjectName(DEMO_BADGE)
        self.demo_badge.setVisible(False)
        root.addWidget(self.demo_badge)

        # Test-data entry point, only shown in demo mode (see set_demo_mode).
        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setObjectName(PRIMARY_BUTTON)
        self.fill_btn.setVisible(False)
        root.addWidget(self.fill_btn)

        # --- 一、物业与计费情况 ---------------------------------------------
        basic = _section(root, "一、物业与计费情况")

        self.property_addr = QLineEdit()
        self.property_addr.setPlaceholderText("如: 幸福里小区 3 栋 1201 室")

        self.house_area = QLineEdit()
        _decimal_validator(self.house_area)
        self.house_area.setPlaceholderText("如: 115.5")

        self.fee_rate = QLineEdit()
        _decimal_validator(self.fee_rate)
        self.fee_rate.setPlaceholderText("如: 2.8")

        self.period_start = QLineEdit()
        self.period_start.setPlaceholderText("格式 YYYY-MM-DD 或 YYYY年M月D日，如 2024-01-01")

        self.period_end = QLineEdit()
        self.period_end.setPlaceholderText("格式 YYYY-MM-DD 或 YYYY年M月D日，如 2025-12-31")

        basic.addRow("物业地址/房号:", self.property_addr)
        basic.addRow("房屋面积(m²):", self.house_area)
        basic.addRow("计费标准(元/m²/月):", self.fee_rate)
        basic.addRow("欠费起始日期:", self.period_start)
        basic.addRow("欠费截止日期:", self.period_end)

        # --- 二、违约金与催缴 -----------------------------------------------
        demand = _section(root, "二、违约金与催缴")

        self.late_fee_logic = QLineEdit()
        self.late_fee_logic.setPlaceholderText("如: 按合同约定计算 / 暂计 500 元")

        self.demand_record = QTextEdit()
        self.demand_record.setMaximumHeight(80)
        self.demand_record.setPlaceholderText("如: 2025年6月多次张贴催缴通知并发送短信。")

        demand.addRow("违约金/滞纳金计算:", self.late_fee_logic)
        demand.addRow("催缴方式:", self.demand_record)

        # --- 三、金额核对（系统计算） ---------------------------------------
        amount = _section(root, "三、金额核对（系统计算）")

        self.total_input = QLineEdit()
        _decimal_validator(self.total_input)
        self.total_input.setPlaceholderText("可选：用户自填总金额，用于与系统计算比对")

        self.calc_label = QLabel("")
        self.calc_label.setObjectName(INFO_LABEL)
        self.calc_label.setWordWrap(True)
        self.warn_label = QLabel("")
        self.warn_label.setObjectName(REMINDER_LABEL)
        self.warn_label.setWordWrap(True)
        self.warn_label.setVisible(False)

        amount.addRow("自填总金额(元):", self.total_input)
        amount.addRow("系统计算:", self.calc_label)
        amount.addRow("", self.warn_label)

        # --- 四、建议管辖法院 -----------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 上海市徐汇区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        for w in [self.house_area, self.fee_rate, self.period_start, self.period_end, self.total_input]:
            w.textChanged.connect(self.update_calc)

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
                        _set_status(self.warn_label, "提示：自填总金额与系统计算误差超过 1%，建议核对。")
                    else:
                        _set_status(self.warn_label, "")
                else:
                    _set_status(self.warn_label, "")
            else:
                _set_status(self.warn_label, "")
        except (InvalidOperation, ValueError):
            self.calc_label.setText("月数=0，总本金=0.00 元")
            _set_status(self.warn_label, "")

    def fill_test_data(self, notify=True):
        """Populate the property form with fictional data for demo mode."""
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
        if notify:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "物业纠纷测试数据已填入。")

    def set_demo_mode(self, enabled):
        """Show or hide the demo-mode badge and test-data button."""
        self.fill_btn.setVisible(enabled)
        self.demo_badge.setVisible(enabled)

class EvidencePage(QWizardPage):
    # A faint background tint for rows loaded from EvidenceLibrary so the user
    # can tell suggested evidence apart from rows they added themselves.  The
    # tint is purely visual — get_evidence_items() returns the same structure.
    _SUGGESTED_TINT = QBrush(QColor(245, 248, 252))

    def __init__(self):
        super().__init__()
        self.setTitle("证据清单（选填）")

        layout = QVBoxLayout()
        self.desc_label = QLabel("请列出您准备提交的证据。")
        layout.addWidget(self.desc_label)

        self.edit_hint = QLabel("双击任意单元格即可编辑证据名称或证明目的。")
        self.edit_hint.setObjectName(INFO_LABEL)
        self.edit_hint.setWordWrap(True)
        layout.addWidget(self.edit_hint)

        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("[+] 添加证据")
        self.add_row_btn.setAccessibleName("添加证据行")
        self.add_row_btn.clicked.connect(self.add_row)
        self.remove_row_btn = QPushButton("[-] 删除选中行")
        self.remove_row_btn.setAccessibleName("删除选中的证据行")
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.remove_row_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        layout.addWidget(btn_widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["证据名称", "证明目的"])
        self.table.setAccessibleName("证据清单表格")
        self.table.setAccessibleDescription("可编辑表格，双击单元格编辑证据名称和证明目的")
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked | QTableWidget.EditTrigger.EditKeyPressed)
        layout.addWidget(self.table)

        # Number of rows that came from EvidenceLibrary suggestions.  Rows beyond
        # this count were added by the user and are not tinted.
        self._suggested_count = 0

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
            elif case_type == "labor":
                self.desc_label.setText("劳动报酬/工资追索常见证据（可按需修改/增删）：")
            elif case_type == "divorce":
                self.desc_label.setText("离婚纠纷常见证据（可按需修改/增删）：")
            else:
                self.desc_label.setText("常见证据（可按需修改/增删）：")
            if self.table.rowCount() == 0:
                self._suggested_count = 0
                for name, target in items:
                    self.add_row(name, target, suggested=True)
        except Exception:
            return

    def add_row(self, name="", target="", suggested=False, auto_edit=True):
        """Append a row and optionally start editing the first cell.

        ``suggested=True`` tints the row so the user can distinguish
        EvidenceLibrary defaults from rows they added.  ``auto_edit=True``
        puts the cursor straight into the first cell so the user can type
        without a second click.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(str(name))
        target_item = QTableWidgetItem(str(target))
        if suggested:
            name_item.setBackground(self._SUGGESTED_TINT)
            target_item.setBackground(self._SUGGESTED_TINT)
            self._suggested_count += 1
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, target_item)
        if auto_edit and not suggested:
            self.table.setCurrentItem(name_item)
            self.table.editItem(name_item)

    def remove_selected_rows(self):
        """Remove selected rows, confirming only when content would be lost."""
        from PySide6.QtWidgets import QMessageBox

        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            return

        has_content = False
        for r in rows:
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and item.text().strip():
                    has_content = True
                    break
            if has_content:
                break

        if has_content:
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"将删除 {len(rows)} 行证据，确定吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        for r in rows:
            self.table.removeRow(r)
            if r < self._suggested_count:
                self._suggested_count = max(0, self._suggested_count - 1)

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
        self.setTitle("填写案情与请求（劳动报酬／工资追索）")

        root = QVBoxLayout()

        # Persistent arbitration-precondition notice with an explicit basis
        # time, so the page never reads as a universally current conclusion.
        from utils.labor_security import LaborProcedureGuard
        self.arbitration_notice = QLabel(LaborProcedureGuard().get_persistent_notice())
        self.arbitration_notice.setObjectName(REMINDER_LABEL)
        self.arbitration_notice.setWordWrap(True)
        root.addWidget(self.arbitration_notice)

        # --- 一、劳动关系基本事实 -------------------------------------------
        basic = _section(root, "一、劳动关系基本事实")

        self.emp_join_date = QLineEdit()
        self.emp_join_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-15")

        self.job_title = QLineEdit()
        self.job_title.setPlaceholderText("如: 软件工程师")

        self.monthly_salary = QLineEdit()
        _decimal_validator(self.monthly_salary)
        self.monthly_salary.setPlaceholderText("如: 8000")

        self.emp_term_date = QLineEdit()
        self.emp_term_date.setPlaceholderText("格式 YYYY-MM-DD，如 2024-03-20")

        basic.addRow("入职日期:", self.emp_join_date)
        basic.addRow("岗位:", self.job_title)
        basic.addRow("月工资标准(元):", self.monthly_salary)
        basic.addRow("离职/截止日期:", self.emp_term_date)

        # --- 二、欠薪与加班 -------------------------------------------------
        unpaid = _section(root, "二、欠薪与加班")

        self.unpaid_months = QLineEdit()
        self.unpaid_months.setPlaceholderText("如: 2023年12月至2024年2月（整月区间）")

        self.overtime_hours = QLineEdit()
        _decimal_validator(self.overtime_hours)
        self.overtime_hours.setPlaceholderText("如: 40（选填）")

        self.overtime_pay = QLineEdit()
        _decimal_validator(self.overtime_pay)
        self.overtime_pay.setPlaceholderText("如: 3500（选填）")

        unpaid.addRow("欠薪月份/区间:", self.unpaid_months)
        unpaid.addRow("加班工时(小时，选填):", self.overtime_hours)
        unpaid.addRow("加班费(元，选填):", self.overtime_pay)

        # --- 三、合同与社保 -------------------------------------------------
        contract = _section(root, "三、合同与社保")

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
        self.social_sec_info.setPlaceholderText("如: 未按实际工资基数缴纳（选填）")

        contract.addRow("是否未签劳动合同:", no_contract_layout)
        contract.addRow("社保缴纳情况:", self.social_sec_info)

        # --- 四、建议管辖法院 -----------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

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
        self.setTitle("填写案情与请求（离婚析产／抚养费纠纷）")

        root = QVBoxLayout()

        # --- 一、婚姻与离婚原因 ---------------------------------------------
        marriage = _section(root, "一、婚姻与离婚原因")

        self.marriage_date = QLineEdit()
        self.marriage_date.setPlaceholderText("格式 YYYY-MM-DD，如 2018-05-20")

        self.divorce_reason = QLineEdit()
        self.divorce_reason.setPlaceholderText("如: 感情不和/长期分居")

        self.separation_start_date = QLineEdit()
        self.separation_start_date.setPlaceholderText("格式 YYYY-MM-DD，如 2022-01-01")

        marriage.addRow("登记结婚日期:", self.marriage_date)
        marriage.addRow("离婚原因:", self.divorce_reason)
        marriage.addRow("分居起始日期:", self.separation_start_date)

        # --- 二、子女与抚养（无子女可留空） ---------------------------------
        child = _section(root, "二、子女与抚养（无子女可留空）")

        self.child_name = QLineEdit()
        self.child_name.setPlaceholderText("如: 张三")

        self.child_birthday = QLineEdit()
        self.child_birthday.setPlaceholderText("格式 YYYY-MM-DD，如 2020-01-01")

        self.custody_preference = QLineEdit()
        self.custody_preference.setPlaceholderText("如: 由原告抚养")

        self.support_monthly = QLineEdit()
        _decimal_validator(self.support_monthly)
        self.support_monthly.setPlaceholderText("如: 3000")

        # Persistent guidance clarifying the conditional relationship: a
        # childless divorce may leave every child-related field blank, but any
        # one of them requires the child's name to identify the child.
        self.child_help = QLabel(
            "无子女的离婚可不填本组任何字段；若填写出生日期、抚养权或抚养费，"
            "需同时填写子女姓名。"
        )
        self.child_help.setObjectName(INFO_LABEL)
        self.child_help.setWordWrap(True)

        # On-page explanation for the conditional child-information requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setObjectName(WARNING_LABEL)
        self.cond_hint.setWordWrap(True)
        self.cond_hint.setVisible(False)

        child.addRow("子女姓名:", self.child_name)
        child.addRow("子女出生日期:", self.child_birthday)
        child.addRow("抚养权诉求:", self.custody_preference)
        child.addRow("月抚养费金额(元):", self.support_monthly)
        child.addRow("", self.child_help)
        child.addRow("", self.cond_hint)

        # --- 三、财产分割 ---------------------------------------------------
        asset = _section(root, "三、财产分割")

        self.asset_description = QLineEdit()
        self.asset_description.setPlaceholderText("如: 房产归原告，车辆归被告")

        asset.addRow("财产分割方案:", self.asset_description)

        # --- 四、建议管辖法院 -----------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

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
        _set_status(self.cond_hint, self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.cond_hint, issue)
            self.child_name.setFocus()
            return False
        return True

class _PreviewDialog(QDialog):
    """A scrollable, read-only preview of the case text before export.

    The dialog explicitly states that the preview is plain text only and does
    not represent the final Word layout (fonts, tables, headers, page breaks).
    """

    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)

        disclaimer = QLabel(
            "以下预览仅展示文本内容，不代表最终 Word 排版"
            "（字体、表格、页眉页脚、分页等）。"
        )
        disclaimer.setObjectName(INFO_LABEL)
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        layout.addWidget(viewer)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ExportPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("核对与导出")
        # Ensure it acts as the final page
        self.setFinalPage(True)

        # Default output directory: the current user's desktop.
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        layout = QVBoxLayout()

        intro = QLabel("信息收集完毕，请核对以下内容后生成文书。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # --- Three document descriptions ----------------------------------
        doc_group = QGroupBox("将生成的文书")
        doc_layout = QVBoxLayout()
        for name in (
            "民事起诉状（可编辑 Word 初稿）",
            "证据清单（可编辑 Word 初稿）",
            "送达地址确认书（可编辑 Word 初稿）",
        ):
            doc_label = QLabel(name)
            doc_layout.addWidget(doc_label)
        doc_note = QLabel("以上文书均为辅助生成的可编辑初稿，请人工核对后再行使用。")
        doc_note.setObjectName(INFO_LABEL)
        doc_note.setWordWrap(True)
        doc_layout.addWidget(doc_note)
        doc_group.setLayout(doc_layout)
        layout.addWidget(doc_group)

        # --- Output directory ---------------------------------------------
        dir_group = QGroupBox("保存位置")
        dir_layout = QVBoxLayout()
        self.dir_label = QLabel(self.output_dir)
        self.dir_label.setWordWrap(True)
        dir_layout.addWidget(self.dir_label)

        dir_btn_layout = QHBoxLayout()
        self.change_dir_btn = QPushButton("更改目录")
        self.change_dir_btn.setObjectName(SECONDARY_BUTTON)
        self.change_dir_btn.setAccessibleName("更改输出目录")
        self.change_dir_btn.clicked.connect(self.change_directory)
        dir_btn_layout.addWidget(self.change_dir_btn)

        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.setObjectName(SECONDARY_BUTTON)
        self.open_dir_btn.setAccessibleName("打开输出目录")
        self.open_dir_btn.clicked.connect(self.open_output_directory)
        dir_btn_layout.addWidget(self.open_dir_btn)
        dir_btn_layout.addStretch()
        dir_btn_widget = QWidget()
        dir_btn_widget.setLayout(dir_btn_layout)
        dir_layout.addWidget(dir_btn_widget)

        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # --- Preview -------------------------------------------------------
        self.preview_btn = QPushButton("预览关键信息")
        self.preview_btn.setObjectName(SECONDARY_BUTTON)
        self.preview_btn.setAccessibleName("预览关键信息")
        self.preview_btn.clicked.connect(self.show_preview)
        layout.addWidget(self.preview_btn)

        # --- Exit (secondary, not destructive) ----------------------------
        self.secure_exit_btn = QPushButton("退出程序（不删除已生成文件）")
        self.secure_exit_btn.setObjectName(SECONDARY_BUTTON)
        self.secure_exit_btn.setAccessibleName("退出程序")
        self.secure_exit_btn.clicked.connect(self.secure_exit)
        layout.addWidget(self.secure_exit_btn)

        self.setLayout(layout)

    # ------------------------------------------------------------------ #
    # Output directory
    # ------------------------------------------------------------------ #

    def get_output_directory(self):
        """Return the currently configured output directory."""
        return self.output_dir

    def change_directory(self):
        """Let the user pick a different output directory via a file dialog."""
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "选择保存目录",
            self.output_dir,
        )
        if new_dir:
            self.output_dir = new_dir
            self.dir_label.setText(new_dir)

    def open_output_directory(self):
        """Open the configured output directory in the system file explorer."""
        path = self.output_dir
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Preview
    # ------------------------------------------------------------------ #

    def show_preview(self):
        """Show a case-specific preview in a scrollable dialog."""
        from PySide6.QtWidgets import QMessageBox

        from views.widgets import CASE_TYPE_LABELS

        wizard = self.wizard()
        case_type = wizard.field("case_type")
        label = CASE_TYPE_LABELS.get(case_type, "未知案由")

        try:
            from presenters.model_builder import build_case_model
            model = build_case_model(wizard)
            claims = model.render_claims()
            facts = model.render_facts()
        except Exception as exc:  # a preview failure must never crash the wizard
            QMessageBox.warning(self, "预览不可用", f"暂时无法生成“{label}”预览：\n{exc}")
            return

        claims_text = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))

        evidence_lines = []
        for i, ev in enumerate(getattr(model, "evidences", []), 1):
            name = getattr(ev, "name", str(ev))
            target = getattr(ev, "target", "")
            if target:
                evidence_lines.append(f"{i}. {name} —— {target}")
            else:
                evidence_lines.append(f"{i}. {name}")
        evidence_text = "\n".join(evidence_lines) if evidence_lines else "（未填写证据）"

        preview_text = (
            f"案由：{label}\n\n"
            f"【诉讼请求（预览）】\n{claims_text}\n\n"
            f"【事实与理由（预览）】\n{facts}\n\n"
            f"【证据清单（预览）】\n{evidence_text}"
        )

        # Stash the text so tests can inspect it without a modal dialog.
        self._last_preview_text = preview_text

        dialog = _PreviewDialog("关键信息预览", preview_text, self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    # Exit
    # ------------------------------------------------------------------ #

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
