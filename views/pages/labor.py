# File: views/pages/labor.py
# Purpose: Labour-compensation claim page (arbitration notice, unpaid period).
# Encoding: UTF-8
"""Labour-compensation claim page with the persistent arbitration-precondition
notice and the no-written-contract tri-state."""

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QVBoxLayout
from views.theme import REMINDER_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _wrap_in_scroll,
)

class LaborClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（劳动报酬／工资追索）")

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
