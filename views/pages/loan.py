# File: views/pages/loan.py
# Purpose: Private-lending claim page (rate validation, IOU tri-state).
# Encoding: UTF-8
"""Private-lending claim page: interest-rate validation through the shared
Decimal contract, IOU tri-state, optional demand pairing and the neutral
repayment-history limitation notice."""

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QVBoxLayout
from models.calculations import validate_rate_text
from models.validation import ValidationStatus
from views.theme import INFO_LABEL, REMINDER_LABEL, WARNING_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)

class LoanClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（民间借贷）")

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

        # Neutral limitation note (no legal conclusion): the current model
        # claims the full principal and has no repayment-history fields, so
        # users with partial repayments must adjust the amount themselves.
        self.repayment_hint = QLabel(
            "说明：当前版本按出借本金全额主张，暂不支持登记已还款记录；"
            "如存在部分还款，请自行调整本金金额并在诉讼中如实说明。"
        )
        self.repayment_hint.setObjectName(INFO_LABEL)
        self.repayment_hint.setWordWrap(True)
        amounts.addRow("", self.repayment_hint)

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
        """Validate the rate through the shared structured validation contract."""
        result = validate_rate_text(self.rate.text())
        if result.status == ValidationStatus.INVALID_FORMAT:
            _set_status(self.rate_warning, result.message)
            return
        if result.status == ValidationStatus.INVALID_RANGE:
            _set_status(self.rate_warning, result.message)
            return
        if result.status == ValidationStatus.EMPTY_ALLOWED:
            _set_status(self.rate_warning, "")
            return
        # VALID: no fixed universal ceiling is asserted here: the applicable limit
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
