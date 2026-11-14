# File: views/pages/labor.py
# Purpose: Labour-compensation claim page (arbitration posture, unpaid period).
# Encoding: UTF-8
"""Labour-compensation claim page with the persistent arbitration-precondition
notice, the arbitration-posture gate and the no-written-contract tri-state."""

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QVBoxLayout
from views.theme import REMINDER_LABEL, WARNING_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)


def _tri_state_group(owner, yes_text, no_text):
    """Return ``(group, yes, no, unknown, layout)`` with "未确认" preselected."""
    group = QButtonGroup(owner)
    yes = QRadioButton(yes_text)
    no = QRadioButton(no_text)
    unknown = QRadioButton("未确认")
    group.addButton(yes, 1)
    group.addButton(no, 0)
    group.addButton(unknown, 2)
    unknown.setChecked(True)
    layout = QHBoxLayout()
    for button in (yes, no, unknown):
        layout.addWidget(button)
    return group, yes, no, unknown, layout


def _tri_state_value(group):
    checked = group.checkedId()
    if checked == 1:
        return True
    if checked == 0:
        return False
    return None


class LaborClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（劳动报酬／工资追索）")

        root = QVBoxLayout()

        # Persistent arbitration-precondition notice with an explicit basis
        # time, so the page never reads as a universally current conclusion.
        from utils.labor_security import LaborProcedureGuard
        self._guard = LaborProcedureGuard()
        self.arbitration_notice = QLabel(self._guard.get_persistent_notice())
        self.arbitration_notice.setObjectName(REMINDER_LABEL)
        self.arbitration_notice.setWordWrap(True)
        root.addWidget(self.arbitration_notice)

        # --- 一、仲裁情况 ---------------------------------------------------
        arbitration = _section(root, "一、仲裁情况")

        (self.arbitrated_group, self.arbitrated_yes, self.arbitrated_no,
         self.arbitrated_unknown, arbitrated_layout) = _tri_state_group(
            self, "已仲裁（已收到裁决或不予受理通知）", "尚未申请仲裁")

        self.arb_commission = QLineEdit()
        self.arb_commission.setPlaceholderText("如: 北京市朝阳区劳动人事争议仲裁委员会")

        self.arb_case_no = QLineEdit()
        self.arb_case_no.setPlaceholderText("如: 京朝劳人仲字〔2024〕第1号（选填）")

        self.arb_receipt_date = QLineEdit()
        self.arb_receipt_date.setPlaceholderText("收到裁决书/通知书的日期，格式 YYYY-MM-DD")

        self.arbitration_hint = QLabel("")
        self.arbitration_hint.setObjectName(WARNING_LABEL)
        self.arbitration_hint.setWordWrap(True)
        self.arbitration_hint.setVisible(False)

        # The three long options need the full row width.
        posture_row = QHBoxLayout()
        posture_row.addWidget(QLabel("是否已经劳动仲裁:"))
        posture_row.addLayout(arbitrated_layout)
        posture_row.addStretch(1)

        arbitration.addRow(posture_row)
        arbitration.addRow("仲裁机构:", self.arb_commission)
        arbitration.addRow("仲裁案号:", self.arb_case_no)
        arbitration.addRow("收到裁决日期:", self.arb_receipt_date)
        arbitration.addRow("", self.arbitration_hint)

        # --- 二、劳动关系基本事实 -------------------------------------------
        basic = _section(root, "二、劳动关系基本事实")

        self.emp_join_date = QLineEdit()
        self.emp_join_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-15")

        self.job_title = QLineEdit()
        self.job_title.setPlaceholderText("如: 软件工程师")

        self.monthly_salary = QLineEdit()
        _decimal_validator(self.monthly_salary)
        self.monthly_salary.setPlaceholderText("如: 8000")

        self.emp_term_date = QLineEdit()
        self.emp_term_date.setPlaceholderText("格式 YYYY-MM-DD（仍在职可不填）")

        basic.addRow("入职日期:", self.emp_join_date)
        basic.addRow("岗位:", self.job_title)
        basic.addRow("月工资标准(元):", self.monthly_salary)
        basic.addRow("离职/截止日期:", self.emp_term_date)

        # --- 三、欠薪与加班 -------------------------------------------------
        unpaid = _section(root, "三、欠薪与加班")

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

        # --- 四、合同与社保 -------------------------------------------------
        contract = _section(root, "四、合同与社保")

        # Tri-state like every other factual confirmation: an untouched control
        # is "未确认" and never asserts that a written contract was missing.
        (self.is_no_contract_group, self.no_contract_yes, self.no_contract_no,
         self.no_contract_unknown, no_contract_layout) = _tri_state_group(self, "是", "否")

        self.social_sec_info = QLineEdit()
        self.social_sec_info.setPlaceholderText("如: 未按实际工资基数缴纳（选填）")

        contract.addRow("是否未签劳动合同:", no_contract_layout)
        contract.addRow("社保缴纳情况:", self.social_sec_info)

        # --- 五、建议管辖法院 -----------------------------------------------
        court = _section(root, "五、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        self.registerField("l_emp_join_date*", self.emp_join_date)
        self.registerField("l_job_title*", self.job_title)
        self.registerField("l_monthly_salary*", self.monthly_salary)
        self.registerField("l_unpaid_months*", self.unpaid_months)
        self.registerField("l_emp_term_date", self.emp_term_date)
        self.registerField("l_overtime_hours", self.overtime_hours)
        self.registerField("l_overtime_pay", self.overtime_pay)
        self.registerField("l_social_sec_info", self.social_sec_info)
        self.registerField("l_court_name*", self.court_name)
        # Required only once arbitration is confirmed (enforced by isComplete()).
        self.registerField("l_arb_commission", self.arb_commission)
        self.registerField("l_arb_case_no", self.arb_case_no)
        self.registerField("l_arb_receipt_date", self.arb_receipt_date)

        self.arbitrated_group.buttonToggled.connect(lambda *_: self._refresh_conditional())
        for widget in (self.arb_commission, self.arb_receipt_date):
            widget.textChanged.connect(lambda *_: self._refresh_conditional())
        self._refresh_conditional()

    def _conditional_issue(self):
        """A complaint is only generated after a completed arbitration."""
        status = self.get_has_arbitrated()
        if status is None:
            return "请先确认是否已经申请劳动仲裁。"
        if status is False:
            return self._guard.get_not_arbitrated_text()
        missing = []
        if not self.arb_commission.text().strip():
            missing.append("仲裁机构")
        if not self.arb_receipt_date.text().strip():
            missing.append("收到裁决日期")
        if missing:
            return "已选择“已仲裁”，请填写" + "、".join(missing) + "。"
        return ""

    def _refresh_conditional(self):
        _set_status(self.arbitration_hint, self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.arbitration_hint, issue)
            self.arbitrated_yes.setFocus()
            return False
        return True

    def get_has_arbitrated(self):
        """Return ``True`` / ``False`` / ``None`` (unconfirmed) arbitration status."""
        return _tri_state_value(self.arbitrated_group)

    def get_has_no_contract(self):
        """Return ``True`` / ``False`` / ``None`` (unconfirmed) no-contract status."""
        return _tri_state_value(self.is_no_contract_group)
