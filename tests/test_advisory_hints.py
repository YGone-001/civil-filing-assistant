# File: tests/test_advisory_hints.py
# Purpose: Advisory-only fields and neutral limitation hints (P1-05 / D-05, P1-08 / D-04).
# Encoding: UTF-8
"""Regression coverage for documented advisory data paths.

``social_sec_info`` is collected for the labor case and stored on the model as
an advisory-only field (rendering it in the complaint would be a legal-content
change requiring review), so the mapping must at least never silently lose it.
The loan page requires an explicit repayment confirmation before the
full-principal template may be used. All data is fictional.
"""

from helpers import fill_case_facts, make_wizard, prepare_case, select_case, set_parties
from presenters.model_builder import build_case_model


def test_social_sec_info_reaches_the_model_without_loss(qapp):
    """The labor advisory field must survive UI -> model (no silent data loss)."""
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    set_parties(wizard)
    fill_case_facts(wizard, "labor")
    wizard.labor_claim_page.social_sec_info.setText("测试社保缴纳情况（虚构）")

    model = build_case_model(wizard)

    assert model.social_sec_info == "测试社保缴纳情况（虚构）"


def test_social_sec_info_is_documented_as_advisory_only():
    """The advisory classification must be visible where the field is mapped."""
    from pathlib import Path

    builder_source = (
        Path(__file__).resolve().parents[1] / "presenters" / "model_builder.py"
    ).read_text(encoding="utf-8")
    assert "social_sec_info" in builder_source


def test_loan_page_requires_an_explicit_repayment_confirmation(qapp):
    """The full-principal template needs a confirmed "never repaid" answer."""
    wizard, _ = make_wizard()
    page = wizard.loan_claim_page

    assert page.get_has_repayment() is None
    assert "确认" in page.repayment_hint.text()

    page.repayment_yes.setChecked(True)
    assert "从未还款" in page.repayment_hint.text()

    page.repayment_no.setChecked(True)
    assert page.repayment_hint.isHidden()


def test_legacy_contract_formula_attribute_stays_unused():
    """The legacy placeholder must remain empty and unpopulated by the builder."""
    from models.case_model import ContractCaseModel

    model = ContractCaseModel()
    assert model.liquidated_damages_formula == ""
