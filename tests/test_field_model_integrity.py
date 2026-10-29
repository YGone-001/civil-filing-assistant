# File: tests/test_field_model_integrity.py
# Purpose: End-to-end field-mapping contract for all five case types (P2-08).
# Encoding: UTF-8
"""Executable proof that registered UI fields reach their model attributes.

Every mapping below is exercised through the real wizard (``prepare_case`` /
``fill_minimal_case``) and the real ``build_case_model`` pipeline, so a future
registration or mapping drift fails here instead of silently losing data.
Classification decisions preserved from earlier phases:
``social_sec_info`` = ADVISORY_ONLY, ``liquidated_damages_formula`` =
LEGACY_COMPATIBILITY, loan repayment history = DEFERRED. All data is fictional.
"""

import pytest

from helpers import (
    CASE_TYPES,
    fill_minimal_case,
    make_wizard,
    prepare_case,
    select_case,
    set_parties,
)
from presenters.model_builder import build_case_model

# (registration key, model attribute) per case category. Fields whose model
# value is derived (contract LPR standard, calculator provenance) are covered
# by the dedicated tests below instead of the value-equality matrix.
FIELD_MODEL_MAP = {
    "loan": [
        ("loan_date", "loan_date"),
        ("loan_reason", "loan_reason"),
        ("principal", "principal_amount"),
        ("rate", "interest_rate"),
        ("start_date", "interest_start_date"),
        ("payment_method", "payment_method"),
        ("demand_date", "demand_date"),
        ("demand_method", "demand_method"),
        ("court_name", "court_name"),
    ],
    "contract": [
        ("c_contract_date", "contract_date"),
        ("c_contract_name", "contract_name"),
        ("c_product_name", "product_name"),
        ("c_total_amount", "total_amount"),
        ("c_delivery_date", "delivery_date"),
        ("c_unpaid_amount", "unpaid_amount"),
        ("c_penalty_amount", "penalty_amount"),
        ("c_overdue_start", "penalty_start_date"),
        ("c_overdue_end", "penalty_cutoff_date"),
        ("c_court_name", "court_name"),
    ],
    "property": [
        ("p_property_addr", "property_addr"),
        ("p_house_area", "house_area"),
        ("p_fee_rate", "fee_rate"),
        ("p_period_start", "period_start"),
        ("p_period_end", "period_end"),
        ("p_late_fee_logic", "late_fee_logic"),
        ("p_demand_record", "demand_record"),
        ("p_total_input", "total_principal"),
        ("p_court_name", "court_name"),
    ],
    "labor": [
        ("l_emp_join_date", "emp_join_date"),
        ("l_job_title", "job_title"),
        ("l_monthly_salary", "monthly_salary"),
        ("l_unpaid_months", "unpaid_months"),
        ("l_emp_term_date", "emp_term_date"),
        ("l_overtime_hours", "overtime_hours"),
        ("l_overtime_pay", "overtime_pay"),
        ("l_social_sec_info", "social_sec_info"),
        ("l_court_name", "court_name"),
    ],
    "divorce": [
        ("d_marriage_date", "marriage_date"),
        ("d_divorce_reason", "divorce_reason"),
        ("d_separation_start_date", "separation_start_date"),
        ("d_child_name", "child_name"),
        ("d_child_birthday", "child_birthday"),
        ("d_custody_preference", "custody_preference"),
        ("d_support_monthly", "support_monthly"),
        ("d_asset_description", "asset_description"),
        ("d_court_name", "court_name"),
    ],
}

ALL_MAPPINGS = [
    (case_type, field, attr)
    for case_type, mappings in FIELD_MODEL_MAP.items()
    for field, attr in mappings
]


@pytest.mark.parametrize("case_type,field,attr", ALL_MAPPINGS)
def test_registered_field_reaches_model_attribute(qapp, case_type, field, attr):
    """Populated input: wizard field value must equal the model attribute."""
    wizard, _ = make_wizard()
    prepare_case(wizard, case_type)
    model = build_case_model(wizard)

    assert getattr(model, attr) == wizard.field(field), (case_type, field, attr)


