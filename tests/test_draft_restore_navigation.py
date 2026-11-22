# File: tests/test_draft_restore_navigation.py
# Purpose: After opening a draft, 上一步 must follow the real wizard route.
# Encoding: UTF-8
"""Regression coverage for the restored wizard's navigation history.

Qt walks the 上一步 button through an internal visited-pages history that a
bare ``setCurrentId()`` call does not reconstruct: a restored wizard used to
hold only the welcome page behind its landing page, so Back jumped straight to
欢迎. The restore now replays the case-specific route, and these tests pin the
resulting Back/Forward behaviour for every case type and every applicable
resume position - through the real 保存草稿 / 打开草稿 presenter path where the
scenario is reachable from the UI, and through the storage layer for the
synthetic fallback drafts a live wizard cannot navigate itself into. All data
is fictional.
"""

import pytest
from PySide6.QtWidgets import QFileDialog, QWizard

from drafts import save_draft, schema
from helpers import (
    CASE_TYPES,
    make_wizard,
    prepare_case,
    select_case,
    set_parties,
)
from presenters.draft_presenter import DraftPresenter
from views.draft_io import (
    CLAIM_PAGE_ATTR_BY_CASE,
    _capture_flags,
    apply_draft,
    capture_draft,
)

CLAIM_PAGE_ID = {
    "loan": "PAGE_LOAN_CLAIM",
    "contract": "PAGE_CONTRACT_CLAIM",
    "property": "PAGE_PROPERTY_CLAIM",
    "labor": "PAGE_LABOR_CLAIM",
    "divorce": "PAGE_DIVORCE_CLAIM",
}


def _read(widget):
    return widget.toPlainText() if hasattr(widget, "toPlainText") else widget.text()


def _claim_page(wizard, case_type):
    return getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])


def _claim_snapshot(wizard, case_type):
    page = _claim_page(wizard, case_type)
    return {
        spec.key: _read(getattr(page, spec.widget))
        for spec in schema.TEXT_FIELDS[case_type]
    }


def _party_snapshot(wizard):
    sides = []
    for widgets in (wizard.party_page.plaintiff_widgets, wizard.party_page.defendant_widgets):
        sides.append([
            {
                key: _read(widget[key])
                for key in ("name", "id", "addr", "phone", "credit_code", "legal_rep")
            }
            | {"is_company": widget["is_company"].isChecked()}
            for widget in widgets
        ])
    return sides


def _flags_snapshot(wizard, case_type):
    return _capture_flags(_claim_page(wizard, case_type), case_type)


def _evidence_snapshot(wizard):
    page = wizard.evidence_page
    return [
        [
            page.table.item(r, c).text() if page.table.item(r, c) else ""
            for c in range(page.table.columnCount())
        ]
        for r in range(page.table.rowCount())
    ]


def _session_snapshot(wizard, case_type):
    """Every user-restorable value, compared across Back/Forward traversal."""
    return {
        "case_type": wizard.field("case_type"),
        "parties": _party_snapshot(wizard),
        "claim": _claim_snapshot(wizard, case_type),
        "flags": _flags_snapshot(wizard, case_type),
        "evidence": _evidence_snapshot(wizard),
    }


def _back_destinations(wizard, qapp):
    """Click the real 上一步 button until it disables; return the id of every
    page the wizard stood on, ending at the page where Back turned off."""
    back = wizard.button(QWizard.BackButton)
    visited = []
    while back.isEnabled():
        visited.append(wizard.currentId())
        back.click()
        qapp.processEvents()
    visited.append(wizard.currentId())
    return visited


def _forward_replay(wizard, qapp, stops):
    """Click the real 下一步 button; return the ids landed on. ``stops`` bounds
    the walk so a validation failure (Next disabled) ends the walk cleanly."""
    landed = []
    for _ in range(stops):
        next_button = wizard.button(QWizard.NextButton)
        if not next_button.isEnabled():
            break
        next_button.click()
        qapp.processEvents()
        landed.append(wizard.currentId())
    return landed


def _route_ids(wizard, case_type):
    """The legitimate welcome->export route for *case_type*."""
    claim_id = getattr(wizard, CLAIM_PAGE_ID[case_type])
    return [
        wizard.PAGE_WELCOME,
        wizard.PAGE_CASE_SELECTION,
        wizard.PAGE_PARTY,
        claim_id,
        wizard.PAGE_EVIDENCE,
        wizard.PAGE_EXPORT,
    ]


