# File: views/main_window.py
# Purpose: Main application window integrating the Wizard
# Encoding: UTF-8

from PySide6.QtWidgets import QAbstractButton, QWizard
from views.wizard_pages import WelcomePage, CaseSelectionPage, PartyPage, LoanClaimPage, ContractClaimPage, PropertyClaimPage, LaborClaimPage, DivorceClaimPage, EvidencePage, ExportPage

class LawsuitWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("民事立案文书助手（离线版）")
        self.resize(700, 650)
        self.setWizardStyle(QWizard.ModernStyle)

        # Qt's QWizard creates an internal, unnamed 32x32 QAbstractButton at the
        # top-left of the header area. On Windows it renders as a stray "back"
        # arrow overlapping the page title, and it has no function here because
        # navigation is provided by the standard Back/Next/Cancel bar. Hide it
        # (and keep it hidden across page changes) without touching the real
        # navigation buttons, which are not direct children of the wizard.
        for child in self.children():
            if isinstance(child, QAbstractButton) and not child.text() and not child.objectName():
                child.hide()
        self.currentIdChanged.connect(self._hide_internal_wizard_buttons)

        # Define Page IDs
        self.PAGE_WELCOME = 0
        self.PAGE_CASE_SELECTION = 1
        self.PAGE_PARTY = 2
        self.PAGE_LOAN_CLAIM = 3
        self.PAGE_CONTRACT_CLAIM = 4
        self.PAGE_PROPERTY_CLAIM = 5
        self.PAGE_LABOR_CLAIM = 6
        self.PAGE_DIVORCE_CLAIM = 7
        self.PAGE_EVIDENCE = 8
        self.PAGE_EXPORT = 9

        # Add pages
        self.welcome_page = WelcomePage()
        self.case_selection_page = CaseSelectionPage()
        self.party_page = PartyPage()
        self.loan_claim_page = LoanClaimPage()
        self.contract_claim_page = ContractClaimPage()
        self.property_claim_page = PropertyClaimPage()
        self.labor_claim_page = LaborClaimPage()
        self.divorce_claim_page = DivorceClaimPage()
        self.evidence_page = EvidencePage()
        self.export_page = ExportPage()

        self.setPage(self.PAGE_WELCOME, self.welcome_page)
        self.setPage(self.PAGE_CASE_SELECTION, self.case_selection_page)
        self.setPage(self.PAGE_PARTY, self.party_page)
        self.setPage(self.PAGE_LOAN_CLAIM, self.loan_claim_page)
        self.setPage(self.PAGE_CONTRACT_CLAIM, self.contract_claim_page)
        self.setPage(self.PAGE_PROPERTY_CLAIM, self.property_claim_page)
        self.setPage(self.PAGE_LABOR_CLAIM, self.labor_claim_page)
        self.setPage(self.PAGE_DIVORCE_CLAIM, self.divorce_claim_page)
        self.setPage(self.PAGE_EVIDENCE, self.evidence_page)
        self.setPage(self.PAGE_EXPORT, self.export_page)

        # Set start page
        self.setStartId(self.PAGE_WELCOME)

        # The presenter registers a Finish handler that performs the export
        # before the wizard commits to its accepted (closed) state.
        self.finish_handler = None

        # Connect template fill button
        self.welcome_page.fill_btn.clicked.connect(self.fill_template_data)

    def _hide_internal_wizard_buttons(self, *_):
        """Keep Qt's internal header button hidden across page changes."""
        for child in self.children():
            if isinstance(child, QAbstractButton) and not child.text() and not child.objectName():
                child.hide()

    def nextId(self):
        current = self.currentId()
        if current == self.PAGE_WELCOME:
            return self.PAGE_CASE_SELECTION

        elif current == self.PAGE_CASE_SELECTION:
            return self.PAGE_PARTY

        elif current == self.PAGE_PARTY:
            case_type = self.field("case_type")
            if case_type == "contract":
                return self.PAGE_CONTRACT_CLAIM
            elif case_type == "property":
                return self.PAGE_PROPERTY_CLAIM
            elif case_type == "labor":
                return self.PAGE_LABOR_CLAIM
            elif case_type == "divorce":
                return self.PAGE_DIVORCE_CLAIM
            else:
                return self.PAGE_LOAN_CLAIM

        elif current == self.PAGE_LOAN_CLAIM or current == self.PAGE_CONTRACT_CLAIM or current == self.PAGE_PROPERTY_CLAIM or current == self.PAGE_LABOR_CLAIM or current == self.PAGE_DIVORCE_CLAIM:
            return self.PAGE_EVIDENCE

        elif current == self.PAGE_EVIDENCE:
            return self.PAGE_EXPORT

        elif current == self.PAGE_EXPORT:
            return -1

        return super().nextId()

    def set_finish_handler(self, handler):
        """Register the pre-accept export step supplied by the presenter."""
        self.finish_handler = handler

    def accept(self):
        """Run the export before accepting, so a failure keeps the wizard open.

        The real QWizard "Finish" button routes through this method. Only a
        successful export advances to Qt's normal accepted (closed) state.
        """
        handler = getattr(self, "finish_handler", None)
        if callable(handler) and not handler():
            return  # keep the wizard open so the user can correct and retry
        super().accept()

    def fill_template_data(self):
        """Auto-fill data for testing purposes"""
        # Get current case type
        case_type = self.field("case_type")

        # Page 1: Party Info
        if self.party_page.plaintiff_widgets:
            self.party_page.plaintiff_widgets[0]["name"].setText("张三")
            self.party_page.plaintiff_widgets[0]["id"].setText("示例证件号-原告")
            self.party_page.plaintiff_widgets[0]["addr"].setText("北京市朝阳区某某路1号")
            self.party_page.plaintiff_widgets[0]["phone"].setText("示例电话-原告")

        if self.party_page.defendant_widgets:
            self.party_page.defendant_widgets[0]["name"].setText("李四")
            self.party_page.defendant_widgets[0]["id"].setText("示例证件号-被告")
            self.party_page.defendant_widgets[0]["addr"].setText("上海市徐汇区某某街2号")
            self.party_page.defendant_widgets[0]["phone"].setText("示例电话-被告")

        # Page 2: Claim Info - Fill based on case type
        if case_type == "loan":
            self.loan_claim_page.loan_date.setText("2023年1月1日")
            self.loan_claim_page.loan_reason.setText("资金周转")
            self.loan_claim_page.principal.setText("50000")
            self.loan_claim_page.payment_method.setText("银行转账")
            self.loan_claim_page.rate.setText("14.6")
            self.loan_claim_page.start_date.setText("2023-05-01")
            self.loan_claim_page.iou_yes.setChecked(True)
            self.loan_claim_page.demand_date.setText("2023年10月至12月")
            self.loan_claim_page.demand_method.setText("微信及电话")
            self.loan_claim_page.court_name.setText("上海市徐汇区人民法院")

        elif case_type == "contract":
            self.contract_claim_page.contract_date.setText("2023年1月1日")
            self.contract_claim_page.contract_name.setText("产品购销合同")
            self.contract_claim_page.product_name.setText("10台联想电脑")
            self.contract_claim_page.total_amount.setText("50000")
            self.contract_claim_page.delivery_date.setText("2023年2月1日")
            self.contract_claim_page.del_yes.setChecked(True)
            self.contract_claim_page.sign_yes.setChecked(True)
            self.contract_claim_page.unpaid_amount.setText("30000")
            self.contract_claim_page.penalty_amount.setText("5000")
            self.contract_claim_page.overdue_start.setText("2023-03-01")
            self.contract_claim_page.overdue_end.setText("")
            self.contract_claim_page.court_name.setText("上海市徐汇区人民法院")

        elif case_type == "property":
            self.property_claim_page.property_addr.setText("幸福里小区 3 栋 1201 室")
            self.property_claim_page.house_area.setText("115.5")
            self.property_claim_page.fee_rate.setText("2.8")
            self.property_claim_page.period_start.setText("2024-01-01")
            self.property_claim_page.period_end.setText("2025-12-31")
            self.property_claim_page.late_fee_logic.setText("按合同约定计算")
            self.property_claim_page.demand_record.setPlainText("2025年6月多次张贴催缴通知、发送短信。")
            self.property_claim_page.total_input.setText("")
            self.property_claim_page.court_name.setText("上海市徐汇区人民法院")

        elif case_type == "labor":
            self.labor_claim_page.emp_join_date.setText("2023-01-15")
            self.labor_claim_page.job_title.setText("软件工程师")
            self.labor_claim_page.monthly_salary.setText("8000")
            self.labor_claim_page.unpaid_months.setText("2023年12月至2024年2月")
            self.labor_claim_page.emp_term_date.setText("2024-03-20")
            self.labor_claim_page.overtime_hours.setText("40")
            self.labor_claim_page.overtime_pay.setText("3500")
            self.labor_claim_page.no_contract_no.setChecked(True)
            self.labor_claim_page.social_sec_info.setText("未按实际工资基数缴纳")
            self.labor_claim_page.court_name.setText("北京市朝阳区人民法院")

        elif case_type == "divorce":
            self.divorce_claim_page.marriage_date.setText("2018-05-20")
            self.divorce_claim_page.child_name.setText("张三")
            self.divorce_claim_page.child_birthday.setText("2020-01-01")
            self.divorce_claim_page.custody_preference.setText("由原告抚养")
            self.divorce_claim_page.support_monthly.setText("3000")
            self.divorce_claim_page.divorce_reason.setText("感情不和")
            self.divorce_claim_page.asset_description.setText("房产归原告，车辆归被告")
            self.divorce_claim_page.court_name.setText("北京市朝阳区人民法院")

        # Page 3: Evidence
        self.evidence_page.table.setRowCount(0)

        # Show message
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "提示", "测试数据已自动填入！您可以直接点击下一步查看并生成文档。")
