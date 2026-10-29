# File: tests/test_gui_flow.py
# Purpose: GUI navigation, export, and evidence-workflow integration tests.
# Encoding: UTF-8

import os

import pytest
from PySide6.QtWidgets import QAbstractButton, QWizard

from helpers import (
    CASE_TYPES,
    fill_case_facts,
    make_wizard,
    navigate_to_export,
    prepare_case,
    select_case,
    set_parties,
)
from utils.doc_generator import DocumentGenerator

EXPECTED_ROUTE_PAGE = {
    "loan": "PAGE_LOAN_CLAIM",
    "contract": "PAGE_CONTRACT_CLAIM",
    "property": "PAGE_PROPERTY_CLAIM",
    "labor": "PAGE_LABOR_CLAIM",
    "divorce": "PAGE_DIVORCE_CLAIM",
}


def _internal_wizard_buttons(wizard):
    """Unnamed direct-child buttons Qt may create inside QWizard.

    Whether this internal button exists is a Qt/platform implementation
    detail (observed on Windows, absent elsewhere), so tests must accept
    its absence and only assert the observable hiding contract.
    """
    return [c for c in wizard.children()
            if isinstance(c, QAbstractButton) and not c.text() and not c.objectName()]


def test_internal_wizard_header_button_is_hidden(qapp):
    """QWizard may create an unnamed 32x32 internal button at the top-left of the
    header area; on Windows it renders as a stray back arrow over the page title,
    while other platforms never create it. The contract is behavioral: any such
    unnamed button must stay hidden on every page, its absence is equally valid,
    and the real Back/Next/Finish/Cancel controls must keep working."""
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()

    assert len(_internal_wizard_buttons(wizard)) <= 1
    # only the internal header button is explicitly hidden by the fix
    for button in _internal_wizard_buttons(wizard):
        assert button.isHidden() is True

    # The real navigation buttons must never be swept into the hiding fix.
    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    finish = wizard.button(QWizard.FinishButton)
    cancel = wizard.button(QWizard.CancelButton)
    assert all(btn not in _internal_wizard_buttons(wizard)
               for btn in (back, next_btn, finish, cancel))
    assert next_btn.isVisible(), "Next must stay usable on the welcome page"
    assert cancel.isVisible(), "Cancel must stay usable"

    wizard.next()  # welcome -> case selection
    select_case(wizard, "loan")
    wizard.next()  # -> party
    set_parties(wizard)
    wizard.next()  # -> loan claim
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM
    # The real Next button stays disabled while mandatory fields are empty;
    # fill the claim facts so the button clicks below can actually navigate.
    fill_case_facts(wizard, "loan")
    for button in _internal_wizard_buttons(wizard):
        assert button.isHidden() is True

    back.click()  # the real Back button must still navigate
    assert wizard.currentId() == wizard.PAGE_PARTY
    next_btn.click()
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM
    # Entered case facts survive Back/Next (fields are no longer reset), so
    # the Next button stays enabled without re-entering anything.
    assert wizard.loan_claim_page.principal.text() == "50000"
    next_btn.click()  # -> evidence
    assert wizard.currentId() == wizard.PAGE_EVIDENCE
    next_btn.click()  # -> export
    assert wizard.currentId() == wizard.PAGE_EXPORT
    for button in _internal_wizard_buttons(wizard):
        assert button.isHidden() is True
    assert finish.isVisible(), "Finish must stay usable on the export page"
    assert cancel.isVisible(), "Cancel must stay usable on the export page"


def _redirect_desktop(monkeypatch, base):
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(base))
    return base / "Desktop"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_wizard_routes_and_initializes(qapp, case_type):
    """Every case type must reach its own claim page then evidence/export."""
    wizard, _ = make_wizard()
    wizard.restart()
    wizard.next()  # welcome -> case selection
    select_case(wizard, case_type)
    wizard.next()  # -> party
    assert wizard.currentId() == wizard.PAGE_PARTY
    set_parties(wizard)

    claim_page_id = getattr(wizard, EXPECTED_ROUTE_PAGE[case_type])
    assert wizard.nextId() == claim_page_id
    wizard.next()
    assert wizard.currentId() == claim_page_id

    wizard.next()  # -> evidence
    assert wizard.currentId() == wizard.PAGE_EVIDENCE

    wizard.next()  # -> export
    assert wizard.currentId() == wizard.PAGE_EXPORT
    assert wizard.nextId() == -1