def _save_draft_file(wizard, presenter, tmp_path, monkeypatch, name="导航草稿.cfdraft"):
    path = tmp_path / name
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(path), "")),
    )
    assert presenter.save_draft() is True
    assert path.exists()
    return path


def _open_draft_file(presenter, path, monkeypatch):
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *args, **kwargs: (str(path), "")),
    )
    assert presenter.open_draft() is True
    return presenter.wizard


def _navigate_and_save(wizard, presenter, tmp_path, monkeypatch, case_type, page_count,
                       prepare=True):
    """Fill *case_type*, walk *page_count* real steps from welcome, save there.
    Tests that already prepared the wizard with non-default fixture arguments
    (e.g. unconfirmed tri-states) pass ``prepare=False`` to keep them."""
    if prepare:
        prepare_case(wizard, case_type)
    wizard.restart()
    for _ in range(page_count):
        wizard.next()
    return _save_draft_file(wizard, presenter, tmp_path, monkeypatch)


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_export_resume_back_walks_the_full_route(qapp, tmp_path, monkeypatch, case_type):
    """A draft saved on the export page restores there, and 上一步 walks
    evidence -> case facts -> parties -> case type -> welcome, then stops."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    path = _navigate_and_save(wizard, draft, tmp_path, monkeypatch, case_type, 5)
    assert wizard.currentId() == wizard.PAGE_EXPORT
    before = _session_snapshot(wizard, case_type)

    restored = _open_draft_file(draft, path, monkeypatch)
    route = _route_ids(restored, case_type)
    claim_id = route[3]
    assert restored.currentId() == wizard.PAGE_EXPORT
    assert restored.visitedIds() == route
    assert restored.button(QWizard.BackButton).isEnabled()

    # Repeated Back: export -> evidence -> facts -> parties -> type -> welcome.
    destinations = _back_destinations(restored, qapp)
    assert destinations == [restored.PAGE_EXPORT, restored.PAGE_EVIDENCE, claim_id,
                            restored.PAGE_PARTY, restored.PAGE_CASE_SELECTION,
                            restored.PAGE_WELCOME]
    assert not restored.button(QWizard.BackButton).isEnabled()

    # Forward replay rebuilds the same route through real validation.
    landed = _forward_replay(restored, qapp, 5)
    assert landed == route[1:]
    assert restored.currentId() == restored.PAGE_EXPORT

    # No unrelated claim page was ever visited, and nothing was lost.
    assert claim_id in restored.visitedIds()
    other_claims = {3, 4, 5, 6, 7} - {claim_id}
    assert not (set(restored.visitedIds()) & other_claims)
    assert _session_snapshot(restored, case_type) == before


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_resume_back_reaches_the_case_facts(qapp, tmp_path, monkeypatch, case_type):
    """A draft saved on the evidence page resumes there; Back lands on the
    case's own facts page, then parties, then case type."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    path = _navigate_and_save(wizard, draft, tmp_path, monkeypatch, case_type, 4)
    assert wizard.currentId() == wizard.PAGE_EVIDENCE

    restored = _open_draft_file(draft, path, monkeypatch)
    route = _route_ids(restored, case_type)[:5]
    assert restored.currentId() == restored.PAGE_EVIDENCE
    assert restored.visitedIds() == route

    destinations = _back_destinations(restored, qapp)
    assert destinations[1] == getattr(restored, CLAIM_PAGE_ID[case_type])
    assert destinations[-2] == restored.PAGE_CASE_SELECTION
    assert destinations[-1] == restored.PAGE_WELCOME

    # Forward again: facts page validation still passes, evidence unchanged.
    landed = _forward_replay(restored, qapp, 4)
    assert landed == route[1:]
    assert _session_snapshot(restored, case_type) == _session_snapshot(
        wizard, case_type
    )


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_claim_resume_back_leads_to_parties(qapp, tmp_path, monkeypatch, case_type):
    """A draft saved on a case-facts page resumes there; Back lands on the
    party page and never on the evidence or export pages."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    path = _navigate_and_save(wizard, draft, tmp_path, monkeypatch, case_type, 3)
    assert wizard.currentId() == getattr(wizard, CLAIM_PAGE_ID[case_type])

    restored = _open_draft_file(draft, path, monkeypatch)
    claim_id = getattr(restored, CLAIM_PAGE_ID[case_type])
    assert restored.currentId() == claim_id
    assert restored.visitedIds() == [restored.PAGE_WELCOME, restored.PAGE_CASE_SELECTION,
                                     restored.PAGE_PARTY, claim_id]

    destinations = _back_destinations(restored, qapp)
    assert destinations == [claim_id, restored.PAGE_PARTY,
                            restored.PAGE_CASE_SELECTION, restored.PAGE_WELCOME]
    assert restored.PAGE_EVIDENCE not in restored.visitedIds()
    assert restored.PAGE_EXPORT not in restored.visitedIds()


def test_case_selection_resume_back_leads_to_welcome(qapp, tmp_path, monkeypatch):
    """A draft saved while still standing on the case-type page resumes there,
    and Back reaches the welcome page exactly once."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    qapp.processEvents()
    wizard.next()  # welcome -> case selection
    select_case(wizard, "loan")
    path = _save_draft_file(wizard, draft, tmp_path, monkeypatch)

    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_CASE_SELECTION
    assert restored.visitedIds() == [restored.PAGE_WELCOME, restored.PAGE_CASE_SELECTION]
    assert restored.field("case_type") == "loan"

    destinations = _back_destinations(restored, qapp)
    assert destinations == [restored.PAGE_CASE_SELECTION, restored.PAGE_WELCOME]
    assert not restored.button(QWizard.BackButton).isEnabled()


