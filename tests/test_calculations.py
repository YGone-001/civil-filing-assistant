# File: tests/test_calculations.py
# Purpose: Regression tests for monetary and case-model calculations.
# Encoding: UTF-8

import datetime

import pytest

from models.case_model import (
    CalculationError,
    ContractCaseModel,
    DivorceCaseModel,
    LaborCaseModel,
    LoanCaseModel,
    PropertyCaseModel,
    parse_month_range,
)


# --- parse_month_range (labor unpaid-period parsing) ----------------------


def test_range_normal_months():
    assert parse_month_range("2023年12月至2024年2月") == (3, False)


def test_range_year_boundary():
    assert parse_month_range("2023-11 至 2024-02") == (4, False)


def test_range_single_month():
    assert parse_month_range("2023年12月") == (1, False)


def test_range_end_year_inferred_is_partial():
    months, partial = parse_month_range("2023年12月至2月")
    assert months == 3
    assert partial is True


def test_range_with_day_component_is_partial():
    months, partial = parse_month_range("2023-12-15 至 2024-01-15")
    assert months == 2
    assert partial is True


def test_range_reversed_raises():
    with pytest.raises(CalculationError):
        parse_month_range("2024年2月至2023年12月")


@pytest.mark.parametrize("bad", ["", "   ", "abc", "无月份", "至到"])
def test_range_malformed_raises(bad):
    with pytest.raises(CalculationError):
        parse_month_range(bad)


# --- LaborCaseModel --------------------------------------------------------


def test_labor_simple_full_month_total():
    model = LaborCaseModel()
    model.monthly_salary = "8000"
    model.unpaid_months = "2023年12月至2024年2月"
    months, partial = model.resolve_unpaid_month_count()
    assert (months, partial) == (3, False)
    total, months, partial = model._calc_unpaid_amount()
    assert str(total) == "24000.00"
    assert total == 24000


def test_labor_claim_uses_computed_total():
    model = LaborCaseModel()
    model.monthly_salary = "8000"
    model.unpaid_months = "2023年12月至2024年2月"
    claims = model.render_claims()
    assert any("24000.00" in c for c in claims), claims


def test_labor_unparseable_period_keeps_editable_placeholder():
    model = LaborCaseModel()
    model.monthly_salary = "8000"
    model.unpaid_months = "不清楚"
    claims = model.render_claims()
    # No fabricated amount; an explicit placeholder is used instead.
    assert any("人工确认" in c for c in claims), claims
    assert not any("8000" in c for c in claims)


def test_labor_negative_salary_does_not_invent_amount():
    model = LaborCaseModel()
    model.monthly_salary = "-5000"
    model.unpaid_months = "2024年1月"
    claims = model.render_claims()
    assert any("人工确认" in c for c in claims), claims


# --- LoanCaseModel ---------------------------------------------------------


def test_loan_principal_claim_and_interest():
    model = LoanCaseModel()
    model.principal_amount = "50000"
    model.interest_rate = "14.6"
    model.interest_start_date = "2023-05-01"
    claims = model.render_claims()
    assert any("50000" in c for c in claims)
    assert any("利息" in c for c in claims)


def test_loan_no_interest_when_fields_missing():
    model = LoanCaseModel()
    model.principal_amount = "50000"
    claims = model.render_claims()
    assert not any("利息" in c for c in claims)


def test_loan_no_hardcoded_rate_ceiling():
    model = LoanCaseModel()
    model.principal_amount = "50000"
    model.interest_rate = "36"
    model.interest_start_date = "2023-05-01"
    claims = model.render_claims()
    joined = "\n".join(claims)
    assert "13.8" not in joined
    assert "LPR" not in joined


def test_loan_negative_principal_uses_neutral_claim():
    model = LoanCaseModel()
    model.principal_amount = "-100"
    model.interest_rate = "10"
    model.interest_start_date = "2023-05-01"
    claims = model.render_claims()
    # Only the principal claim plus a neutral interest statement, no bogus figure.
    assert any("以实际清偿日结算为准" in c for c in claims), claims


# --- PropertyCaseModel -----------------------------------------------------


def test_property_whole_month_total():
    model = PropertyCaseModel()
    model.house_area = "115.5"
    model.fee_rate = "2.8"
    model.period_start = "2024-01-01"
    model.period_end = "2025-12-31"
    assert model._calc_months() == 24
    assert model._resolved_principal() == "7761.60"


def test_property_user_total_never_overwritten():
    model = PropertyCaseModel()
    model.house_area = "115.5"
    model.fee_rate = "2.8"
    model.period_start = "2024-01-01"
    model.period_end = "2025-12-31"
    model.total_principal = "9999"
    assert model._resolved_principal() == "9999"


def test_property_partial_billing_flagged():
    model = PropertyCaseModel()
    model.house_area = "100"
    model.fee_rate = "2"
    model.period_start = "2024-01-15"
    model.period_end = "2024-03-20"
    model._resolved_principal()
    assert model.is_partial_billing is True
    assert "估算" in model.render_facts()


def test_property_reversed_period_zero_months():
    model = PropertyCaseModel()
    model.house_area = "100"
    model.fee_rate = "2"
    model.period_start = "2024-12-01"
    model.period_end = "2024-01-01"
    assert model._calc_months() == 0


# --- ContractCaseModel -----------------------------------------------------


def test_contract_claim_matches_input():
    model = ContractCaseModel()
    model.unpaid_amount = "30000"
    model.penalty_amount = "5000"
    model.penalty_start_date = "2023-03-01"
    model.penalty_calc_standard = "3.45%×4"
    claims = model.render_claims()
    assert any("30000" in c for c in claims)
    assert any("5000" in c for c in claims)


def test_contract_plain_penalty_without_standard():
    model = ContractCaseModel()
    model.unpaid_amount = "30000"
    model.penalty_amount = "5000"
    claims = model.render_claims()
    assert any("违约金" in c and "5000" in c for c in claims)


# --- DivorceCaseModel ------------------------------------------------------


def test_divorce_core_claim_present():
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    claims = model.render_claims()
    assert claims[0] == "判令原告与被告离婚；"


def test_divorce_without_children_has_no_custody_or_support():
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    claims = model.render_claims()
    joined = "\n".join(claims)
    assert "抚养" not in joined
    assert "抚养费" not in joined


def test_divorce_support_makes_support_claim():
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    model.support_monthly = "3000"
    claims = model.render_claims()
    assert any("抚养费" in c for c in claims)


def test_divorce_property_facts_depend_on_asset_not_support():
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    model.support_monthly = "3000"  # support only, no property
    facts = model.render_facts()
    assert "共同财产" not in facts

    model.asset_description = "房产归原告"
    facts = model.render_facts()
    assert "共同财产" in facts


def test_divorce_no_invented_child_facts_when_none():
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    facts = model.render_facts()
    assert "子女" not in facts
