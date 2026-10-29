# File: tests/test_evidence_state.py
# Purpose: Evidence-page state machine and cross-category isolation (P1-03 / D-03).
# Encoding: UTF-8
"""Regression coverage for deterministic evidence initialization.

The evidence page used to reload suggestions whenever the table happened to be
empty (resurrecting deliberately deleted rows) and kept stale rows across case
category switches. It now tracks per-category state, stashes rows when the
category changes, and marks suggested rows with item data instead of a bare
row index. All data is fictional.
"""

import os

from helpers import docx_all_text, make_wizard, prepare_case, select_case, set_parties

EXPECTED_SUGGESTIONS = {
    "loan": ("借条/借款协议", "银行转账凭证/现金收据", "催款聊天记录/通话录音/催告函"),
    "divorce": ("结婚证/户口本", "出生医学证明", "财产凭证（产证/存折）", "收入证明/银行流水"),
}


def _init(wizard, case_type):
    select_case(wizard, case_type)
    page = wizard.evidence_page
    page.initializePage()
    return page


def _names(page):
    return [page.table.item(r, 0).text() for r in range(page.table.rowCount())]


def _delete_all(page, dialog_recorder):
    dialog_recorder.clear()
    page.table.selectAll()
    page.remove_selected_rows()
    assert page.table.rowCount() == 0


def test_first_visit_loads_category_suggestions(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")

    assert tuple(_names(page)) == EXPECTED_SUGGESTIONS["loan"]
    assert page._suggested_count == len(EXPECTED_SUGGESTIONS["loan"])
    assert page.get_case_state() == page.INITIALIZED_WITH_SUGGESTIONS


def test_same_case_reentry_preserves_user_rows(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    page.add_row("用户补充证据（测试）", "证明目的（测试）", auto_edit=False)

    page.initializePage()  # navigate away and back within the same category

    assert "用户补充证据（测试）" in _names(page)
    assert page.get_case_state() == page.USER_MODIFIED


def test_delete_all_stays_empty_across_reentry(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    _delete_all(page, dialog_recorder)
    assert page.get_case_state() == page.USER_EXPLICITLY_CLEARED

    page.initializePage()  # re-entry must not resurrect deleted suggestions

    assert page.table.rowCount() == 0
    assert page.get_evidence_items() == []
    assert page.get_case_state() == page.USER_EXPLICITLY_CLEARED


def test_editing_a_suggestion_is_preserved(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    page.table.item(0, 0).setText("修改后的借条（测试）")

    assert page.get_case_state() == page.USER_MODIFIED
    page.initializePage()
    assert _names(page)[0] == "修改后的借条（测试）"


def test_case_switch_does_not_leak_suggestions_across_categories(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    assert "借条/借款协议" in _names(page)

    page2 = _init(wizard, "divorce")

    assert tuple(_names(page2)) == EXPECTED_SUGGESTIONS["divorce"]
    assert not any("借条" in name for name in _names(page2))
    assert page2._suggested_count == len(EXPECTED_SUGGESTIONS["divorce"])


def test_switching_back_restores_previous_category_edits(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    page.add_row("用户补充证据（测试）", "证明目的（测试）", auto_edit=False)
    loan_rows = _names(page)

    _init(wizard, "divorce")
    assert "用户补充证据（测试）" not in _names(page)
    _init(wizard, "loan")

    assert _names(page) == loan_rows
    assert page.get_case_state() == page.USER_MODIFIED


def test_multi_category_switching_is_deterministic(qapp):
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")
    page.add_row("借贷专用补充（测试）", "", auto_edit=False)

    for case_type in ("contract", "labor", "divorce", "property", "loan"):
        _init(wizard, case_type)

    names = _names(page)
    assert tuple(names[:3]) == EXPECTED_SUGGESTIONS["loan"]
    assert "借贷专用补充（测试）" in names
    assert page._suggested_count == len(EXPECTED_SUGGESTIONS["loan"])


def test_suggested_identity_survives_arbitrary_deletions(qapp):
    """Row index alone must not decide suggested status after deletions."""
    wizard, _ = make_wizard()
    page = _init(wizard, "loan")

    page.table.selectRow(0)
    page.remove_selected_rows()  # delete the first suggested row (confirmed)
    assert page._suggested_count == 2

    page.add_row("用户证据（测试）", "", auto_edit=False)
    assert page._suggested_count == 2
    # The remaining suggested rows keep their tint; the user row does not.
    assert page._is_suggested_row(0) and page._is_suggested_row(1)
    assert not page._is_suggested_row(2)

    page.table.selectRow(1)
    page.remove_selected_rows()
    assert page._suggested_count == 1
    assert not page._is_suggested_row(1)


def test_intentionally_empty_evidence_list_exports_empty(qapp, monkeypatch, tmp_path, dialog_recorder):
    """The evidence list document must reflect a deliberate empty selection."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan")
    _delete_all(wizard.evidence_page, dialog_recorder)

    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    assert len(docs) == 3
    evidence = next(d for d in docs if "证据清单" in d.name)
    text = docx_all_text(evidence)
    assert "证据名称" in text  # header intact
    for suggested in EXPECTED_SUGGESTIONS["loan"]:
        assert suggested not in text, f"deleted suggestion {suggested!r} reappeared"