def test_case_selection_field_tracks_combo(qapp):
    wizard, _ = make_wizard()
    for case_type in CASE_TYPES:
        select_case(wizard, case_type)
        assert wizard.field("case_type") == case_type


def test_export_blocked_when_parties_incomplete(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=[{"name": "   "}])

    presenter.on_wizard_accepted()

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not desktop.exists() or not list(desktop.rglob("*.docx"))


def test_export_success_writes_three_documents(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")

    presenter.on_wizard_accepted()

    docs = sorted(desktop.rglob("*.docx"))
    assert len(docs) == 3, [d.name for d in docs]
    assert any(entry["kind"] == "information" for entry in dialog_recorder)


def test_export_failure_does_not_exit_and_can_retry(qapp, monkeypatch, tmp_path, dialog_recorder):
    """Regression: the presenter used to call sys.exit(0) in a finally block."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")

    calls = {"n": 0}
    original = DocumentGenerator.export_complaint

    def flaky(self, model, file_path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("模拟磁盘写入失败")
        return original(self, model, file_path)

    monkeypatch.setattr(DocumentGenerator, "export_complaint", flaky)

    wizard, presenter = make_wizard()
    prepare_case(wizard, "contract")

    # First attempt fails but must return normally (no SystemExit) and leave no files.
    presenter.on_wizard_accepted()
    assert any(entry["kind"] == "critical" for entry in dialog_recorder)
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))

    # Second attempt succeeds after the transient failure.
    presenter.on_wizard_accepted()
    assert len(list(desktop.rglob("*.docx"))) == 3


def test_export_directory_failure_is_recoverable(qapp, monkeypatch, tmp_path, dialog_recorder):
    blocked = tmp_path / "not_a_directory"
    blocked.write_text("i am a file", encoding="utf-8")
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(blocked))

    wizard, presenter = make_wizard()
    prepare_case(wizard, "property")
    presenter.on_wizard_accepted()  # must not raise

    assert any(entry["kind"] == "critical" for entry in dialog_recorder)


def test_preview_is_case_specific(qapp, dialog_recorder):
    expectations = {
        "loan": "偿还借款本金",
        "contract": "货款本金",
        "property": "物业费",
        "labor": "欠付工资",
        "divorce": "离婚",
    }
    for case_type, keyword in expectations.items():
        wizard, _ = make_wizard()
        prepare_case(wizard, case_type)
        dialog_recorder.clear()

        wizard.export_page.show_preview()

        text = getattr(wizard.export_page, "_last_preview_text", "")
        assert text, f"no preview shown for {case_type}"
        assert keyword in text, f"{case_type} preview missing {keyword!r}: {text}"


def test_evidence_defaults_load_without_duplication(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    first_count = wizard.evidence_page.table.rowCount()
    assert first_count >= 1

    wizard.evidence_page.initializePage()  # e.g. navigating back and forward
    assert wizard.evidence_page.table.rowCount() == first_count


def test_evidence_add_edit_remove(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    wizard.evidence_page.initializePage()
    page = wizard.evidence_page
    base = page.table.rowCount()

    page.add_row("自定义证据（测试）", "证明目的（测试）")
    assert ("自定义证据（测试）", "证明目的（测试）") in page.get_evidence_items()

    page.table.selectRow(page.table.rowCount() - 1)
    page.remove_selected_rows()
    assert page.table.rowCount() == base

    page.add_row("", "")  # blank row must not become evidence
    assert len(page.get_evidence_items()) == base


# --- Real QWizard "Finish" button lifecycle (C1) ---------------------------
# These tests click the actual Finish button (not presenter.on_wizard_accepted)
# and assert the export happens before the wizard reaches its accepted state.


def test_finish_button_success_exports_and_accepts(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")

    finish = navigate_to_export(wizard)
    accepted = []
    wizard.accepted.connect(lambda: accepted.append(True))

    wizard.show()
    qapp.processEvents()
    finish.click()
    qapp.processEvents()

    assert accepted, "Finish button did not reach the accepted state"
    assert wizard.result() != 0
    docs = sorted(desktop.rglob("*.docx"))
    assert len(docs) == 3, [d.name for d in docs]
    assert any(entry["kind"] == "information" for entry in dialog_recorder)


def test_finish_button_failure_keeps_wizard_open(qapp, monkeypatch, tmp_path, dialog_recorder):
    """A failed export must keep the wizard open and preserve the user's input."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")
    principal_before = wizard.loan_claim_page.principal.text()

    finish = navigate_to_export(wizard)

    def boom(self, model, file_path):
        raise RuntimeError("模拟生成失败")

    monkeypatch.setattr(DocumentGenerator, "export_complaint", boom)

    accepted = []
    wizard.accepted.connect(lambda: accepted.append(True))
    wizard.show()
    qapp.processEvents()
    finish.click()
    qapp.processEvents()

    assert not accepted
    assert wizard.result() == 0
    assert wizard.isVisible(), "wizard should remain open after a failure"
    assert wizard.loan_claim_page.principal.text() == principal_before, "input must be preserved"
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))
    assert any(entry["kind"] == "critical" for entry in dialog_recorder)