def test_incomplete_party_draft_resumes_on_party_and_back_leads_to_case_selection(
    qapp, tmp_path, monkeypatch
):
    """A draft saved on the party page with blank parties must not pretend the
    case passed party validation: it resumes on 当事人, and Back leads to
    选择案件类型, not to an unrelated page."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    qapp.processEvents()
    wizard.next()  # welcome -> case selection
    select_case(wizard, "loan")
    wizard.next()  # -> party (cards still blank)
    path = _save_draft_file(wizard, draft, tmp_path, monkeypatch)
    assert not wizard.party_page.isComplete()

    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_PARTY
    assert not restored.party_page.isComplete()
    # Forward is blocked by real validation while the parties stay blank.
    assert not restored.button(QWizard.NextButton).isEnabled()
    assert restored.visitedIds() == [restored.PAGE_WELCOME,
                                     restored.PAGE_CASE_SELECTION,
                                     restored.PAGE_PARTY]

    destinations = _back_destinations(restored, qapp)
    assert destinations == [restored.PAGE_PARTY, restored.PAGE_CASE_SELECTION,
                            restored.PAGE_WELCOME]


def _save_synthetic(wizard, tmp_path, resume_page, name="回退草稿.cfdraft"):
    """Save a draft whose recorded resume page names a page the live wizard
    never reached - the only way to exercise the resume-page fallback rules.
    The party page is initialised first so the capture matches the card state
    the real UI would hold (one blank card per side)."""
    wizard.party_page.initializePage()
    document = schema.validate_document(capture_draft(wizard, resume_page))
    path = tmp_path / name
    save_draft(str(path), document)
    return path


def test_export_draft_with_incomplete_parties_falls_back_and_back_leads_to_case_selection(
    qapp, tmp_path, monkeypatch
):
    """An export-page draft whose parties are blank falls back to 当事人;
    Back from the fallback page must lead to 选择案件类型."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    select_case(wizard, "loan")  # parties deliberately left blank
    path = _save_synthetic(wizard, tmp_path, "export")

    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_PARTY
    assert restored.visitedIds() == [restored.PAGE_WELCOME,
                                     restored.PAGE_CASE_SELECTION,
                                     restored.PAGE_PARTY]

    destinations = _back_destinations(restored, qapp)
    assert destinations == [restored.PAGE_PARTY, restored.PAGE_CASE_SELECTION,
                            restored.PAGE_WELCOME]


