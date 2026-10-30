# File: tests/test_page_modularization_contract.py
# Purpose: Modularization contract: facade identity, page IDs, lifecycle and
#          single-implementation guarantees (P3A-03 ~ P3A-10).
# Encoding: UTF-8
"""Behavioral contract tests for the extracted page package.

The compatibility facade must resolve to the *same class objects* as the new
owner modules, page registration/routing/lifecycle must be unchanged, and no
duplicate page or helper implementations may exist. Real wizard behavior is
exercised through the actual QWizard buttons.
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QWizard

import views.pages.base as pages_base
import views.pages.common as pages_common
import views.wizard_pages as facade
from helpers import CASE_TYPES, fill_case_facts, make_wizard, select_case, set_parties

PAGE_OWNERS = {
    "WelcomePage": "views.pages.welcome",
    "CaseSelectionPage": "views.pages.case_selection",
    "PartyPage": "views.pages.party",
    "LoanClaimPage": "views.pages.loan",
    "ContractClaimPage": "views.pages.contract",
    "PropertyClaimPage": "views.pages.property",
    "LaborClaimPage": "views.pages.labor",
    "DivorceClaimPage": "views.pages.divorce",
    "EvidencePage": "views.pages.evidence",
    "ExportPage": "views.pages.export",
}

PAGE_IDS = {
    "PAGE_WELCOME": 0,
    "PAGE_CASE_SELECTION": 1,
    "PAGE_PARTY": 2,
    "PAGE_LOAN_CLAIM": 3,
    "PAGE_CONTRACT_CLAIM": 4,
    "PAGE_PROPERTY_CLAIM": 5,
    "PAGE_LABOR_CLAIM": 6,
    "PAGE_DIVORCE_CLAIM": 7,
    "PAGE_EVIDENCE": 8,
    "PAGE_EXPORT": 9,
}

CLAIM_PAGE_ATTR = {
    "loan": ("PAGE_LOAN_CLAIM", "loan_claim_page"),
    "contract": ("PAGE_CONTRACT_CLAIM", "contract_claim_page"),
    "property": ("PAGE_PROPERTY_CLAIM", "property_claim_page"),
    "labor": ("PAGE_LABOR_CLAIM", "labor_claim_page"),
    "divorce": ("PAGE_DIVORCE_CLAIM", "divorce_claim_page"),
}


@pytest.mark.parametrize("class_name,owner", sorted(PAGE_OWNERS.items()))
def test_facade_resolves_to_the_same_class_object(class_name, owner):
    """The legacy import path and the new owner module yield one class object."""
    import importlib

    owner_module = importlib.import_module(owner)
    owner_class = getattr(owner_module, class_name)
    facade_class = getattr(facade, class_name)
    assert facade_class is owner_class
    assert facade_class.__module__ == owner  # defined in (not imported into) the owner


def test_facade_has_no_duplicate_page_implementations():
    """The facade source must contain imports only — no class definitions."""
    source = (Path(__file__).resolve().parents[1] / "views" / "wizard_pages.py").read_text(
        encoding="utf-8"
    )
    assert "class " not in source
    assert "def _set_status" not in source
    assert "def _dedup_messages" not in source


def test_shared_helpers_have_one_implementation():
    assert facade._set_status is pages_common._set_status
    assert facade._dedup_messages is pages_common._dedup_messages
    assert facade._decimal_validator is pages_common._decimal_validator
    assert facade._wrap_in_scroll is pages_common._wrap_in_scroll


def test_base_page_cleanup_preservation_survives_extraction():
    """The deliberate cleanupPage() no-op (Back/Next data preservation)."""
    assert facade._TitledPage is pages_base._TitledPage
    assert "cleanupPage" in pages_base._TitledPage.__dict__


def test_page_ids_unchanged(qapp):
    wizard, _ = make_wizard()
    for name, value in PAGE_IDS.items():
        assert getattr(wizard, name) == value, name


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_pages_register_with_expected_ids_and_instances(qapp, case_type):
    wizard, _ = make_wizard()
    page_id, attr = CLAIM_PAGE_ATTR[case_type]
    page = getattr(wizard, attr)
    assert wizard.page(getattr(wizard, page_id)) is page
    owner_name = {
        "loan": "LoanClaimPage", "contract": "ContractClaimPage",
        "property": "PropertyClaimPage", "labor": "LaborClaimPage",
        "divorce": "DivorceClaimPage",
    }[case_type]
    assert type(page) is getattr(facade, owner_name)


def test_real_button_navigation_across_all_five_case_types(qapp):
    """Real QWizard buttons drive welcome → selection → party → claim →
    evidence → export for every case type, then Back preserves input."""
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()

    next_btn = wizard.button(QWizard.NextButton)
    back_btn = wizard.button(QWizard.BackButton)

    for case_type in CASE_TYPES:
        while wizard.currentId() != wizard.PAGE_WELCOME:
            wizard.back()
        select_case(wizard, case_type)
        next_btn.click()  # welcome -> case selection
        next_btn.click()  # case selection -> party
        set_parties(wizard)
        next_btn.click()  # -> claim page
        page_id, attr = CLAIM_PAGE_ATTR[case_type]
        assert wizard.currentId() == getattr(wizard, page_id), case_type
        fill_case_facts(wizard, case_type)
        qapp.processEvents()
        next_btn.click()  # -> evidence
        assert wizard.currentId() == wizard.PAGE_EVIDENCE
        next_btn.click()  # -> export
        assert wizard.currentId() == wizard.PAGE_EXPORT

        back_btn.click()
        qapp.processEvents()
        assert wizard.currentId() == wizard.PAGE_EVIDENCE
        back_btn.click()
        qapp.processEvents()
        assert wizard.currentId() == getattr(wizard, page_id)
        # Entered facts survive the backward navigation (cleanupPage contract).
        assert _claim_page_has_values(wizard, case_type)


def _claim_page_has_values(wizard, case_type):
    page = getattr(wizard, CLAIM_PAGE_ATTR[case_type][1])
    probe = {
        "loan": ("loan_date", "principal"),
        "contract": ("contract_date", "unpaid_amount"),
        "property": ("property_addr", "house_area"),
        "labor": ("emp_join_date", "monthly_salary"),
        "divorce": ("marriage_date", "child_name"),
    }[case_type]
    return all(getattr(page, name).text().strip() for name in probe)


def test_claim_page_public_widget_attributes_preserved(qapp):
    """Existing public widget attributes consumed by presenters and tests."""
    wizard, _ = make_wizard()
    prepare = {
        "loan": ("loan_claim_page", ["loan_date", "loan_reason", "principal", "rate",
                                     "court_name", "iou_yes", "iou_no", "iou_unknown"]),
        "contract": ("contract_claim_page", ["contract_date", "unpaid_amount", "penalty_amount",
                                             "overdue_start", "overdue_end", "lpr_value",
                                             "lpr_multiple", "del_yes", "sign_yes",
                                             "calc_daily_btn", "calc_lpr_btn"]),
        "property": ("property_claim_page", ["property_addr", "house_area", "fee_rate",
                                             "period_start", "period_end", "total_input",
                                             "calc_label", "warn_label"]),
        "labor": ("labor_claim_page", ["emp_join_date", "monthly_salary", "unpaid_months",
                                       "social_sec_info", "no_contract_yes", "arbitration_notice"]),
        "divorce": ("divorce_claim_page", ["marriage_date", "child_name", "support_monthly",
                                           "asset_description", "child_help"]),
    }
    for case_type, (attr, widgets) in prepare.items():
        select_case(wizard, case_type)
        page = getattr(wizard, attr)
        for widget in widgets:
            assert hasattr(page, widget), (case_type, widget)


def test_evidence_state_constants_preserved(qapp):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    assert page.NOT_INITIALIZED == "NOT_INITIALIZED"
    assert page.INITIALIZED_WITH_SUGGESTIONS == "INITIALIZED_WITH_SUGGESTIONS"
    assert page.USER_MODIFIED == "USER_MODIFIED"
    assert page.USER_EXPLICITLY_CLEARED == "USER_EXPLICITLY_CLEARED"


def test_party_page_public_state_preserved(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)
    page = wizard.party_page
    for attr in ("plaintiff_widgets", "defendant_widgets", "current_case_type",
                 "is_initialized", "msg_label", "scroll_area"):
        assert hasattr(page, attr), attr
    assert page.is_initialized is True


def test_preview_dialog_importable_from_both_paths(qapp):
    from views.pages.export import _PreviewDialog as direct
    assert facade._PreviewDialog is direct


def test_no_absolute_positioning_in_any_page_module():
    pages_dir = Path(__file__).resolve().parents[1] / "views" / "pages"
    for source in pages_dir.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "setGeometry(" not in text, source.name
        assert ".move(" not in text, source.name


def test_no_module_level_qapplication_construction():
    pages_dir = Path(__file__).resolve().parents[1] / "views" / "pages"
    for source in pages_dir.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "QApplication(" not in text, source.name