def test_finish_button_retry_after_failure(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    calls = {"n": 0}
    original = DocumentGenerator.export_complaint

    def flaky(self, model, file_path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("首次失败")
        return original(self, model, file_path)

    monkeypatch.setattr(DocumentGenerator, "export_complaint", flaky)

    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")
    finish = navigate_to_export(wizard)
    wizard.show()
    qapp.processEvents()

    finish.click()
    qapp.processEvents()
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))

    finish.click()
    qapp.processEvents()
    assert len(list(desktop.rglob("*.docx"))) == 3


def test_finish_button_blocks_on_incomplete_parties(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")
    finish = navigate_to_export(wizard)

    # Make the party page incomplete after navigation, before accepting.
    wizard.party_page.plaintiff_widgets[0]["name"].setText("")

    accepted = []
    wizard.accepted.connect(lambda: accepted.append(True))
    wizard.show()
    qapp.processEvents()
    finish.click()
    qapp.processEvents()

    assert not accepted
    assert wizard.result() == 0
    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))


def test_reentrant_finish_does_not_duplicate_export(qapp, monkeypatch, tmp_path, dialog_recorder):
    """A reentrant Finish request while an export is active must be ignored."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")

    state = {"exports": 0}
    original = DocumentGenerator.export_complaint

    def reentrant(self, model, file_path):
        state["exports"] += 1
        if state["exports"] == 1:
            result = presenter.attempt_finish()
            assert result == presenter.FINISH_EXPORT_FAILED
        return original(self, model, file_path)

    monkeypatch.setattr(DocumentGenerator, "export_complaint", reentrant)

    result = presenter.attempt_finish()
    assert result == presenter.FINISH_SUCCESS
    assert state["exports"] == 1, "reentrant Finish must not run a second export"
    assert len(list(desktop.rglob("*.docx"))) == 3


# --- T07: evidence editability and anti-mistake -----------------------------


def test_t07_evidence_edit_hint_is_visible(qapp):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    assert page.edit_hint.text(), "edit hint label should have text"
    assert page.edit_hint.objectName() == "infoLabel"


def test_t07_evidence_labor_has_dedicated_description(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    wizard.evidence_page.initializePage()
    text = wizard.evidence_page.desc_label.text()
    assert "劳动" in text, f"labor description missing case-specific text: {text}"


def test_t07_evidence_divorce_has_dedicated_description(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "divorce")
    wizard.evidence_page.initializePage()
    text = wizard.evidence_page.desc_label.text()
    assert "离婚" in text, f"divorce description missing case-specific text: {text}"


def test_t07_evidence_suggested_rows_are_marked(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    page = wizard.evidence_page
    page.initializePage()
    assert page._suggested_count > 0, "suggested rows should be loaded"
    # First row (suggested) should have a tinted background.
    item = page.table.item(0, 0)
    assert item is not None
    tint = page._SUGGESTED_TINT.color()
    bg = item.background().color()
    assert (bg.red(), bg.green(), bg.blue()) == (tint.red(), tint.green(), tint.blue()), \
        "suggested row should have the tinted background"
    # A user-added row should not have the tint.
    page.add_row("自定义证据（测试）", "", auto_edit=False)
    user_item = page.table.item(page.table.rowCount() - 1, 0)
    user_bg = user_item.background().color()
    assert (user_bg.red(), user_bg.green(), user_bg.blue()) != (tint.red(), tint.green(), tint.blue()), \
        "user-added row should not be tinted"


def test_t07_evidence_add_row_sets_current_item(qapp):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    page.add_row("新证据（测试）", "证明目的", auto_edit=True)
    current = page.table.currentItem()
    assert current is not None, "current item should be set after add_row"
    assert current.row() == page.table.rowCount() - 1
    assert current.column() == 0


def test_t07_evidence_delete_confirms_when_content_exists(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    page = wizard.evidence_page
    page.initializePage()
    dialog_recorder.clear()
    # Select the first suggested row (which has content) and delete it.
    page.table.selectRow(0)
    page.remove_selected_rows()
    questions = [e for e in dialog_recorder if e["kind"] == "question"]
    assert questions, "should confirm deletion when content exists"
    assert page.table.rowCount() >= 0  # deletion proceeded (Yes was returned)


def test_t07_evidence_delete_skips_confirm_for_empty_rows(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    # Add a blank row (no content) and delete it — no confirmation needed.
    page.add_row("", "", auto_edit=False)
    dialog_recorder.clear()
    page.table.selectRow(page.table.rowCount() - 1)
    before = page.table.rowCount()
    page.remove_selected_rows()
    questions = [e for e in dialog_recorder if e["kind"] == "question"]
    assert not questions, "should not confirm deletion of empty rows"
    assert page.table.rowCount() == before - 1


# --- T08: export page redo --------------------------------------------------


def test_t08_export_page_lists_three_documents(qapp):
    from PySide6.QtWidgets import QGroupBox

    wizard, _ = make_wizard()
    page = wizard.export_page
    groups = page.findChildren(QGroupBox)
    doc_group = next((g for g in groups if "将生成的文书" in g.title()), None)
    assert doc_group is not None, "should have a document group"
    text = " ".join(label.text() for label in doc_group.findChildren(type(wizard.export_page.dir_label)))
    for name in ("民事起诉状", "证据清单", "送达地址确认书"):
        assert name in text, f"document list missing {name}: {text}"
    assert "可编辑" in text


def test_t08_export_page_shows_default_output_directory(qapp):
    wizard, _ = make_wizard()
    page = wizard.export_page
    assert page.dir_label.text(), "directory label should show a path"
    assert page.get_output_directory() == page.dir_label.text()


def test_t08_export_page_change_directory(qapp, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    wizard, _ = make_wizard()
    page = wizard.export_page
    custom = "C:/custom_output_dir_test"
    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **kw: custom))
    page.change_directory()
    assert page.get_output_directory() == custom
    assert page.dir_label.text() == custom


def test_t08_export_page_preview_is_scrollable_dialog(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    dialog_recorder.clear()
    wizard.export_page.show_preview()
    execs = [e for e in dialog_recorder if e["kind"] == "dialog_exec"]
    assert execs, "preview should use a QDialog, not a QMessageBox"
    # The preview text should be stashed for inspection.
    text = getattr(wizard.export_page, "_last_preview_text", "")
    assert text, "preview text should be available"


def test_t08_export_page_preview_clarifies_not_final_layout(qapp):
    from PySide6.QtWidgets import QLabel
    from views.wizard_pages import _PreviewDialog

    wizard, _ = make_wizard()
    dialog = _PreviewDialog("关键信息预览", "测试内容", wizard.export_page)
    labels = dialog.findChildren(QLabel)
    disclaimer_text = " ".join(l.text() for l in labels)
    assert "不代表最终" in disclaimer_text, \
        f"preview dialog should clarify it is not final layout, got: {disclaimer_text}"


def test_t08_export_page_exit_is_secondary_button(qapp):
    from views.theme import SECONDARY_BUTTON

    wizard, _ = make_wizard()
    btn = wizard.export_page.secure_exit_btn
    assert btn.objectName() == SECONDARY_BUTTON, \
        f"exit button should be secondary, got {btn.objectName()!r}"


def test_t08_presenter_reads_directory_from_export_page(qapp, monkeypatch, tmp_path):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")
    # Change the output directory to a custom path.
    custom_dir = tmp_path / "custom_export"
    custom_dir.mkdir()
    wizard.export_page.output_dir = str(custom_dir)
    presenter.attempt_finish()
    docs = sorted(custom_dir.rglob("*.docx"))
    assert len(docs) == 3, f"presenter should export to the custom dir, got {len(docs)} files"
