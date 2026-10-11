"""Regression coverage for the UI-foundation work in T01–T03."""

from PySide6.QtWidgets import QMessageBox, QWizard

from main import _parse_args
from views.main_window import LawsuitWizard
from views.theme import PRIMARY_BUTTON
from views.widgets import CASE_TYPE_LABELS


def test_wizard_navigation_is_localized_and_primary(qapp):
    wizard = LawsuitWizard()

    assert wizard.button(QWizard.BackButton).text() == "上一步"
    assert wizard.button(QWizard.NextButton).text() == "下一步"
    assert wizard.button(QWizard.FinishButton).text() == "生成三份 Word 初稿"
    assert wizard.button(QWizard.CancelButton).text() == "退出"
    assert wizard.button(QWizard.NextButton).objectName() == PRIMARY_BUTTON
    assert wizard.button(QWizard.FinishButton).objectName() == PRIMARY_BUTTON

    page_titles = [
        wizard.case_selection_page.title(),
        wizard.party_page.title(),
        wizard.loan_claim_page.title(),
        wizard.contract_claim_page.title(),
        wizard.property_claim_page.title(),
        wizard.labor_claim_page.title(),
        wizard.divorce_claim_page.title(),
        wizard.evidence_page.title(),
        wizard.export_page.title(),
    ]
    assert all(not title.startswith("第") for title in page_titles)


def test_demo_mode_requires_an_explicit_launch_flag():
    assert not _parse_args([]).demo_mode
    assert _parse_args(["--demo"]).demo_mode
    assert _parse_args(["--dev"]).demo_mode


def test_case_context_indicator_refreshes_when_selection_changes(qapp):
    wizard = LawsuitWizard()
    wizard.restart()
    wizard.next()  # welcome -> case selection

    wizard.case_selection_page.case_combo.setCurrentIndex(3)  # labor
    qapp.processEvents()

    assert all(indicator.current() == 1 for indicator in wizard._step_indicators)
    assert all(
        indicator.case_label.text() == CASE_TYPE_LABELS["labor"]
        for indicator in wizard._step_indicators
    )


def test_demo_controls_are_hidden_in_production_and_guard_property_data(
    qapp, monkeypatch, dialog_recorder
):
    production = LawsuitWizard()
    assert production.welcome_page.fill_btn.isHidden()
    assert production.property_claim_page.fill_btn.isHidden()

    wizard = LawsuitWizard(demo_mode=True)
    assert not wizard.welcome_page.fill_btn.isHidden()
    assert not wizard.property_claim_page.fill_btn.isHidden()

    wizard.case_selection_page.case_combo.setCurrentIndex(2)  # property
    wizard.property_claim_page.property_addr.setText("已填写的虚构地址")

    calls = []

    def decline(*args, **kwargs):
        calls.append((args, kwargs))
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", decline)
    wizard.property_claim_page.fill_btn.click()

    assert calls
    assert wizard.property_claim_page.property_addr.text() == "已填写的虚构地址"
    assert not [call for call in dialog_recorder if call["kind"] == "information"]


def test_property_demo_fill_shows_one_completion_notice(qapp, dialog_recorder):
    wizard = LawsuitWizard(demo_mode=True)
    wizard.case_selection_page.case_combo.setCurrentIndex(2)  # property

    wizard.property_claim_page.fill_btn.click()

    assert wizard.property_claim_page.property_addr.text() == "幸福里小区 3 栋 1201 室"
    notices = [call for call in dialog_recorder if call["kind"] == "information"]
    assert len(notices) == 1
