# File: tests/test_ui_contract.py
# Purpose: T12 — UI contract regression tests covering production/demo mode,
#          Chinese button text, step-indicator states, party card field
#          visibility, progressive validation with focus recovery, accessible
#          names, scroll-area wrapping, and status-style definitions.
# Encoding: UTF-8

"""Automated contract tests for the Qt frontend (T01–T11 surface).

These tests supplement the existing flow/e2e suites by asserting that the
*contract* the UI presents to the user — button labels, step states,
accessible names, scroll containers, status styles, and focus recovery —
remains stable across future refactors.  All data is fictional.
"""

import pytest
from PySide6.QtWidgets import (
    QScrollArea,
    QWizard,
    QPushButton,
    QLabel,
    QComboBox,
    QTableWidget,
    QLineEdit,
)

from helpers import make_wizard, select_case, set_parties, CASE_TYPES
from views.theme import (
    INFO_LABEL,
    WARNING_LABEL,
    ERROR_LABEL,
    SUCCESS_LABEL,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    DANGER_BUTTON,
    COLOR_INFO_BG,
    COLOR_WARNING_BG,
    COLOR_ERROR_BG,
    COLOR_SUCCESS_BG,
)
from views.widgets import STEP_NAMES, CASE_TYPE_LABELS


# ---------------------------------------------------------------------------
# 1. Production / demo mode
# ---------------------------------------------------------------------------


def test_demo_badge_hidden_in_production_and_visible_in_demo(qapp):
    """The demo badge must only appear when the wizard is launched in demo mode."""
    from PySide6.QtWidgets import QLabel

    prod = make_wizard()[0]
    badge = prod.welcome_page.demo_badge
    assert badge.isHidden(), "demo badge must be hidden in production"
    assert not badge.text() == "", "demo badge should have descriptive text"

    demo = make_wizard()[0]
    demo.welcome_page.set_demo_mode(True)
    assert not demo.welcome_page.demo_badge.isHidden(), "demo badge must be visible in demo"


def test_demo_mode_propagates_to_welcome_and_property_pages(qapp):
    """LawsuitWizard(demo_mode=True) must enable demo controls on both pages."""
    from views.main_window import LawsuitWizard

    wizard = LawsuitWizard(demo_mode=True)
    assert not wizard.welcome_page.fill_btn.isHidden()
    assert not wizard.property_claim_page.fill_btn.isHidden()


# ---------------------------------------------------------------------------
# 2. Chinese button text — all non-standard buttons
# ---------------------------------------------------------------------------

EXPECTED_BUTTON_TEXTS = {
    "add_p_btn": "[+] 添加原告",
    "add_d_btn": "[+] 添加被告",
    "add_row_btn": "[+] 添加证据",
    "remove_row_btn": "[-] 删除选中行",
    "change_dir_btn": "更改目录",
    "open_dir_btn": "打开输出目录",
    "preview_btn": "预览关键信息",
}