@pytest.mark.parametrize(
    "case_type,field,attr",
    [
        ("loan", "rate", "interest_rate"),
        ("loan", "start_date", "interest_start_date"),
        ("contract", "c_penalty_amount", "penalty_amount"),
        ("contract", "c_overdue_start", "penalty_start_date"),
        ("contract", "c_overdue_end", "penalty_cutoff_date"),
        ("property", "p_late_fee_logic", "late_fee_logic"),
        ("property", "p_demand_record", "demand_record"),
        ("property", "p_total_input", "total_principal"),
        ("labor", "l_overtime_hours", "overtime_hours"),
        ("labor", "l_overtime_pay", "overtime_pay"),
        ("labor", "l_social_sec_info", "social_sec_info"),
        ("divorce", "d_divorce_reason", "divorce_reason"),
        ("divorce", "d_separation_start_date", "separation_start_date"),
        ("divorce", "d_asset_description", "asset_description"),
    ],
)
def test_empty_optional_fields_map_as_empty_without_fabrication(qapp, case_type, field, attr):
    """Empty optional input maps to an empty model attribute (no invented data).

    ``fill_minimal_case`` deliberately fills the demand pair (loan), the
    delivery date (contract) and the child group (divorce) because their
    conditional validation requires them to appear together; the truly
    optional fields above stay blank.
    """
    wizard, _ = make_wizard()
    fill_minimal_case(wizard, case_type)
    model = build_case_model(wizard)

    assert getattr(model, attr) == "", (case_type, field, attr)


# --- Tri-state confirmation and provenance mappings --------------------------


def test_contract_tri_state_and_provenance_reach_model(qapp):
    from helpers import prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.contract_claim_page
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()

    model = build_case_model(wizard)

    assert model.is_delivered is True
    assert model.is_signed is True
    assert model.penalty_calc_method == "lpr_multiple"
    assert model.penalty_calc_cutoff == "2023-06-30"
    assert model.penalty_calc_standard == "3.45%×4"
    assert model.penalty_cutoff_date == "2023-06-30"


def test_loan_iou_tri_state_reaches_model(qapp):
    from helpers import prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    assert build_case_model(wizard).has_iou is True

    wizard.loan_claim_page.iou_unknown.setChecked(True)
    assert build_case_model(wizard).has_iou is None


def test_labor_no_contract_flag_reaches_model(qapp):
    from helpers import prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    # prepare_case leaves the tri-state on "否"; select "是" explicitly.
    wizard.labor_claim_page.no_contract_yes.setChecked(True)
    assert build_case_model(wizard).is_no_contract is True

    wizard.labor_claim_page.no_contract_no.setChecked(True)
    assert build_case_model(wizard).is_no_contract is False


# --- Preserved classification decisions --------------------------------------


def test_social_sec_info_is_advisory_only_but_never_lost(qapp):
    """ADVISORY_ONLY: collected and stored, deliberately not rendered (review)."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    model = build_case_model(wizard)

    assert model.social_sec_info == "未按实际工资基数缴纳"
    rendered = model.render_facts() + "".join(model.render_claims())
    assert "未按实际工资基数缴纳" not in rendered


def test_legacy_contract_formula_attribute_is_untouched(qapp):
    """LEGACY_COMPATIBILITY: never populated by the builder, never rendered."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    model = build_case_model(wizard)

    assert model.liquidated_damages_formula == ""


def test_loan_repayment_history_remains_unsupported(qapp):
    """DEFERRED: the model carries no repayment-history attributes at all."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    model = build_case_model(wizard)

    assert not any("repay" in attr or "repayment" in attr for attr in vars(model))


def test_evidence_selection_reaches_the_model(qapp):
    from helpers import prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.evidence_page.add_row("补充证据（测试）", "证明目的（测试）", auto_edit=False)
    model = build_case_model(wizard)

    items = [(ev.name, ev.target) for ev in model.evidences]
    assert ("补充证据（测试）", "证明目的（测试）") in items
    assert any("借条" in name for name, _ in items)  # suggested rows included


def test_enterprise_party_fields_reach_the_model(qapp):
    from helpers import prepare_case

    wizard, _ = make_wizard()
    prepare_case(
        wizard,
        "loan",
        plaintiffs=[
            {
                "name": "示例科技（测试）有限公司",
                "is_company": True,
                "credit_code": "91310000MA1FL0TEST",
                "legal_rep": "赵六",
                "address": "地B",
                "phone": "021-00000000",
            }
        ],
    )
    model = build_case_model(wizard)

    plaintiff = model.party_manager.plaintiffs[0]
    assert plaintiff.is_company is True
    assert plaintiff.credit_code == "91310000MA1FL0TEST"
    assert plaintiff.legal_representative == "赵六"


def test_minimal_input_still_builds_every_case_model(qapp):
    """Required-only input builds all five models (required-field contract)."""
    for case_type in CASE_TYPES:
        wizard, _ = make_wizard()
        fill_minimal_case(wizard, case_type)
        model = build_case_model(wizard)
        assert model.case_type_name
        assert model.party_manager.plaintiffs and model.party_manager.defendants
