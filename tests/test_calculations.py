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
    model.child_name = "测试子女"  # a support claim requires an identified child
    model.support_monthly = "3000"
    claims = model.render_claims()
    assert any("抚养费" in c for c in claims)


def test_divorce_support_without_child_makes_no_claim():
    """A support amount without an identified child must not become a claim."""
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    model.support_monthly = "3000"  # no child_name
    claims = model.render_claims()
    assert not any("抚养费" in c for c in claims)
    assert "抚养" not in model.render_facts()


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


# --- Contract view-level penalty calculation (T05: buttons stay auxiliary) ---


def test_contract_view_daily_penalty_computes(qapp):
    from helpers import make_wizard

    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    page.unpaid_amount.setText("10000")
    page.overdue_start.setText("2023-03-01")
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()
    # unpaid × 0.0005 × 7 days = 10000 × 0.0005 × 7 = 35.00
    assert page.penalty_amount.text() == "35.00"


def test_contract_view_lpr_penalty_computes(qapp):
    from helpers import make_wizard

    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    page.unpaid_amount.setText("10000")
    page.lpr_value.setText("3.65")
    page.lpr_multiple.setText("4")
    page.overdue_start.setText("2023-01-01")
    page.overdue_end.setText("2023-01-11")
    page.calc_penalty_by_lpr_multiple()
    # annual = 3.65 × 4 / 100 = 0.146; 10000 × 0.146 × 10 days / 365 = 40.00
    assert page.penalty_amount.text() == "40.00"


# --- Property view-level monthly total (T06: result sits near amount field) ---


def test_property_view_total_computes(qapp):
    from helpers import make_wizard

    wizard, _ = make_wizard()
    page = wizard.property_claim_page
    page.house_area.setText("115.5")
    page.fee_rate.setText("2.8")
    page.period_start.setText("2024-01-01")
    page.period_end.setText("2025-12-31")
    page.update_calc()
    # 115.5 × 2.8 × 24 months = 7761.60
    assert "7761.60" in page.calc_label.text()
    assert "月数=24" in page.calc_label.text()


# --- Generated wording regressions (fictional data) -----------------------


def _divorce(custody, support="3000"):
    model = DivorceCaseModel()
    model.marriage_date = "2018-05-20"
    model.child_name = "测试子女"
    model.custody_preference = custody
    model.support_monthly = support
    return model


@pytest.mark.parametrize("custody", ["由原告抚养", "原告抚养", "由原告直接抚养", "原告"])
def test_divorce_custody_wording_is_not_duplicated(custody):
    model = _divorce(custody)
    text = "\n".join(model.render_claims()) + model.render_facts()
    assert "抚养抚养" not in text
    assert "判令婚生子女测试子女由原告抚养；" in model.render_claims()
    assert any(c.startswith("判令被告按月支付抚养费人民币3000元") for c in model.render_claims())


def test_divorce_defendant_custody_never_claims_support_from_defendant():
    model = _divorce("由被告抚养")
    claims = model.render_claims()
    facts = model.render_facts()
    assert not any("被告按月支付" in c for c in claims)
    assert "判令婚生子女测试子女由被告抚养，原告按月支付抚养费人民币3000元，至子女年满18周岁止；" in claims
    assert "被告应按月支付" not in facts
    assert "原告愿按月支付抚养费3000元。" in facts


def test_divorce_reason_is_stated_without_tautology():
    model = _divorce("由原告抚养")
    model.divorce_reason = "感情不和"
    facts = model.render_facts()
    assert "原告主张的离婚原因：感情不和。" in facts
    assert "日益淡漠" not in facts


@pytest.mark.parametrize("record, expected", [
    ("2025年6月多次张贴催缴通知并发送短信。", "催缴情况如下：2025年6月多次张贴催缴通知并发送短信。但被告至今未缴纳。"),
    ("发送短信", "催缴情况如下：发送短信。但被告至今未缴纳。"),
])
def test_property_demand_record_reads_as_a_sentence(record, expected):
    model = PropertyCaseModel()
    model.demand_record = record
    facts = model.render_facts()
    assert expected in facts
    assert "曾通过" not in facts


def _labor():
    model = LaborCaseModel()
    model.emp_join_date = "2023-01-15"
    model.job_title = "测试岗位"
    model.monthly_salary = "8000"
    model.unpaid_months = "2023年12月至2024年2月"
    return model


def test_labor_facts_use_neutral_party_wording():
    model = _labor()
    model.is_no_contract = True
    facts = model.render_facts()
    for phrase in ("另查", "被告单位", "严重侵害"):
        assert phrase not in facts
    assert "入职被告处" in facts
    assert "第八十二条" in facts


def test_labor_unconfirmed_contract_status_asserts_nothing():
    model = _labor()
    assert model.is_no_contract is None
    text = "\n".join(model.render_claims()) + model.render_facts()
    assert "二倍工资" not in text
    assert "书面劳动合同" not in text


def test_labor_without_end_date_still_reads_cleanly():
    facts = _labor().render_facts()
    assert "截至" not in facts and "截止" not in facts
    assert "被告共计欠付原告工资24000.00元。" in facts


def test_labor_arbitration_is_stated_from_supplied_details_only():
    model = _labor()
    model.labor_procedure = "non_final_award"
    model.labor_role = "employee"
    model.arb_commission = "示例劳动人事争议仲裁委员会"
    model.arb_receipt_date = "2024-06-01"
    facts = model.render_facts()
    assert "向示例劳动人事争议仲裁委员会申请劳动仲裁，并于2024-06-01收到该委员会作出的非终局仲裁裁决书" in facts
    assert "案号" not in facts

    model.arb_case_no = "示例仲裁案号-001"
    assert "（案号：示例仲裁案号-001）" in model.render_facts()

    # Unconfirmed role/classification and blocked states must not produce a
    # sentence: eligibility, plaintiff identity and wording stay consistent.
    model.labor_role = None
    assert "仲裁" not in model.render_facts()

    model.labor_role = "employee"
    model.labor_procedure = None
    assert "仲裁" not in model.render_facts()

    model.labor_procedure = "mediation_effective"
    model.arb_case_no = ""
    assert "仲裁" not in model.render_facts()
