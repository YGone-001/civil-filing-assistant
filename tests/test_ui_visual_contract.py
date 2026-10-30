# File: tests/test_ui_visual_contract.py
# Purpose: Visual-contract tests for the redesigned theme (P3B-02 / P3B-13).
# Encoding: UTF-8
"""Assertions over the design-token system and the rendered pages.

These are deliberately non-pixel tests: they assert the presence and
coherence of the stylesheet contract (focus rings, distinct hover/selected
card states, party-card styling) and that every page actually renders
offscreen, rather than comparing screenshots.
"""

import pytest

from views.theme import (
    APP_STYLESHEET,
    CASE_CARD,
    CASE_CARD_SELECTED,
    COLOR_FOCUS,
    PARTY_CARD,
    PRIMARY_BUTTON,
)

from helpers import CASE_TYPES, fill_case_facts, make_wizard, prepare_case, select_case


def test_focus_ring_contract_is_defined_for_critical_inputs():
    """Keyboard focus must draw a 2px primary ring on inputs and buttons."""
    assert "QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus" in APP_STYLESHEET
    assert f"border: 2px solid {COLOR_FOCUS}" in APP_STYLESHEET
    # Buttons and case cards carry the same ring.
    assert "QPushButton:focus" in APP_STYLESHEET
    assert f"QPushButton#{CASE_CARD}:focus" in APP_STYLESHEET


def test_case_card_states_are_visually_distinct():
    """Hover tints only the accent; selection combines a 2px border, a tinted
    surface and a bold title (never colour alone)."""
    hover_at = APP_STYLESHEET.find(f"QPushButton#{CASE_CARD}:hover")
    selected_at = APP_STYLESHEET.find(f"QPushButton#{CASE_CARD}[{CASE_CARD_SELECTED}=\"true\"]")
    assert hover_at != -1 and selected_at != -1
    hover_block = APP_STYLESHEET[hover_at:selected_at]
    selected_block = APP_STYLESHEET[selected_at:selected_at + 600]

    assert "font-weight" not in hover_block, "hover must not look selected"
    assert "font-weight" in selected_block
    assert f"border: 2px solid" in selected_block
    # The selected title turns bold and primary via the descendant rule.
    assert f"QPushButton#{CASE_CARD}[{CASE_CARD_SELECTED}=\"true\"] QLabel#caseCardTitle" in APP_STYLESHEET


def test_party_card_styling_rule_exists():
    assert f"QGroupBox#{PARTY_CARD}" in APP_STYLESHEET
    assert f"QGroupBox#{PARTY_CARD}::title" in APP_STYLESHEET


def test_theme_tokens_are_coherent_no_role_duplicates():
    """The five status backgrounds must stay distinct roles, and the focus
    token must be defined rather than duplicated ad hoc in QSS strings."""
    from views import theme

    status_bgs = {
        "info": theme.COLOR_INFO_BG,
        "reminder": theme.COLOR_REMINDER_BG,
        "warning": theme.COLOR_WARNING_BG,
        "error": theme.COLOR_ERROR_BG,
        "success": theme.COLOR_SUCCESS_BG,
    }
    assert len(set(status_bgs.values())) == len(status_bgs)
    assert theme.COLOR_FOCUS == theme.COLOR_PRIMARY
    assert theme.FOCUS_BORDER_WIDTH == 2


def test_welcome_page_communicates_capabilities_and_hides_demo(qapp):
    wizard, _ = make_wizard()
    page = wizard.welcome_page
    labels = " ".join(child.text() for child in page.findChildren(type(page.demo_badge)))
    assert "五类常见案由" in labels
    # Demo controls stay hidden in production mode.
    assert page.fill_btn.isHidden()
    assert page.demo_badge.isHidden()


def test_evidence_table_presentation_settings(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    table = wizard.evidence_page.table
    assert table.verticalHeader().defaultSectionSize() == 34
    assert table.alternatingRowColors() is True


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_every_page_renders_offscreen(qapp, case_type):
    """Each claim page must produce a non-trivial render (no blank page)."""
    wizard, _ = make_wizard()
    prepare_case(wizard, case_type)
    page = getattr(wizard, {
        "loan": "loan_claim_page", "contract": "contract_claim_page",
        "property": "property_claim_page", "labor": "labor_claim_page",
        "divorce": "divorce_claim_page",
    }[case_type])
    pixmap = page.grab()
    assert not pixmap.isNull()
    assert pixmap.width() >= 200 and pixmap.height() >= 200


def test_wizard_window_renders_styled(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.show()
    qapp.processEvents()
    pixmap = wizard.grab()
    assert not pixmap.isNull()
    assert pixmap.width() >= 400
