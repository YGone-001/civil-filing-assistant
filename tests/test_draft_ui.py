# File: tests/test_draft_ui.py
# Purpose: Save/open actions, confirmations, cancellation and session safety.
# Encoding: UTF-8
"""UI-level acceptance for the two draft actions.

Everything here drives the real ``DraftPresenter`` against a real wizard; only
the modal dialogs are stubbed (as everywhere else in this suite). The tests
focus on the promises a user relies on:

* nothing is written without an explicit confirmation and a chosen path;
* a cancelled or failed action leaves both the session and any existing draft
  file untouched;
* opening a draft replaces the wizard only after the whole payload validated,
  and the replacement keeps working (Finish still exports).
"""

import os

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWizard

from drafts import save_draft, schema, validate_document
from drafts.errors import ProtectionUnavailable
from helpers import make_wizard, prepare_case, navigate_to_export, select_case, set_parties
from presenters.draft_presenter import DraftPresenter
from views.draft_io import capture_draft, claim_page
from views.theme import SECONDARY_BUTTON

SECRET_NAME = "机密姓名测试甲"


class _UnavailableProtector:
    """Simulates a machine where Windows user-scoped protection is unusable."""

    def protect(self, data):
        raise ProtectionUnavailable("当前环境不支持 Windows 用户级数据保护。")

    def unprotect(self, blob):
        raise ProtectionUnavailable("当前环境不支持 Windows 用户级数据保护。")


def _save_dialog_to(monkeypatch, path):
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: (path, ""))
    )


def _open_dialog_to(monkeypatch, path):
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: (path, ""))
    )


def _answer_questions(monkeypatch, answer, recorded=None):
    """Answer every question with *answer*, optionally recording it.

    ``recorded`` is the ``dialog_recorder`` list: installing this stub replaces
    the fixture's fake, so a test that inspects the questions must pass the
    recorder here.
    """

    def _fake(parent, title, text, buttons=None, default=None):
        if recorded is not None:
            recorded.append(
                {
                    "kind": "question",
                    "args": (parent, title, text, buttons, default),
                    "kwargs": {},
                }
            )
        return answer

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))


def _dialog_texts(recorded):
    """Every string a dialog showed (title and body), for leak assertions."""
    texts = []
    for call in recorded:
        for argument in call["args"][1:]:
            if isinstance(argument, str):
                texts.append(argument)
    return texts


def _draft_files(directory):
    return [name for name in os.listdir(directory) if name.endswith(".cfdraft")]


def _make(tmp_path, monkeypatch, case_type="loan", fill=True, protector=None):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter, protector=protector)
    wizard.show()
    if fill:
        prepare_case(wizard, case_type)
        wizard.setCurrentId(getattr(wizard, {
            "loan": "PAGE_LOAN_CLAIM",
            "contract": "PAGE_CONTRACT_CLAIM",
            "property": "PAGE_PROPERTY_CLAIM",
            "labor": "PAGE_LABOR_CLAIM",
            "divorce": "PAGE_DIVORCE_CLAIM",
        }[case_type]))
    return wizard, presenter, draft


# --------------------------------------------------------------------------- #
# Discoverability
# --------------------------------------------------------------------------- #


def test_wizard_exposes_the_two_draft_actions(qapp):
    wizard, _ = make_wizard()
    assert wizard.save_draft_button.text() == "保存草稿"
    assert wizard.open_draft_button.text() == "打开草稿"
    assert wizard.save_draft_button.objectName() == SECONDARY_BUTTON
    assert wizard.open_draft_button.objectName() == SECONDARY_BUTTON


def test_every_page_carries_a_draft_action_bar(qapp):
    """Both actions must be reachable from every step of the wizard."""
    wizard, _ = make_wizard()
    pages = (
        wizard.welcome_page,
        wizard.case_selection_page,
        wizard.party_page,
        wizard.loan_claim_page,
        wizard.contract_claim_page,
        wizard.property_claim_page,
        wizard.labor_claim_page,
        wizard.divorce_claim_page,
        wizard.evidence_page,
        wizard.export_page,
    )
    assert len(wizard._draft_bars) == len(pages)
    for page, bar in wizard._draft_bars:
        assert bar.save_button.text() == "保存草稿"
        assert bar.open_button.text() == "打开草稿"
        assert bar.parent() is page or page.isAncestorOf(bar)


