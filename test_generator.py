# File: test_generator.py
# Encoding: UTF-8

from models.case_model import LoanCaseModel
from utils.doc_generator import DocGenerator
import os
import traceback

def run_test():
    try:
        model = LoanCaseModel()

        from models.case_model import PartyInfo
        model.party_manager.add_party(0, PartyInfo("张三（测试）", "示例证件号-原告", "北京市朝阳区示例地址", "示例电话-原告"))
        model.party_manager.add_party(1, PartyInfo("李四（测试）", "示例证件号-被告", "上海市徐汇区示例地址", "示例电话-被告"))

        model.principal_amount = "50000"
        model.interest_rate = "14.6"
        model.interest_start_date = "2023年5月1日"
        model.payment_method = "银行转账"
        model.has_iou = True
        model.collection_process = "多次催要无果"
        model.court_name = "测试人民法院"

        output_path = os.path.join(os.getcwd(), "测试_起诉状.docx")
        print(f"Attempting to generate test document at: {output_path}")

        DocGenerator.generate_loan_lawsuit(model, output_path)
        print("Success! Test document generated.")
    except Exception as e:
        print(f"Error during test generation:\n{traceback.format_exc()}")

if __name__ == "__main__":
    run_test()
