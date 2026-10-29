# File: tests/test_sensitive_cleanup.py
# Purpose: Best-effort sensitive-field cleanup coverage (P1-06 / D-06).
# Encoding: UTF-8
"""Regression coverage for SecurityGuard.wipe_memory.

The cleanup list used to omit ``separation_start_date`` and
``total_unpaid_amount`` (both survived a wipe). These tests pin the full
coverage contract: every string attribute of every case model except the
non-sensitive ``case_type_name`` label must be cleared. The cleanup stays
best-effort — it never claims secure erasure and never touches files.
"""

import pytest

from models.case_model import (
    ContractCaseModel,
    DivorceCaseModel,
    LaborCaseModel,
    LoanCaseModel,
    PropertyCaseModel,
)
from utils.security_check import SecurityGuard

# The only model attribute allowed to survive a wipe: a fixed, non-sensitive
# category label shared by every model class.
NON_SENSITIVE_ATTRS = {"case_type_name"}

FICTIONAL_VALUES = {
    "loan": {
        "loan_date": "2023-01-01", "loan_reason": "测试事由", "principal_amount": "50000",
        "payment_method": "测试转账", "interest_rate": "14.6", "interest_start_date": "2023-05-01",
        "demand_date": "2023年10月", "demand_method": "测试催告", "court_name": "测试人民法院",
    },
    "contract": {
        "contract_date": "2023-01-01", "contract_name": "测试合同", "product_name": "测试货物",
        "total_amount": "50000", "delivery_date": "2023-02-01", "unpaid_amount": "30000",
        "penalty_amount": "5000", "penalty_start_date": "2023-03-01",
        "penalty_cutoff_date": "2023-06-30", "penalty_calc_method": "lpr_multiple",
        "penalty_calc_cutoff": "2023-06-30", "penalty_calc_standard": "3.45%×4",
        "liquidated_damages_formula": "测试公式", "court_name": "测试人民法院",
    },
    "property": {
        "property_addr": "测试小区1栋101室", "house_area": "100", "fee_rate": "2.8",
        "period_start": "2024-01-01", "period_end": "2024-12-31",
        "late_fee_logic": "按约定", "demand_record": "测试催缴记录",
        "total_principal": "3360.00", "court_name": "测试人民法院",
    },
    "labor": {
        "emp_join_date": "2023-01-15", "job_title": "测试岗位", "monthly_salary": "8000",
        "unpaid_months": "2024年1月至2024年3月", "emp_term_date": "2024-03-20",
        "overtime_hours": "40", "overtime_pay": "3500", "social_sec_info": "测试社保信息",
        "total_unpaid_amount": "24000.00", "court_name": "测试人民法院",
    },
    "divorce": {
        "marriage_date": "2018-05-20", "child_name": "测试子女", "child_birthday": "2020-01-01",
        "custody_preference": "由原告抚养", "support_monthly": "3000",
        "divorce_reason": "测试原因", "separation_start_date": "2022-01-01",
        "asset_description": "测试房产归原告", "court_name": "测试人民法院",
    },
}

MODEL_CLASSES = {
    "loan": LoanCaseModel,
    "contract": ContractCaseModel,
    "property": PropertyCaseModel,
    "labor": LaborCaseModel,
    "divorce": DivorceCaseModel,
}


def _filled_model(case_type):
    model = MODEL_CLASSES[case_type]()
    for attr, value in FICTIONAL_VALUES[case_type].items():
        setattr(model, attr, value)
    return model


def _string_attrs(model):
    return sorted(
        name for name in vars(model)
        if isinstance(getattr(model, name), str) and name not in NON_SENSITIVE_ATTRS
    )


def _cleared(value):
    """The existing cleanup contract: strings become "X"*len; amounts may
    become "0"; empty strings stay empty."""
    return value == "" or value == "0" or set(value) == {"X"}


@pytest.mark.parametrize("case_type", sorted(MODEL_CLASSES))
def test_wipe_clears_every_string_case_field(case_type):
    model = _filled_model(case_type)
    attrs = _string_attrs(model)
    assert attrs, "fixture must expose string fields"

    SecurityGuard.wipe_memory(model)

    for attr in attrs:
        assert _cleared(getattr(model, attr)), f"{case_type}.{attr} survived: {getattr(model, attr)!r}"


def test_confirmed_phase0_omissions_are_now_covered():
    divorce = _filled_model("divorce")
    labor = _filled_model("labor")

    SecurityGuard.wipe_memory(divorce)
    SecurityGuard.wipe_memory(labor)

    assert _cleared(divorce.separation_start_date)
    assert _cleared(labor.total_unpaid_amount)


def test_wipe_covers_parties_and_evidence():
    from models.case_model import EvidenceItem, PartyInfo

    model = _filled_model("loan")
    model.party_manager.add_party(0, PartyInfo("原告甲（测试）", "示例证件", "测试地址", "13800000000"))
    model.party_manager.add_party(1, PartyInfo("被告乙（测试）", "示例证件", "测试地址", "13900000000"))
    model.evidences.append(EvidenceItem("测试证据", "测试证明目的"))

    SecurityGuard.wipe_memory(model)

    for party in model.party_manager.plaintiffs + model.party_manager.defendants:
        assert party.name == "X" * len("原告甲（测试）") or party.name == ""
    assert model.evidences == []


def test_repeated_wipe_is_safe():
    model = _filled_model("divorce")
    SecurityGuard.wipe_memory(model)
    first = model.separation_start_date
    SecurityGuard.wipe_memory(model)  # must not raise and must stay cleared
    assert model.separation_start_date == first or model.separation_start_date == ""


def test_successful_export_cleanup_keeps_generated_documents_valid(
    qapp, monkeypatch, tmp_path, dialog_recorder
):
    """The post-export wipe must not corrupt the files already written."""
    import os

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    from helpers import make_wizard, prepare_case, verify_docx_package
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")

    result = presenter.attempt_finish()
    assert result == "SUCCESS"

    docs = sorted((home / "Desktop").rglob("*.docx"))
    assert len(docs) == 3
    for doc in docs:  # wipe already ran; the published files must still be valid
        verify_docx_package(doc)