def test_draft_actions_reach_the_presenter_from_every_page(qapp):
    """Clicking the bar on a page emits the wizard-level request signals."""
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    calls = []
    wizard.save_draft_requested.connect(lambda: calls.append("save"))
    wizard.open_draft_requested.connect(lambda: calls.append("open"))

    for _page, bar in wizard._draft_bars:
        bar.save_button.click()
        bar.open_button.click()

    assert calls.count("save") == len(wizard._draft_bars)
    assert calls.count("open") == len(wizard._draft_bars)
    assert draft.wizard is wizard


def test_draft_actions_have_accessible_names(qapp):
    wizard, _ = make_wizard()
    assert wizard.save_draft_button.accessibleName() == "保存草稿"
    assert wizard.open_draft_button.accessibleName() == "打开草稿"
    assert wizard.save_draft_button.accessibleDescription()
    assert wizard.open_draft_button.accessibleDescription()


def test_draft_actions_are_visible_on_the_first_and_last_page(qapp):
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()
    for page_id in (wizard.PAGE_WELCOME, wizard.PAGE_EXPORT):
        wizard.setCurrentId(page_id)
        qapp.processEvents()
        assert wizard.save_draft_button.isVisible()
        assert wizard.open_draft_button.isVisible()


def test_standard_navigation_buttons_are_unchanged(qapp):
    wizard, _ = make_wizard()
    assert wizard.button(QWizard.BackButton).text() == "上一步"
    assert wizard.button(QWizard.NextButton).text() == "下一步"
    assert wizard.button(QWizard.FinishButton).text() == "生成三份 Word 初稿"
    assert wizard.button(QWizard.CancelButton).text() == "退出"


def test_default_suggested_filename_is_neutral(qapp):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    path = draft._default_file_path()
    assert path.endswith(".cfdraft")
    for card in wizard.party_page.plaintiff_widgets + wizard.party_page.defendant_widgets:
        name = card["name"].text()
        if name:
            assert name not in os.path.basename(path)


# --------------------------------------------------------------------------- #
# Saving
# --------------------------------------------------------------------------- #


def test_save_draft_writes_an_encrypted_file(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, _, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))

    assert draft.save_draft() is True

    raw = target.read_bytes()
    assert raw[:8] == b"CFADRAFT"
    assert "原告甲（测试）".encode("utf-8") not in raw
    assert b"loan_date" not in raw
    assert any("草稿已保存" in text for text in _dialog_texts(dialog_recorder))


def test_save_draft_confirms_sensitive_content_first(qapp, tmp_path, monkeypatch, dialog_recorder):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    _save_dialog_to(monkeypatch, str(tmp_path / "case.cfdraft"))

    draft.save_draft()

    first_question = next(c for c in dialog_recorder if c["kind"] == "question")
    text = first_question["args"][2]
    assert "敏感信息" in text
    assert "Windows" in text
    assert "账户" in text


def test_cancelled_confirmation_writes_nothing(qapp, tmp_path, monkeypatch):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    _save_dialog_to(monkeypatch, str(tmp_path / "case.cfdraft"))
    _answer_questions(monkeypatch, QMessageBox.No)

    assert draft.save_draft() is False
    assert _draft_files(str(tmp_path)) == []


def test_cancelled_file_dialog_writes_nothing(qapp, tmp_path, monkeypatch):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    # conftest already stubs the dialogs to "cancelled".
    assert draft.save_draft() is False
    assert _draft_files(str(tmp_path)) == []


def test_missing_extension_is_added(qapp, tmp_path, monkeypatch):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    _save_dialog_to(monkeypatch, str(tmp_path / "case"))

    assert draft.save_draft() is True
    assert (tmp_path / "case.cfdraft").exists()


