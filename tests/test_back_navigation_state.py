# File: tests/test_back_navigation_state.py
# Purpose: Back/Next navigation must preserve entered case facts (P1-01 / D-09).
# Encoding: UTF-8
"""Regression coverage for wizard input preservation across Back navigation.

Qt's default ``QWizardPage.cleanupPage()`` used to reset every registered
field when the user pressed 上一步, silently erasing entered case facts. The
application now overrides it, and these tests use the *real* wizard buttons
for the key scenarios so a future restoration of the destructive cleanup
behavior fails loudly. All data is fictional.
"""

import pytest
from PySide6.QtWidgets import QWizard

from helpers import (
    CASE_TYPES,
    fill_case_facts,
    fill_minimal_case,
    make_wizard,
    select_case,
    set_parties,
)
from presenters.model_builder import build_case_model

CLAIM_PAGE_ATTR = {
    "loan": "loan_claim_page",
    "contract": "contract_claim_page",
    "property": "property_claim_page",
    "labor": "labor_claim_page",
    "divorce": "divorce_claim_page",
}

CLAIM_PAGE_ID = {
    "loan": "PAGE_LOAN_CLAIM",
    "contract": "PAGE_CONTRACT_CLAIM",
    "property": "PAGE_PROPERTY_CLAIM",
    "labor": "PAGE_LABOR_CLAIM",
    "divorce": "PAGE_DIVORCE_CLAIM",
}


def _read(widget):
    """Read a QLineEdit/QTextEdit value uniformly."""
    return widget.toPlainText() if hasattr(widget, "toPlainText") else widget.text()


def _page_values(page, names):
    return {name: _read(getattr(page, name)) for name in names}


def _navigate_to_claim(wizard, qapp, case_type):
    """Drive a fresh wizard to the case claim page with real button clicks."""
    wizard.show()
    qapp.processEvents()
    wizard.button(QWizard.NextButton).click()  # welcome -> case selection
    select_case(wizard, case_type)
    wizard.button(QWizard.NextButton).click()  # -> party
    set_parties(wizard)
    wizard.button(QWizard.NextButton).click()  # -> claim page
    assert wizard.currentId() == getattr(wizard, CLAIM_PAGE_ID[case_type])
    page = getattr(wizard, CLAIM_PAGE_ATTR[case_type])
    fill_case_facts(wizard, case_type)
    qapp.processEvents()
    return page


ALL_FIELD_NAMES = {
    "loan": ("loan_date", "loan_reason", "principal", "payment_method", "rate",
             "start_date", "demand_date", "demand_method", "court_name"),
    "contract": ("contract_date", "contract_name", "product_name", "total_amount",
                 "delivery_date", "unpaid_amount", "penalty_amount", "overdue_start",
                 "overdue_end", "lpr_value", "lpr_multiple", "court_name"),
    "property": ("property_addr", "house_area", "fee_rate", "period_start",
                 "period_end", "late_fee_logic", "court_name"),
    "labor": ("emp_join_date", "job_title", "monthly_salary", "unpaid_months",
              "emp_term_date", "overtime_hours", "overtime_pay", "social_sec_info",
              "court_name"),
    "divorce": ("marriage_date", "divorce_reason", "separation_start_date",
                "child_name", "child_birthday", "custody_preference",
                "support_monthly", "asset_description", "court_name"),
}


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_back_next_preserves_all_case_facts(qapp, case_type):
    """Loan page -> Back -> Next (and likewise for the other four) keeps values."""
    wizard, _ = make_wizard()
    page = _navigate_to_claim(wizard, qapp, case_type)
    expected = _page_values(page, ALL_FIELD_NAMES[case_type])
    assert any(value.strip() for value in expected.values()), "fixture must fill values"

    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    back.click()
    qapp.processEvents()
    assert wizard.currentId() == wizard.PAGE_PARTY
    next_btn.click()
    qapp.processEvents()
    assert wizard.currentId() == getattr(wizard, CLAIM_PAGE_ID[case_type])

    assert _page_values(page, ALL_FIELD_NAMES[case_type]) == expected


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_repeated_back_next_cycles_preserve_values(qapp, case_type):
    """Three consecutive Back/Next cycles must not degrade any field."""
    wizard, _ = make_wizard()
    page = _navigate_to_claim(wizard, qapp, case_type)
    expected = _page_values(page, ALL_FIELD_NAMES[case_type])

    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    for _ in range(3):
        back.click()
        qapp.processEvents()
        next_btn.click()
        qapp.processEvents()
        assert wizard.currentId() == getattr(wizard, CLAIM_PAGE_ID[case_type])

    assert _page_values(page, ALL_FIELD_NAMES[case_type]) == expected


