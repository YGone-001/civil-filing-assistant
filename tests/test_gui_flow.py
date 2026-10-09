# File: tests/test_gui_flow.py
# Purpose: GUI navigation, export, and evidence-workflow integration tests.
# Encoding: UTF-8

import os

import pytest

from helpers import (
    CASE_TYPES,
    make_wizard,
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

        infos = [e for e in dialog_recorder if e["kind"] == "information"]
        assert infos, f"no preview shown for {case_type}"
        text = " ".join(str(a) for a in infos[-1]["args"])
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
