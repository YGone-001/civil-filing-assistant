# File: presenters/main_presenter.py
# Purpose: Bridge between View (QWizard) and Model/Utils
# Encoding: UTF-8

import os
from PySide6.QtWidgets import QMessageBox
from models.case_model import LoanCaseModel
from utils.doc_generator import DocGenerator, DocumentGenerator
from utils.security_check import SecurityGuard
from utils.batch_manager import BatchExportManager

class MainPresenter:
    def __init__(self, view):
        self.view = view
        self.view.accepted.connect(self.on_wizard_accepted)

    def on_wizard_accepted(self):
        """
        Triggered when the user clicks 'Finish' on the last page.
        Gathers data, builds the model, and generates the docx file.
        """
        print("DEBUG: MainPresenter on_wizard_accepted triggered.")

        # Decide which model to instantiate based on step 0
        case_type = self.view.field("case_type")
        if case_type == "contract":
            from models.case_model import ContractCaseModel
            model = ContractCaseModel()
        elif case_type == "property":
            from models.case_model import PropertyCaseModel
            model = PropertyCaseModel()
        elif case_type == "labor":
            from models.case_model import LaborCaseModel
            model = LaborCaseModel()
        elif case_type == "divorce":
            from models.case_model import DivorceCaseModel
            model = DivorceCaseModel()
        else:
            model = LoanCaseModel()

        # Populate Parties
        party_data = self.view.party_page.get_party_data()

        from models.case_model import PartyInfo
        for p_data in party_data["plaintiffs"]:
            # Only add if name is not empty
            if p_data["name"].strip():
                pi = PartyInfo(
                    p_data["name"],
                    p_data["id_number"],
                    p_data["address"],
                    p_data["phone"],
                    p_data["is_company"],
                    p_data["legal_representative"],
                    p_data["credit_code"]
                )
                model.party_manager.add_party(0, pi)

        for d_data in party_data["defendants"]:
            if d_data["name"].strip():
                pi = PartyInfo(
                    d_data["name"],
                    d_data["id_number"],
                    d_data["address"],
                    d_data["phone"],
                    d_data["is_company"],
                    d_data["legal_representative"],
                    d_data["credit_code"]
                )
                model.party_manager.add_party(1, pi)

        # Populate Claims based on case type
        if case_type == "contract":
            model.contract_date = self.view.field("c_contract_date")
            model.contract_name = self.view.field("c_contract_name")
            model.product_name = self.view.field("c_product_name")
            model.total_amount = self.view.field("c_total_amount")
            model.delivery_date = self.view.field("c_delivery_date")
            model.unpaid_amount = self.view.field("c_unpaid_amount")
            model.penalty_amount = self.view.field("c_penalty_amount")
            model.penalty_start_date = self.view.field("c_overdue_start")
            model.penalty_calc_standard = self.view.field("c_lpr_value") + "%×" + self.view.field("c_lpr_multiple")
            model.court_name = self.view.field("c_court_name")

            flags = self.view.contract_claim_page.get_flags()
            model.is_delivered = flags["is_delivered"]
            model.is_signed = flags["is_signed"]
        elif case_type == "property":
            model.property_addr = self.view.field("p_property_addr")
            model.house_area = self.view.field("p_house_area")
            model.fee_rate = self.view.field("p_fee_rate")
            model.period_start = self.view.field("p_period_start")
            model.period_end = self.view.field("p_period_end")
            model.late_fee_logic = self.view.field("p_late_fee_logic")
            model.demand_record = self.view.field("p_demand_record")
            model.total_principal = self.view.field("p_total_input")
            model.court_name = self.view.field("p_court_name")

            try:
                from decimal import Decimal
                user_total_text = (model.total_principal or "").strip()
                if user_total_text:
                    model.months = model._calc_months()
                    total = model._calc_total()
                    if total is not None:
                        user_total = Decimal(user_total_text)
                        if user_total != 0:
                            diff = abs(user_total - total) / user_total
                            if diff > Decimal("0.01"):
                                QMessageBox.warning(self.view, "提示", "物业费总金额与系统计算误差超过 1%，建议核对（仍将继续生成文书）。")
            except Exception:
                pass
        elif case_type == "labor":
            model.emp_join_date = self.view.field("l_emp_join_date")
            model.job_title = self.view.field("l_job_title")
            model.monthly_salary = self.view.field("l_monthly_salary")
            model.unpaid_months = self.view.field("l_unpaid_months")
            model.emp_term_date = self.view.field("l_emp_term_date")
            model.overtime_hours = self.view.field("l_overtime_hours")
            model.overtime_pay = self.view.field("l_overtime_pay")
            model.is_no_contract = self.view.labor_claim_page.get_has_no_contract()
            model.social_sec_info = self.view.field("l_social_sec_info")
            model.court_name = self.view.field("l_court_name")
        elif case_type == "divorce":
            model.marriage_date = self.view.field("d_marriage_date")
            model.child_name = self.view.field("d_child_name")
            model.child_birthday = self.view.field("d_child_birthday")
            model.custody_preference = self.view.field("d_custody_preference")
            model.support_monthly = self.view.field("d_support_monthly")
            model.divorce_reason = self.view.field("d_divorce_reason")
            model.asset_description = self.view.field("d_asset_description")
            model.court_name = self.view.field("d_court_name")
        else:
            model.loan_date = self.view.field("loan_date")
            model.loan_reason = self.view.field("loan_reason")
            model.principal_amount = self.view.field("principal")
            model.interest_rate = self.view.field("rate")
            model.interest_start_date = self.view.field("start_date")
            model.payment_method = self.view.field("payment_method")

            model.has_iou = self.view.loan_claim_page.get_has_iou()

            model.demand_date = self.view.field("demand_date")
            model.demand_method = self.view.field("demand_method")
            model.court_name = self.view.field("court_name")

        from models.case_model import EvidenceItem
        for name, target in self.view.evidence_page.get_evidence_items():
            model.evidences.append(EvidenceItem(name, target))

        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            manager = BatchExportManager(DocumentGenerator())
            target_dir = manager.run_batch_export(model, desktop_path)
            print(f"DEBUG: Batch export completed at {target_dir}")

            # Securely wipe data from RAM before showing the success message
            SecurityGuard.wipe_memory(model)

            QMessageBox.information(self.view, "生成成功", f"立案材料已生成完成（起诉状 / 证据清单 / 送达地址确认书）。\n\n文件夹位置：\n{target_dir}\n\n所有内存数据已被彻底销毁，请放心使用。")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"DEBUG: Error occurred: {error_trace}")
            QMessageBox.critical(self.view, "生成失败", f"生成文档时发生错误:\n{str(e)}\n\n详情已打印到控制台。")
        finally:
            # Ensure model is wiped even if error occurs
            SecurityGuard.wipe_memory(model)
            import sys
            sys.exit(0)
