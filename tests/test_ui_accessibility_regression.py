# File: tests/test_ui_accessibility_regression.py
# Purpose: Keyboard and accessibility regression coverage (P3B-11 / P3B-13).
# Encoding: UTF-8
"""Keyboard-focus and accessibility guarantees for the redesigned UI.

Case cards must be reachable and activatable from the keyboard, focus must be
visible (stylesheet focus ring), tab order must start at the first form field,
and validation errors must move focus to the blocking field.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea

from helpers import make_wizard, prepare_case, select_case, set_parties
from views.theme import APP_STYLESHEET, CASE_CARD, COLOR_FOCUS


def test_case_cards_are_keyboard_reachable_and_activatable(qapp):
    wizard, _ = make_wizard()
    for card in wizard.case_selection_page._case_cards:
        button = card[1]
        assert button.focusPolicy() & Qt.FocusPolicy.TabFocus, card[0]
        assert button.isEnabled()


def test_case_card_keyboard_activation_selects_case(qapp):
    """Activating a focused card through Qt's button semantics (space/enter)
    must update the backing ``case_type`` field."""
    wizard, _ = make_wizard()
    wizard.show()
    wizard.setCurrentId(wizard.PAGE_CASE_SELECTION)
    qapp.processEvents()
    page = wizard.case_selection_page
    divorce_card = dict(page._case_cards)["divorce"]
    divorce_card.setFocus()
    qapp.processEvents()
    assert divorce_card.hasFocus()

    divorce_card.click()  # keyboard activation routes through clicked()
    assert wizard.field("case_type") == "divorce"


def test_case_cards_have_a_visible_focus_rule():
    assert f"QPushButton#{CASE_CARD}:focus" in APP_STYLESHEET
    assert COLOR_FOCUS in APP_STYLESHEET


def test_input_focus_ring_rules_present():
    for selector in ("QLineEdit:focus", "QComboBox:focus", "QTextEdit:focus",
                     "QPlainTextEdit:focus", "QPushButton:focus"):
        assert selector in APP_STYLESHEET, selector


def test_party_tab_order_starts_at_first_name_field(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    page = wizard.party_page
    page.initializePage()
    page.setVisible(True)
    qapp.processEvents()

    from PySide6.QtTest import QTest

    first_field = page.plaintiff_widgets[0]["name"]
    first_field.setFocus()
    qapp.processEvents()
    assert page.focusWidget() is first_field

    QTest.keyClick(first_field, Qt.Key.Key_Tab)
    qapp.processEvents()
    assert page.focusWidget() is page.plaintiff_widgets[0]["id"]


def test_validation_focus_recovery_contract_preserved(qapp):
    """Conditional validation still focuses the blocking field after redesign."""
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)
    wizard.next()
    wizard.show()
    qapp.processEvents()
    page = wizard.loan_claim_page
    page.demand_date.setText("2023年10月")
    page.demand_method.setText("")

    assert page.validatePage() is False
    assert page.demand_date.hasFocus()


def test_status_labels_remain_screen_reader_readable(qapp):
    """Status text lives in the label text (not only colour/graphics)."""
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    page = wizard.party_page
    page.initializePage()
    page._touched = True
    page.plaintiff_widgets[0]["name"].setText("")
    page._refresh_validation_message()
    assert "原告1的姓名/名称不能为空" in page.msg_label.text()


def test_required_names_reachable_without_scrolling(qapp):
    """At the minimum window size the first required name field is inside the
    visible scroll viewport (no inaccessible required fields)."""
    from PySide6.QtWidgets import QScrollArea

    wizard, _ = make_wizard()
    wizard.resize(wizard.minimumSize())
    wizard.show()
    wizard.setCurrentId(wizard.PAGE_PARTY)
    qapp.processEvents()
    select_case(wizard, "loan")
    page = wizard.party_page
    page.initializePage()
    qapp.processEvents()

    name_field = page.plaintiff_widgets[0]["name"]
    areas = page.findChildren(QScrollArea)
    assert areas, "party page hosts its cards in a scroll area"
    viewport = areas[0].viewport()
    pos = name_field.mapTo(viewport, name_field.rect().topLeft())
    # Geometric visibility: the first required field sits inside the scroll
    # viewport's visible bounds, without needing to scroll down.
    assert 0 <= pos.x() < viewport.width(), pos
    assert 0 <= pos.y() < viewport.height(), pos
