# File: views/pages/contract.py
# Purpose: Sales-contract claim page (tri-states, penalty calculators, provenance).
# Encoding: UTF-8
"""Sales-contract claim page: delivery/receipt tri-states, the auxiliary
penalty calculators (thin adapters over ``models.calculations``), their
provenance recording and the conditional delivery-date requirement."""

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from models.calculations import (
    CalculationError,
    calculate_daily_penalty,
    calculate_lpr_penalty,
    format_money,
    parse_decimal,
)
from models.validation import DateStatus, ValidationResult, ValidationStatus, parse_full_date
from views.theme import INFO_LABEL, REMINDER_LABEL, SECONDARY_BUTTON, WARNING_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)

class ContractClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（买卖合同）")

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
        self.lpr_value.setPlaceholderText("LPR(%)，示例值需自行核实")
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
            "LPR 与倍数是本工具内置的示例参数（不联网更新），不代表当前适用的"
            "官方利率，请在提交前自行核实后再使用。"
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

        # Auxiliary-calculation provenance: the generated claim may only state
        # a cutoff date while the penalty amount is the untouched result of a
        # calculator run with unchanged inputs. Any later manual edit (of the
        # amount or of a calculation input) clears the recorded basis.
        self._penalty_calc_basis = None
        self._applying_penalty_calc = False
        for widget in (self.unpaid_amount, self.overdue_start, self.overdue_end,
                       self.lpr_value, self.lpr_multiple):
            widget.textChanged.connect(self._invalidate_penalty_basis)
        self.penalty_amount.textChanged.connect(self._on_penalty_amount_edited)

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
        # Shared finite-Decimal validation: NaN/Infinity/negative never read as
        # a valid monetary value; the text stays visible and editable.
        try:
            value = parse_decimal(text, "违约金/逾期利息")
        except CalculationError:
            _set_status(self.penalty_warning, "违约金/逾期利息应为数字，请核对。")
            return
        if value < 0:
            _set_status(self.penalty_warning, "违约金/逾期利息不应为负数，请核对。")
            return
        # No fixed ratio is asserted as a legal ceiling; whether a penalty is
        # excessive is decided by the court in light of the contract and actual
        # loss, so only a neutral manual-review reminder is shown.
        _set_status(
            self.penalty_warning,
            "提示：违约金（或逾期付款利息）是否过高、可否调整，由法院结合合同约定与实际损失判断，"
            "本工具不作绝对判断，请在提交前人工核对。",
        )

    def _resolve_overdue_cutoff(self):
        """Resolve the penalty calculators' date interval explicitly.

        Returns ``(start, cutoff, error_result)``. Dates go through the shared
        full-date validation, so malformed input is distinguished from blank
        input: an unparseable explicit cutoff is reported as an error instead
        of silently falling back to today's date, while a blank cutoff keeps
        the existing calculation-day contract. Never raises.
        """
        import datetime

        start_result = parse_full_date(self.overdue_start.text())
        if start_result.status != DateStatus.VALID:
            status = (
                ValidationStatus.REQUIRED_MISSING
                if start_result.status == DateStatus.EMPTY
                else ValidationStatus.INVALID_FORMAT
            )
            return None, None, ValidationResult(
                "c_overdue_start", status, "OVERDUE_START_INVALID",
                "请填写正确的逾期起算日（格式 YYYY-MM-DD）。",
            )
        start = start_result.value

        end_result = parse_full_date(self.overdue_end.text())
        if end_result.status == DateStatus.EMPTY:
            cutoff = datetime.date.today()
        elif end_result.status == DateStatus.VALID:
            cutoff = end_result.value
        else:
            return None, None, ValidationResult(
                "c_overdue_end", ValidationStatus.INVALID_FORMAT, "OVERDUE_END_INVALID",
                "违约金计算截止日格式无法识别（格式 YYYY-MM-DD），请修正后再计算。",
            )
        if cutoff < start:
            return None, None, ValidationResult(
                "c_overdue_end", ValidationStatus.INVALID_RANGE, "OVERDUE_REVERSED",
                "违约金计算截止日早于起算日，请核对后重新填写。",
            )
        return start, cutoff, None

    def _invalidate_penalty_basis(self, *_):
        """A manual edit of a calculation input invalidates the recorded basis."""
        if self._applying_penalty_calc:
            return
        self._penalty_calc_basis = None

    def _on_penalty_amount_edited(self, *_):
        self.update_penalty_warning()
        if not self._applying_penalty_calc:
            self._penalty_calc_basis = None

    def _apply_calculated_penalty(self, text, method, cutoff):
        """Fill the penalty box from an auxiliary calculator and record its basis."""
        self._applying_penalty_calc = True
        try:
            self.penalty_amount.setText(text)
        finally:
            self._applying_penalty_calc = False
        self._penalty_calc_basis = {"method": method, "cutoff": cutoff.isoformat()}
        self.update_penalty_warning()

    def get_penalty_calc_basis(self):
        """Return the recorded auxiliary-calculation basis, or ``None``.

        The basis exists only while the penalty amount is the untouched result
        of a calculator run with unchanged inputs; it carries the calculation
        method and the cutoff date that computation actually used, so the
        exported claim can describe it truthfully.
        """
        if not self._penalty_calc_basis:
            return None
        return dict(self._penalty_calc_basis)

    def calc_penalty_daily_5_per_10k(self):
        """Thin adapter: read inputs, call the pure calculator, show or record."""
        from PySide6.QtWidgets import QMessageBox
        try:
            start, cutoff, error = self._resolve_overdue_cutoff()
            if error is not None:
                QMessageBox.warning(self, "提示", error.message)
                return
            result = calculate_daily_penalty(self.unpaid_amount.text(), start, cutoff)
        except CalculationError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            return
        except Exception:
            QMessageBox.warning(self, "提示", "请先填写有效的“尚欠货款本金(元)”与日期(YYYY-MM-DD)。")
            return
        self._apply_calculated_penalty(format_money(result.amount), result.method, result.cutoff)

    def calc_penalty_by_lpr_multiple(self):
        """Thin adapter: read inputs, call the pure calculator, show or record."""
        from PySide6.QtWidgets import QMessageBox
        try:
            start, cutoff, error = self._resolve_overdue_cutoff()
            if error is not None:
                QMessageBox.warning(self, "提示", error.message)
                return
            result = calculate_lpr_penalty(
                self.unpaid_amount.text(),
                self.lpr_value.text(),
                self.lpr_multiple.text(),
                start,
                cutoff,
            )
        except CalculationError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            return
        except Exception:
            QMessageBox.warning(self, "提示", "请先填写有效的本金、LPR、倍数与日期(YYYY-MM-DD)。")
            return
        self._apply_calculated_penalty(format_money(result.amount), result.method, result.cutoff)