def test_tri_state_selections_survive_back_next(qapp):
    """Confirmed tri-state facts (IOU, delivery, receipt) must not be reset."""
    wizard, _ = make_wizard()
    loan_page = _navigate_to_claim(wizard, qapp, "loan")
    contract_page = getattr(wizard, "contract_claim_page")
    fill_case_facts(wizard, "contract")
    qapp.processEvents()

    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    for _ in range(2):
        back.click()
        qapp.processEvents()
        next_btn.click()
        qapp.processEvents()

    assert loan_page.get_has_iou() is True
    flags = contract_page.get_flags()
    assert flags["is_delivered"] is True
    assert flags["is_signed"] is True


def test_optional_blank_fields_stay_blank_across_back_next(qapp):
    """Blank optional fields must not be silently repopulated by navigation."""
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()
    fill_minimal_case(wizard, "loan")
    wizard.button(QWizard.NextButton).click()  # welcome -> case selection
    wizard.button(QWizard.NextButton).click()  # -> party
    wizard.button(QWizard.NextButton).click()  # -> loan claim
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM

    page = wizard.loan_claim_page
    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    back.click()
    qapp.processEvents()
    next_btn.click()
    qapp.processEvents()

    # rate/start_date are the optional-blank pair in this fixture; the demand
    # pair is filled by fill_minimal_case and must merely be preserved.
    for optional in ("rate", "start_date"):
        assert _read(getattr(page, optional)) == "", optional
    assert _read(page.demand_date) == "2023年10月"
    assert _read(page.demand_method) == "微信"


def test_mandatory_validation_still_blocks_after_fix(qapp):
    """Empty mandatory fields must still disable Next; a click must be a no-op."""
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()
    wizard.button(QWizard.NextButton).click()  # welcome -> case selection
    select_case(wizard, "loan")
    wizard.button(QWizard.NextButton).click()  # -> party
    set_parties(wizard)
    wizard.button(QWizard.NextButton).click()  # -> loan claim

    next_btn = wizard.button(QWizard.NextButton)
    assert not next_btn.isEnabled()
    next_btn.click()
    qapp.processEvents()
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM


def test_edited_preserved_value_updates_model(qapp):
    """A value kept across Back/Next must flow into the freshly built model."""
    wizard, _ = make_wizard()
    _navigate_to_claim(wizard, qapp, "loan")

    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    back.click()
    qapp.processEvents()
    next_btn.click()
    qapp.processEvents()

    wizard.loan_claim_page.principal.setText("777")
    qapp.processEvents()
    model = build_case_model(wizard)
    assert model.principal_amount == "777"


def test_fresh_wizard_instance_starts_empty(qapp):
    """An explicit new case (new process/wizard) must not reuse stale input."""
    wizard, _ = make_wizard()
    _navigate_to_claim(wizard, qapp, "loan")

    fresh, _ = make_wizard()
    assert fresh.loan_claim_page.loan_date.text() == ""
    assert fresh.loan_claim_page.principal.text() == ""


def test_case_switch_does_not_cross_contaminate_claim_pages(qapp):
    """Switching loan -> contract must show empty contract fields, not loan data."""
    wizard, _ = make_wizard()
    _navigate_to_claim(wizard, qapp, "loan")
    loan_values = _page_values(wizard.loan_claim_page, ALL_FIELD_NAMES["loan"])

    back = wizard.button(QWizard.BackButton)
    back.click()  # loan claim -> party
    qapp.processEvents()
    back.click()  # party -> case selection
    qapp.processEvents()
    select_case(wizard, "contract")
    wizard.button(QWizard.NextButton).click()  # -> party
    set_parties(wizard)
    wizard.button(QWizard.NextButton).click()  # -> contract claim (first entry)
    assert wizard.currentId() == wizard.PAGE_CONTRACT_CLAIM

    contract_values = _page_values(wizard.contract_claim_page, ALL_FIELD_NAMES["contract"])
    # The LPR fields carry documented example defaults (P1-07); every other
    # contract field must be blank on first entry — no loan data may leak in.
    checked = {k: v for k, v in contract_values.items() if k not in ("lpr_value", "lpr_multiple")}
    assert not any(value.strip() for value in checked.values())

    # The loan page keeps its own (same-category) data for this session.
    assert _page_values(wizard.loan_claim_page, ALL_FIELD_NAMES["loan"]) == loan_values