def test_party_page_button_texts_are_chinese(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    assert page.add_p_btn.text() == "[+] 添加原告"
    assert page.add_d_btn.text() == "[+] 添加被告"


def test_evidence_page_button_texts_are_chinese(qapp):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    assert page.add_row_btn.text() == "[+] 添加证据"
    assert page.remove_row_btn.text() == "[-] 删除选中行"


def test_export_page_button_texts_are_chinese(qapp):
    wizard, _ = make_wizard()
    page = wizard.export_page
    assert page.change_dir_btn.text() == "更改目录"
    assert page.open_dir_btn.text() == "打开输出目录"
    assert page.preview_btn.text() == "预览关键信息"
    assert "退出程序" in page.secure_exit_btn.text()


def test_contract_calc_buttons_are_auxiliary_and_chinese(qapp):
    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    assert "辅助" in page.calc_daily_btn.text()
    assert "辅助" in page.calc_lpr_btn.text()
    assert page.calc_daily_btn.objectName() == SECONDARY_BUTTON
    assert page.calc_lpr_btn.objectName() == SECONDARY_BUTTON


def test_welcome_fill_button_text_is_chinese(qapp):
    from views.main_window import LawsuitWizard

    wizard = LawsuitWizard(demo_mode=True)
    assert wizard.welcome_page.fill_btn.text() == "一键填写测试数据"


def test_property_fill_button_text_is_chinese(qapp):
    from views.main_window import LawsuitWizard

    wizard = LawsuitWizard(demo_mode=True)
    assert wizard.property_claim_page.fill_btn.text() == "一键填写测试数据"


def test_party_delete_button_text_is_chinese(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    # Cards are created during initializePage / set_parties.
    set_parties(wizard)
    for widget in page.plaintiff_widgets:
        assert widget["delete_btn"].text() == "删除"
    for widget in page.defendant_widgets:
        assert widget["delete_btn"].text() == "删除"


# ---------------------------------------------------------------------------
# 3. Step-indicator states for all five steps
# ---------------------------------------------------------------------------


def _all_indicators(wizard):
    return wizard._step_indicators


def test_step_indicators_count_matches_non_welcome_pages(qapp):
    wizard, _ = make_wizard()
    # 9 non-welcome pages: case-selection, party, 5 claim pages, evidence, export.
    assert len(_all_indicators(wizard)) == 9


def test_step_indicators_show_not_started_on_welcome(qapp):
    wizard, _ = make_wizard()
    wizard.restart()
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 0


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_step_indicators_update_through_full_navigation(qapp, case_type):
    """Walk the wizard to the export page and verify the step number at each stage."""
    wizard, _ = make_wizard()
    wizard.restart()
    wizard.next()  # welcome -> case selection (step 1)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 1

    select_case(wizard, case_type)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.case_label.text() == CASE_TYPE_LABELS[case_type]

    wizard.next()  # -> party (step 2)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 2

    set_parties(wizard)
    wizard.next()  # -> claim (step 3)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 3

    wizard.next()  # -> evidence (step 4)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 4

    wizard.next()  # -> export (step 5)
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert ind.current() == 5


def test_step_indicator_chip_labels_match_step_names(qapp):
    wizard, _ = make_wizard()
    ind = _all_indicators(wizard)[0]
    for chip, expected in zip(ind._chips, STEP_NAMES):
        assert expected in chip.text()


def test_step_indicator_case_label_hidden_when_no_case_selected(qapp):
    wizard, _ = make_wizard()
    wizard.restart()
    wizard.next()  # case selection page, no case chosen yet
    qapp.processEvents()
    for ind in _all_indicators(wizard):
        assert not ind.case_label.isVisible()


# ---------------------------------------------------------------------------
# 4. Party card enterprise field visibility
# ---------------------------------------------------------------------------


def test_enterprise_toggle_hides_personal_fields_and_shows_company_fields(qapp):
    """Switching a party card to enterprise mode must swap visible field groups."""
    wizard, _ = make_wizard()
    page = wizard.party_page
    set_parties(wizard)

    widget = page.plaintiff_widgets[0]
    # Default: personal mode — use isHidden() because the page may not be shown.
    assert not widget["is_company"].isChecked()
    assert not widget["id"].isHidden()
    assert widget["credit_code"].isHidden()

    # Switch to enterprise.
    widget["is_company"].setChecked(True)
    qapp.processEvents()
    assert not widget["credit_code"].isHidden()
    assert not widget["legal_rep"].isHidden()


def test_add_and_delete_party_preserves_remaining_data(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    set_parties(
        wizard,
        plaintiffs=[
            {"name": "原告甲（测试）", "id_number": "示例-甲", "address": "地址甲", "phone": "13800000000"},
            {"name": "原告乙（测试）", "id_number": "示例-乙", "address": "地址乙", "phone": "13900000000"},
        ],
    )
    assert len(page.plaintiff_widgets) == 2

    # Delete the first plaintiff card.
    page.plaintiff_widgets[0]["delete_btn"].click()
    assert len(page.plaintiff_widgets) == 1
    assert page.plaintiff_widgets[0]["name"].text() == "原告乙（测试）"


# ---------------------------------------------------------------------------
# 5. Progressive validation — focus recovery on claim pages
# ---------------------------------------------------------------------------


def _show_claim_page(wizard, case_type):
    """Show the wizard and navigate to the claim page so widgets can receive focus."""
    wizard.restart()
    wizard.next()  # welcome -> case selection
    select_case(wizard, case_type)
    wizard.next()  # -> party
    set_parties(wizard)
    wizard.next()  # -> claim page
    wizard.show()
    qapp = wizard.app() if hasattr(wizard, "app") else None
    if qapp is None:
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
    qapp.processEvents()
    return getattr(wizard, {
        "loan": "loan_claim_page",
        "contract": "contract_claim_page",
        "property": "property_claim_page",
        "labor": "labor_claim_page",
        "divorce": "divorce_claim_page",
    }[case_type])


def test_loan_validate_page_moves_focus_to_demand_date_on_error(qapp):
    """Partial demand info must block Next and focus the demand_date field."""
    wizard, _ = make_wizard()
    page = _show_claim_page(wizard, "loan")
    # Fill demand_date but leave demand_method empty → conditional issue.
    page.demand_date.setText("2023年10月")
    page.demand_method.setText("")

    result = page.validatePage()
    assert result is False
    assert page.cond_hint.text(), "conditional hint should be visible"
    assert page.demand_date.hasFocus()


def test_contract_validate_page_moves_focus_to_delivery_date_on_error(qapp):
    """Selecting 'delivered' without a date must block Next and focus delivery_date."""
    wizard, _ = make_wizard()
    page = _show_claim_page(wizard, "contract")
    page.del_yes.setChecked(True)
    page.delivery_date.setText("")

    result = page.validatePage()
    assert result is False
    assert page.cond_hint.text()
    assert page.delivery_date.hasFocus()


def test_divorce_validate_page_moves_focus_to_child_name_on_error(qapp):
    """Child-related fields without a child name must block Next and focus child_name."""
    wizard, _ = make_wizard()
    page = _show_claim_page(wizard, "divorce")
    page.child_name.setText("")
    page.child_birthday.setText("2020-01-01")

    result = page.validatePage()
    assert result is False
    assert page.cond_hint.text()
    assert page.child_name.hasFocus()


def test_validate_page_passes_when_no_conditional_issue(qapp):
    """A properly filled loan page must pass validatePage."""
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    page = wizard.loan_claim_page
    # Both demand fields filled → no issue.
    page.demand_date.setText("2023年10月")
    page.demand_method.setText("微信")
    assert page.validatePage() is True

    # Both empty → no issue either.
    page.demand_date.setText("")
    page.demand_method.setText("")
    assert page.validatePage() is True


# ---------------------------------------------------------------------------
# 6. _dedup_messages and _set_status helpers
# ---------------------------------------------------------------------------


def test_dedup_messages_removes_duplicates_preserving_order():
    from views.wizard_pages import _dedup_messages

    msgs = ["错误A", "错误B", "错误A", "", "  ", "错误C", "错误B"]
    assert _dedup_messages(msgs) == ["错误A", "错误B", "错误C"]


def test_dedup_messages_handles_empty_and_whitespace_only():
    from views.wizard_pages import _dedup_messages

    assert _dedup_messages([]) == []
    assert _dedup_messages(["", "  ", "\t"]) == []


def test_set_status_hides_label_on_empty_text(qapp):
    from views.wizard_pages import _set_status

    wizard, _ = make_wizard()
    label = wizard.party_page.msg_label
    _set_status(label, "some message")
    assert not label.isHidden()
    assert label.text() == "some message"

    _set_status(label, "")
    assert label.isHidden()


# ---------------------------------------------------------------------------
# 7. Status style definitions (T09)
# ---------------------------------------------------------------------------


def test_five_status_label_object_names_are_distinct():
    names = {INFO_LABEL, WARNING_LABEL, ERROR_LABEL, SUCCESS_LABEL}
    assert len(names) == 4
    assert INFO_LABEL == "infoLabel"
    assert WARNING_LABEL == "warningLabel"
    assert ERROR_LABEL == "errorLabel"
    assert SUCCESS_LABEL == "successLabel"


def test_five_status_color_tokens_are_defined_and_distinct():
    colors = {COLOR_INFO_BG, COLOR_WARNING_BG, COLOR_ERROR_BG, COLOR_SUCCESS_BG}
    assert len(colors) == 4
    for c in colors:
        assert c.startswith("#")


def test_status_labels_use_warning_not_error_for_conditional_hints(qapp):
    """Conditional hints (form-level advisories) must use WARNING_LABEL, not ERROR_LABEL."""
    wizard, _ = make_wizard()
    # Loan page conditional hint.
    assert wizard.loan_claim_page.cond_hint.objectName() == WARNING_LABEL
    assert wizard.contract_claim_page.cond_hint.objectName() == WARNING_LABEL
    assert wizard.divorce_claim_page.cond_hint.objectName() == WARNING_LABEL


# ---------------------------------------------------------------------------
# 8. Accessible names on key controls (T10)
# ---------------------------------------------------------------------------


def test_case_combo_has_accessible_name(qapp):
    wizard, _ = make_wizard()
    combo = wizard.case_selection_page.case_combo
    assert combo.accessibleName() == "案由选择"
    assert combo.accessibleDescription() == "选择起诉状的案件类型"


def test_party_buttons_have_accessible_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    assert page.add_p_btn.accessibleName() == "添加原告"
    assert page.add_d_btn.accessibleName() == "添加被告"


def test_party_delete_buttons_have_dynamic_accessible_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    set_parties(wizard)
    assert page.plaintiff_widgets[0]["delete_btn"].accessibleName() == "删除原告卡片"
    assert page.defendant_widgets[0]["delete_btn"].accessibleName() == "删除被告卡片"


def test_evidence_controls_have_accessible_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    assert page.add_row_btn.accessibleName() == "添加证据行"
    assert page.remove_row_btn.accessibleName() == "删除选中的证据行"
    assert page.table.accessibleName() == "证据清单表格"
    assert "编辑" in page.table.accessibleDescription()


def test_export_buttons_have_accessible_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.export_page
    assert page.change_dir_btn.accessibleName() == "更改输出目录"
    assert page.open_dir_btn.accessibleName() == "打开输出目录"
    assert page.preview_btn.accessibleName() == "预览关键信息"
    assert page.secure_exit_btn.accessibleName() == "退出程序"


def test_contract_calc_buttons_have_accessible_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    assert page.calc_daily_btn.accessibleName() == "按日万五折算违约金"
    assert page.calc_lpr_btn.accessibleName() == "按LPR倍数折算违约金"


# ---------------------------------------------------------------------------
# 9. Scroll-area wrapping on claim pages (T11)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_type,page_attr",
    [
        ("loan", "loan_claim_page"),
        ("contract", "contract_claim_page"),
        ("property", "property_claim_page"),
        ("labor", "labor_claim_page"),
        ("divorce", "divorce_claim_page"),
    ],
)
def test_claim_pages_are_wrapped_in_scroll_area(qapp, case_type, page_attr):
    """Each of the five claim pages must contain a QScrollArea for small-screen support."""
    wizard, _ = make_wizard()
    page = getattr(wizard, page_attr)
    scroll_areas = page.findChildren(QScrollArea)
    assert len(scroll_areas) >= 1, f"{page_attr} should contain at least one QScrollArea"
    assert scroll_areas[0].widgetResizable()


def test_scroll_area_has_no_frame_to_blend_with_page(qapp):
    """The scroll area must be frameless so it doesn't look like an embedded box."""
    wizard, _ = make_wizard()
    scroll_areas = wizard.loan_claim_page.findChildren(QScrollArea)
    assert scroll_areas[0].frameShape() == QScrollArea.Shape.NoFrame


# ---------------------------------------------------------------------------
# 10. Button object-name styling contract
# ---------------------------------------------------------------------------


def test_export_buttons_have_correct_object_names(qapp):
    wizard, _ = make_wizard()
    page = wizard.export_page
    assert page.change_dir_btn.objectName() == SECONDARY_BUTTON
    assert page.open_dir_btn.objectName() == SECONDARY_BUTTON
    assert page.preview_btn.objectName() == SECONDARY_BUTTON
    assert page.secure_exit_btn.objectName() == SECONDARY_BUTTON


def test_party_delete_button_has_danger_object_name(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    set_parties(wizard)
    assert page.plaintiff_widgets[0]["delete_btn"].objectName() == DANGER_BUTTON


def test_party_delete_button_has_danger_object_name(qapp):
    wizard, _ = make_wizard()
    page = wizard.party_page
    set_parties(wizard)
    assert page.plaintiff_widgets[0]["delete_btn"].objectName() == DANGER_BUTTON


def test_wizard_next_and_finish_buttons_have_primary_object_name(qapp):
    wizard, _ = make_wizard()
    assert wizard.button(QWizard.NextButton).objectName() == PRIMARY_BUTTON
    assert wizard.button(QWizard.FinishButton).objectName() == PRIMARY_BUTTON