def test_overwrite_requires_confirmation_and_declining_preserves_the_file(
    qapp, tmp_path, monkeypatch
):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True
    before = target.read_bytes()

    _answer_questions(monkeypatch, QMessageBox.No)
    assert draft.save_draft() is False
    assert target.read_bytes() == before


def test_overwrite_after_confirmation_replaces_the_file(qapp, tmp_path, monkeypatch):
    wizard, _, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True
    before = target.read_bytes()

    wizard.loan_claim_page.principal.setText("77777")
    _answer_questions(monkeypatch, QMessageBox.Yes)
    assert draft.save_draft() is True
    assert target.read_bytes() != before


def test_save_failure_reports_and_keeps_the_session(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, _, draft = _make(tmp_path, monkeypatch, protector=_UnavailableProtector())
    _save_dialog_to(monkeypatch, str(tmp_path / "case.cfdraft"))

    assert draft.save_draft() is False
    assert _draft_files(str(tmp_path)) == []
    assert wizard.loan_claim_page.principal.text() == "50000"
    assert any("保存草稿失败" in text for text in _dialog_texts(dialog_recorder))


def test_save_without_a_case_type_warns_and_writes_nothing(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    original_field = wizard.field
    monkeypatch.setattr(
        wizard,
        "field",
        lambda name: "" if name == "case_type" else original_field(name),
    )
    _save_dialog_to(monkeypatch, str(tmp_path / "case.cfdraft"))

    assert draft.save_draft() is False
    assert _draft_files(str(tmp_path)) == []
    assert any("案件类型" in text for text in _dialog_texts(dialog_recorder))


def test_no_draft_is_written_without_user_action(qapp, tmp_path, monkeypatch):
    wizard, _, _draft = _make(tmp_path, monkeypatch)
    wizard.close()
    qapp.processEvents()
    assert _draft_files(str(tmp_path)) == []


# --------------------------------------------------------------------------- #
# Opening
# --------------------------------------------------------------------------- #


def test_open_draft_restores_into_a_new_wizard(qapp, tmp_path, monkeypatch):
    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True

    wizard.loan_claim_page.principal.setText("99999")
    _open_dialog_to(monkeypatch, str(target))
    assert draft.open_draft() is True

    assert draft.wizard is not wizard
    assert draft.wizard.loan_claim_page.principal.text() == "50000"
    assert presenter.view is draft.wizard
    assert draft.wizard.finish_handler is not None


def test_opened_wizard_keeps_a_working_finish_flow(qapp, tmp_path, monkeypatch, dialog_recorder):
    desktop = tmp_path / "home" / "Desktop"
    (tmp_path / "home").mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(tmp_path / "home"))

    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True

    _open_dialog_to(monkeypatch, str(target))
    assert draft.open_draft() is True

    finish = navigate_to_export(draft.wizard)
    finish.click()
    qapp.processEvents()

    assert len(sorted(desktop.rglob("*.docx"))) == 3


def test_cancelled_open_changes_nothing(qapp, tmp_path, monkeypatch):
    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    assert draft.open_draft() is False
    assert draft.wizard is wizard
    assert presenter.view is wizard


def test_failed_open_preserves_the_current_session(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    broken = tmp_path / "broken.cfdraft"
    broken.write_bytes(b"CFADRAFT\x01\x00\x00\x00\x20" + b"\x00" * 16)
    _open_dialog_to(monkeypatch, str(broken))

    assert draft.open_draft() is False
    assert draft.wizard is wizard
    assert presenter.view is wizard
    assert wizard.loan_claim_page.principal.text() == "50000"
    assert wizard.party_page.plaintiff_widgets[0]["name"].text() == "原告甲（测试）"
    assert any("无法打开草稿" in text for text in _dialog_texts(dialog_recorder))


def test_open_of_a_non_draft_file_is_rejected(qapp, tmp_path, monkeypatch):
    wizard, _, draft = _make(tmp_path, monkeypatch)
    foreign = tmp_path / "notes.txt"
    foreign.write_text("这是一份普通文本文件", encoding="utf-8")
    _open_dialog_to(monkeypatch, str(foreign))

    assert draft.open_draft() is False
    assert draft.wizard is wizard


def test_declining_session_replacement_keeps_the_current_case(qapp, tmp_path, monkeypatch):
    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True

    wizard.loan_claim_page.principal.setText("12345")
    _open_dialog_to(monkeypatch, str(target))
    _answer_questions(monkeypatch, QMessageBox.No)

    assert draft.open_draft() is False
    assert draft.wizard is wizard
    assert wizard.loan_claim_page.principal.text() == "12345"


def test_open_asks_before_discarding_an_unsaved_session(qapp, tmp_path, monkeypatch, dialog_recorder):
    _wizard, _, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True

    _open_dialog_to(monkeypatch, str(target))
    assert draft.open_draft() is True

    titles = [call["args"][1] for call in dialog_recorder if call["kind"] == "question"]
    assert "替换当前内容" in titles


def test_empty_session_opens_without_a_replacement_prompt(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, presenter, draft = _make(tmp_path, monkeypatch)
    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    assert draft.save_draft() is True

    # A brand-new wizard holds no user input, so no replacement prompt appears.
    fresh, fresh_presenter = make_wizard()
    fresh_draft = DraftPresenter(fresh, fresh_presenter)
    _open_dialog_to(monkeypatch, str(target))
    assert fresh_draft.open_draft() is True

    titles = [call["args"][1] for call in dialog_recorder if call["kind"] == "question"]
    assert "替换当前内容" not in titles


# --------------------------------------------------------------------------- #
# Privacy of the dialogs themselves
# --------------------------------------------------------------------------- #


def test_dialog_text_never_contains_case_data(qapp, tmp_path, monkeypatch, dialog_recorder):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    select_case(wizard, "loan")
    set_parties(
        wizard,
        plaintiffs=[{"name": SECRET_NAME, "id_number": "示例-机密", "address": "机密地址", "phone": "13800000009"}],
    )

    target = tmp_path / "case.cfdraft"
    _save_dialog_to(monkeypatch, str(target))
    draft.save_draft()

    broken = tmp_path / "broken.cfdraft"
    broken.write_bytes(b"not a draft")
    _open_dialog_to(monkeypatch, str(broken))
    draft.open_draft()

    joined = "\n".join(_dialog_texts(dialog_recorder))
    assert SECRET_NAME not in joined
    assert "示例-机密" not in joined
    assert "机密地址" not in joined


# --------------------------------------------------------------------------- #
# C-08 — a meaningful current session must never be replaced silently
# --------------------------------------------------------------------------- #
#
# These tests drive the real Open Draft action against a real wizard and answer
# the replacement confirmation with QMessageBox.No. They deliberately do not
# call the detection helper directly: the defect was that the *user-visible*
# guard never appeared, so only the end-to-end path can prove the fix.


def _draft_on_disk(path, case_type="divorce"):
    """Write a valid encrypted draft of another case to *path*."""
    source, _ = make_wizard()
    prepare_case(source, case_type)
    save_draft(str(path), validate_document(capture_draft(source, "party")))
    return path


def _read_text(widget):
    return widget.toPlainText() if hasattr(widget, "toPlainText") else widget.text()


def _wizard_snapshot(wizard):
    """Everything a replacement would discard, as one comparable value."""
    case_type = wizard.field("case_type")
    page = claim_page(wizard, case_type)
    snapshot = {
        "current_id": wizard.currentId(),
        "case_type": case_type,
        "fields": {
            spec.key: _read_text(getattr(page, spec.widget))
            for spec in schema.TEXT_FIELDS[case_type]
        },
        "parties": wizard.party_page.get_party_data(),
        "party_titles": [
            card["group"].title()
            for card in wizard.party_page.plaintiff_widgets
            + wizard.party_page.defendant_widgets
        ],
        "evidence": wizard.evidence_page.snapshot_evidence(case_type),
        "evidence_states": dict(wizard.evidence_page._case_state),
    }
    if case_type == "loan":
        snapshot["flags"] = {"has_iou": wizard.loan_claim_page.get_has_iou()}
    elif case_type == "contract":
        snapshot["flags"] = dict(wizard.contract_claim_page.get_flags())
    elif case_type == "labor":
        snapshot["flags"] = {
            "is_no_contract": wizard.labor_claim_page.get_has_no_contract()
        }
    else:
        snapshot["flags"] = {}
    return snapshot


def _decline_open(qapp, tmp_path, monkeypatch, dialog_recorder, prepare):
    """Prepare one edit, choose Open Draft, and answer the prompt with No."""
    target = _draft_on_disk(tmp_path / "other.cfdraft")
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    qapp.processEvents()

    prepare(wizard)
    qapp.processEvents()
    before = _wizard_snapshot(wizard)

    _open_dialog_to(monkeypatch, str(target))
    _answer_questions(monkeypatch, QMessageBox.No, dialog_recorder)
    dialog_recorder.clear()

    result = draft.open_draft()

    questions = [call for call in dialog_recorder if call["kind"] == "question"]
    titles = [call["args"][1] for call in questions]
    assert "替换当前内容" in titles, (
        "opening a draft over a session with user input must ask for confirmation"
    )
    assert questions[0]["args"][4] == QMessageBox.StandardButton.No, (
        "the replacement confirmation must default to No"
    )
    assert result is False
    assert draft.wizard is wizard
    assert presenter.view is wizard
    assert _wizard_snapshot(wizard) == before
    return wizard, draft


def _init_party_page(wizard, case_type="loan"):
    select_case(wizard, case_type)
    wizard.party_page.initializePage()


def _add_blank_party_card(wizard):
    _init_party_page(wizard)
    wizard.party_page.add_party_ui(0)


def _set_party_field(wizard, key, value):
    _init_party_page(wizard)
    wizard.party_page.plaintiff_widgets[0][key].setText(value)


def _mark_party_as_company(wizard):
    _init_party_page(wizard)
    wizard.party_page.plaintiff_widgets[0]["is_company"].setChecked(True)


def _select_loan_iou(wizard, value):
    select_case(wizard, "loan")
    if value is True:
        wizard.loan_claim_page.iou_yes.setChecked(True)
    else:
        wizard.loan_claim_page.iou_no.setChecked(True)


def _confirm_contract_delivery(wizard):
    select_case(wizard, "contract")
    wizard.contract_claim_page.del_yes.setChecked(True)


def _deny_contract_receipt(wizard):
    select_case(wizard, "contract")
    wizard.contract_claim_page.sign_no.setChecked(True)


def _edit_lpr(wizard):
    select_case(wizard, "contract")
    wizard.contract_claim_page.lpr_value.setText("3.5")


def _edit_lpr_multiple(wizard):
    select_case(wizard, "contract")
    wizard.contract_claim_page.lpr_multiple.setText("3")


def _select_labor_no_contract(wizard):
    select_case(wizard, "labor")
    wizard.labor_claim_page.no_contract_yes.setChecked(True)


def _edit_evidence(wizard):
    select_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    wizard.evidence_page.table.item(0, 0).setText("修改后的借条（测试）")


def _clear_evidence(wizard):
    select_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    wizard.evidence_page.table.selectAll()
    wizard.evidence_page.remove_selected_rows()


def _modify_evidence_then_switch_category(wizard):
    select_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    wizard.evidence_page.add_row("补充证据（测试）", "证明目的（测试）", auto_edit=False)
    select_case(wizard, "divorce")
    wizard.evidence_page.initializePage()


@pytest.mark.parametrize(
    "prepare,label",
    [
        (lambda w: _set_party_field(w, "id", "示例证件号-无姓名"), "party id only"),
        (lambda w: _set_party_field(w, "addr", "示例地址-无姓名"), "party address only"),
        (lambda w: _set_party_field(w, "phone", "13800000000"), "party phone only"),
        (lambda w: _set_party_field(w, "credit_code", "91310000MA1FL0TEST"), "credit code only"),
        (lambda w: _set_party_field(w, "legal_rep", "赵六"), "legal representative only"),
        (_mark_party_as_company, "company toggle"),
        (_add_blank_party_card, "extra blank card"),
        (lambda w: _select_loan_iou(w, True), "loan iou true"),
        (lambda w: _select_loan_iou(w, False), "loan iou false"),
        (_confirm_contract_delivery, "contract delivery confirmed"),
        (_deny_contract_receipt, "contract receipt denied"),
        (_edit_lpr, "lpr edited"),
        (_edit_lpr_multiple, "lpr multiplier edited"),
        (_select_labor_no_contract, "labor contract flag"),
        (_edit_evidence, "evidence edited"),
        (_clear_evidence, "evidence cleared"),
        (_modify_evidence_then_switch_category, "evidence from another category"),
    ],
)
def test_meaningful_session_is_protected_before_opening_a_draft(
    qapp, tmp_path, monkeypatch, dialog_recorder, prepare, label
):
    """C-08: every editable state must trigger the replacement confirmation."""
    _decline_open(qapp, tmp_path, monkeypatch, dialog_recorder, prepare)


def test_pristine_session_opens_without_a_replacement_prompt(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    """A brand-new wizard holds nothing worth protecting."""
    target = _draft_on_disk(tmp_path / "other.cfdraft")
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    qapp.processEvents()

    _open_dialog_to(monkeypatch, str(target))
    _answer_questions(monkeypatch, QMessageBox.No, dialog_recorder)
    dialog_recorder.clear()

    assert draft.open_draft() is True
    titles = [call["args"][1] for call in dialog_recorder if call["kind"] == "question"]
    assert "替换当前内容" not in titles
    assert draft.wizard is not wizard


def test_untouched_contract_defaults_do_not_trigger_a_replacement_prompt(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    """The LPR reference value and multiplier are defaults, not user input."""
    target = _draft_on_disk(tmp_path / "other.cfdraft")
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()
    select_case(wizard, "contract")
    qapp.processEvents()

    _open_dialog_to(monkeypatch, str(target))
    _answer_questions(monkeypatch, QMessageBox.No, dialog_recorder)
    dialog_recorder.clear()

    assert draft.open_draft() is True
    titles = [call["args"][1] for call in dialog_recorder if call["kind"] == "question"]
    assert "替换当前内容" not in titles


def test_replacement_confirmation_wording_does_not_claim_the_session_is_unsaved(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    """The dialog must not assert something the app cannot know."""
    _decline_open(
        qapp, tmp_path, monkeypatch, dialog_recorder,
        lambda w: _set_party_field(w, "phone", "13800000000"),
    )
    question = next(call for call in dialog_recorder if call["kind"] == "question")
    body = question["args"][2]
    assert "已填写或已修改" in body
    assert "请先保存草稿" in body
    assert "尚未保存" not in body


def test_declining_a_replacement_writes_no_file(qapp, tmp_path, monkeypatch, dialog_recorder):
    """Open Draft must never write, save or create a draft of its own."""
    _decline_open(
        qapp, tmp_path, monkeypatch, dialog_recorder,
        lambda w: _set_party_field(w, "id", "示例证件号-无姓名"),
    )
    # The only file present is the draft the test wrote before opening.
    assert sorted(os.listdir(tmp_path)) == ["other.cfdraft"]


def test_opening_a_draft_installs_exactly_one_save_handler(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    """The window swap must not stack duplicate signal connections."""
    target = _draft_on_disk(tmp_path / "other.cfdraft")
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    wizard.show()

    _open_dialog_to(monkeypatch, str(target))
    _answer_questions(monkeypatch, QMessageBox.Yes, dialog_recorder)
    assert draft.open_draft() is True

    reopened = draft.wizard
    assert reopened is not wizard
    _save_dialog_to(monkeypatch, str(tmp_path / "after-open.cfdraft"))
    dialog_recorder.clear()
    draft.save_draft()

    titles = [call["args"][1] for call in dialog_recorder if call["kind"] == "question"]
    assert titles.count("保存草稿") == 1