def test_evidence_draft_with_incomplete_case_facts_falls_back_and_back_leads_to_parties(
    qapp, tmp_path, monkeypatch
):
    """An evidence-page draft whose facts page is blank falls back to the
    case's facts page; Back from there leads to the party page."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    select_case(wizard, "contract")
    set_parties(wizard)  # parties complete, case facts left blank
    path = _save_synthetic(wizard, tmp_path, "evidence")

    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_CONTRACT_CLAIM
    assert restored.PAGE_EVIDENCE not in restored.visitedIds()

    destinations = _back_destinations(restored, qapp)
    assert destinations == [restored.PAGE_CONTRACT_CLAIM, restored.PAGE_PARTY,
                            restored.PAGE_CASE_SELECTION, restored.PAGE_WELCOME]


def test_explicitly_cleared_evidence_stays_empty_through_restore_navigation(
    qapp, tmp_path, monkeypatch
):
    """Deleting every suggested evidence row, saving and reopening must not
    resurrect suggestions - not even after walking Back and Forward again."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")  # loads the loan suggestion rows
    wizard.evidence_page.clear_all_rows()
    qapp.processEvents()
    assert _evidence_snapshot(wizard) == [[] for _ in range(wizard.evidence_page.table.rowCount())]

    wizard.restart()
    for _ in range(4):
        wizard.next()  # -> evidence page
    path = _save_draft_file(wizard, draft, tmp_path, monkeypatch, name="清空证据草稿.cfdraft")
    assert wizard.currentId() == wizard.PAGE_EVIDENCE

    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_EVIDENCE
    assert _evidence_snapshot(restored) == _evidence_snapshot(wizard)

    back_button = restored.button(QWizard.BackButton)
    back_button.click()  # evidence -> loan facts
    qapp.processEvents()
    assert restored.currentId() == restored.PAGE_LOAN_CLAIM
    restored.button(QWizard.NextButton).click()  # facts -> evidence again
    qapp.processEvents()
    assert restored.currentId() == restored.PAGE_EVIDENCE
    assert restored.evidence_page.table.rowCount() == wizard.evidence_page.table.rowCount()
    for row in range(restored.evidence_page.table.rowCount()):
        for column in range(restored.evidence_page.table.columnCount()):
            item = restored.evidence_page.table.item(row, column)
            assert item is None or not item.text().strip()


def test_multi_party_and_company_data_survive_back_forward_traversal(
    qapp, tmp_path, monkeypatch
):
    """Two plaintiffs and a company defendant keep their values, checkbox state
    and order across a full restore, Back-to-welcome and Forward-to-export."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")
    set_parties(
        wizard,
        plaintiffs=[
            {"name": "原告甲（测试）", "id_number": "示例证件号-甲", "address": "示例地址一",
             "phone": "13800000001"},
            {"name": "原告乙公司（测试）", "is_company": True, "credit_code": "示例统一社会信用代码",
             "legal_rep": "示例法定代表人"},
        ],
        defendants=[
            {"name": "被告丙公司（测试）", "is_company": True, "credit_code": "示例代码-丙",
             "legal_rep": "示例负责人"},
        ],
    )
    before = _session_snapshot(wizard, "loan")

    path = _navigate_and_save(wizard, draft, tmp_path, monkeypatch, "loan", 5, prepare=False)
    restored = _open_draft_file(draft, path, monkeypatch)
    _back_destinations(restored, qapp)  # walk all the way to welcome
    landed = _forward_replay(restored, qapp, 5)
    assert landed[-1] == restored.PAGE_EXPORT
    assert _session_snapshot(restored, "loan") == before


def test_unconfirmed_tri_state_survives_restore_navigation(qapp, tmp_path, monkeypatch):
    """A None ("未确认") factual confirmation is a value: it must survive the
    restore and a Back/Forward cycle without silently becoming True/False."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)

    prepare_case(wizard, "loan", confirm_flags=False)
    assert wizard.loan_claim_page.get_has_iou() is None
    before = _session_snapshot(wizard, "loan")
    assert before["flags"] == {"has_iou": None}

    path = _navigate_and_save(wizard, draft, tmp_path, monkeypatch, "loan", 3, prepare=False)
    restored = _open_draft_file(draft, path, monkeypatch)
    assert restored.currentId() == restored.PAGE_LOAN_CLAIM
    assert restored.loan_claim_page.get_has_iou() is None

    back_button = restored.button(QWizard.BackButton)
    back_button.click()
    qapp.processEvents()
    restored.button(QWizard.NextButton).click()
    qapp.processEvents()
    assert restored.loan_claim_page.get_has_iou() is None
    assert _session_snapshot(restored, "loan") == before
