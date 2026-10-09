# File: test_generator.py
# Purpose: Document-generation smoke test (exits nonzero on failure)
# Encoding: UTF-8
"""Smoke test: generate one complaint from a fictional loan model.

This is intentionally a small smoke test, not a full test suite. It exits with
a nonzero status when generation fails so that CI and callers can detect the
failure; it never reports success after catching an exception. All data here is
clearly fictional, and the output is written to a temporary directory so no
generated document lands in a tracked repository path.
"""

import os
import sys
import tempfile
import zipfile

from models.case_model import LoanCaseModel
from models.case_model import PartyInfo
from utils.doc_generator import DocGenerator


def run_test():
    """Return ``True`` on success, ``False`` on any failure."""
    tmp_dir = tempfile.mkdtemp(prefix="cfa_smoke_")
    output_path = os.path.join(tmp_dir, "fictional_test_complaint.docx")

    try:
        model = LoanCaseModel()

        # Clearly fictional placeholders; not valid real identifiers.
        model.party_manager.add_party(
            0,
            PartyInfo("张三（测试）", "示例证件号-原告", "北京市朝阳区示例地址", "示例电话-原告"),
        )
        model.party_manager.add_party(
            1,
            PartyInfo("李四（测试）", "示例证件号-被告", "上海市徐汇区示例地址", "示例电话-被告"),
        )

        model.loan_date = "2023年1月1日"
        model.loan_reason = "资金周转"
        model.principal_amount = "50000"
        model.interest_rate = "14.6"
        model.interest_start_date = "2023年5月1日"
        model.payment_method = "银行转账"
        model.has_iou = True
        model.demand_date = "2023年10月"
        model.demand_method = "微信及电话"
        model.court_name = "测试人民法院"

        print(f"Attempting to generate smoke-test document at: {output_path}")
        DocGenerator.generate_loan_lawsuit(model, output_path)

        if not os.path.exists(output_path):
            print("FAIL: output file was not created.")
            return False
        if not zipfile.is_zipfile(output_path):
            print("FAIL: output file is not a valid docx package.")
            return False
        with zipfile.ZipFile(output_path) as archive:
            if "word/document.xml" not in archive.namelist():
                print("FAIL: docx package is missing word/document.xml.")
                return False

        print("Success! Smoke-test document generated and verified.")
        return True
    except Exception:
        import traceback

        print(f"Error during smoke-test generation:\n{traceback.format_exc()}")
        return False
    finally:
        # Clean up the temporary artifact regardless of outcome.
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(0 if run_test() else 1)
