# File: tests/test_date_input.py
# Purpose: Calendar-backed date field contract across the wizard.
# Encoding: UTF-8
"""Date inputs must keep the plain-text contract used by drafts and wizard
fields, while offering a calendar and refusing obviously impossible future
dates in the popup."""

from PySide6.QtCore import QDate

from helpers import make_wizard, set_parties
from models.validation import DateStatus, parse_full_date
from views.widgets import DateLineEdit


def test_date_line_edit_keeps_the_text_interface(qapp):
    edit = DateLineEdit()
    edit.setText("2023-1-2")
    assert edit.text() == "2023-1-2"
    assert parse_full_date(edit.text()).status == DateStatus.VALID

    edit.setPlaceholderText("格式 YYYY-MM-DD")
    assert edit.placeholderText() == "格式 YYYY-MM-DD"


def test_calendar_selection_writes_an_iso_date(qapp):
    edit = DateLineEdit()
    edit._apply_calendar_date(QDate(2023, 1, 2))
    assert edit.text() == "2023-01-02"


def test_restrict_future_caps_the_calendar_popup(qapp):
    edit = DateLineEdit(restrict_future=True)
    popup = edit._ensure_calendar_popup()
    assert popup.maximumDate() == QDate.currentDate()
    assert edit.restrict_future() is True


def test_case_pages_use_calendar_date_fields(qapp):
    wizard, _ = make_wizard()
    expected = {
        "loan_claim_page": ("loan_date", "start_date"),
        "contract_claim_page": (
            "contract_date", "delivery_date", "overdue_start", "overdue_end"
        ),
        "property_claim_page": ("period_start", "period_end"),
        "labor_claim_page": (
            "emp_join_date", "emp_term_date", "arb_receipt_date",
            "arb_application_date", "arb_acceptance_date",
        ),
        "divorce_claim_page": (
            "marriage_date", "separation_start_date", "child_birthday"
        ),
    }
    for page_attr, attributes in expected.items():
        page = getattr(wizard, page_attr)
        for attribute in attributes:
            assert isinstance(getattr(page, attribute), DateLineEdit), (
                page_attr, attribute
            )


def test_party_birth_date_uses_the_calendar_field(qapp):
    wizard, _ = make_wizard()
    set_parties(wizard)
    for card in wizard.party_page.plaintiff_widgets + wizard.party_page.defendant_widgets:
        assert isinstance(card["birth"], DateLineEdit)
        assert card["birth"].restrict_future() is True
