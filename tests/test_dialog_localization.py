# File: tests/test_dialog_localization.py
# Purpose: Critical dialogs must show Chinese actions with fail-safe defaults.
# Encoding: UTF-8
"""Regression coverage for the Chinese dialog helper (Phase Problem B).

Windows acceptance testing found confirmation dialogs whose body text is
Chinese (sometimes instructing 选择“否”) while the rendered buttons still
read Yes / No. The production code now builds its dialogs through
:mod:`views.dialogs`, which keeps Qt's standard buttons but labels them in
Chinese and makes cancellation the default and Escape action of every
destructive confirmation.

These tests verify the *real rendered buttons* - text, default button,
Escape button, keyboard and window-close behaviour through a real event loop -
and every in-scope production flow's recorded wording. The real functions are
captured at import time because the session's ``dialog_recorder`` fixture
replaces them per test. All data is fictional.
"""

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWizard

from helpers import make_wizard, prepare_case
from presenters.draft_presenter import DraftPresenter
from views import dialogs

# Captured before any fixture runs: dialog_recorder patches dialogs.* and
# QDialog.exec per test, so restoring these is the only way to drive a real
# event-loop dialog in an offscreen session.
_REAL_CONFIRM = dialogs.confirm
_REAL_INFORMATION = dialogs.information
_REAL_WARNING = dialogs.warning
_REAL_CRITICAL = dialogs.critical
_REAL_NOTICE_BOX = dialogs._notice_box
_REAL_QDIALOG_EXEC = QDialog.exec


# --------------------------------------------------------------------------- #
# Rendered-button verification (no event loop needed)
# --------------------------------------------------------------------------- #


def test_confirmation_dialog_renders_action_specific_chinese_buttons():
    box = dialogs._confirmation_box(
        None, "退出确认", "确定退出吗？", positive="确认退出", negative="取消",
        destructive=True,
    )
    yes = box.button(QMessageBox.StandardButton.Yes)
    no = box.button(QMessageBox.StandardButton.No)
    assert yes.text() == "确认退出"
    assert no.text() == "取消"
    assert box.defaultButton() is no, "destructive confirms must default to 取消"
    assert box.escapeButton() is no, "Esc must decline destructive confirms"
    assert box.standardButton(yes) == QMessageBox.StandardButton.Yes


def test_confirmation_dialog_negative_defaults_to_cancel():
    box = dialogs._confirmation_box(None, "保存草稿", "是否继续保存草稿？", positive="保存")
    assert box.button(QMessageBox.StandardButton.No).text() == "取消"
    assert box.defaultButton() is box.button(QMessageBox.StandardButton.No)


def test_non_destructive_confirmation_defaults_to_the_positive_action():
    box = dialogs._confirmation_box(
        None, "标题", "正文", positive="继续", negative="取消", destructive=False,
    )
    assert box.defaultButton() is box.button(QMessageBox.StandardButton.Yes)
    # Esc still declines even when the affirmative is the default.
    assert box.escapeButton() is box.button(QMessageBox.StandardButton.No)


def test_notice_dialog_labels_the_acknowledgement_button_in_chinese():
    for builder, icon in (
        (dialogs.information, QMessageBox.Icon.Information),
        (dialogs.warning, QMessageBox.Icon.Warning),
        (dialogs.critical, QMessageBox.Icon.Critical),
    ):
        box = dialogs._notice_box(None, "标题", "正文", icon)
        assert box.button(QMessageBox.StandardButton.Ok).text() == "确定"
        assert box.icon() == icon


# --------------------------------------------------------------------------- #
# Real event-loop behaviour (Esc / Enter / close / clicks)
# --------------------------------------------------------------------------- #


def _run_real_confirm(qapp, monkeypatch, action):
    """Run the *real* ``dialogs.confirm`` with a deferred click on its box."""
    monkeypatch.setattr(QDialog, "exec", _REAL_QDIALOG_EXEC)
    monkeypatch.setattr(dialogs, "confirm", _REAL_CONFIRM)
    holder = {}
    real_builder = dialogs._confirmation_box

    def capture(*args, **kwargs):
        box = real_builder(*args, **kwargs)
        holder["box"] = box
        return box

    monkeypatch.setattr(dialogs, "_confirmation_box", capture)
    QTimer.singleShot(0, lambda: action(holder))
    return dialogs.confirm(None, "测试标题", "测试正文", positive="确认退出")


def test_real_confirm_returns_true_only_for_the_affirmative_click(qapp, monkeypatch):
    def click_yes(holder):
        holder["box"].button(QMessageBox.StandardButton.Yes).click()

    assert _run_real_confirm(qapp, monkeypatch, click_yes) is True


def test_real_confirm_returns_false_for_the_negative_click(qapp, monkeypatch):
    def click_no(holder):
        holder["box"].button(QMessageBox.StandardButton.No).click()

    assert _run_real_confirm(qapp, monkeypatch, click_no) is False


def test_real_confirm_esc_declines(qapp, monkeypatch):
    def press_escape(holder):
        QTest.keyClick(holder["box"], Qt.Key_Escape)

    assert _run_real_confirm(qapp, monkeypatch, press_escape) is False


def test_real_confirm_enter_activates_the_safe_default(qapp, monkeypatch):
    def press_enter(holder):
        QTest.keyClick(holder["box"], Qt.Key_Return)

    assert _run_real_confirm(qapp, monkeypatch, press_enter) is False


def test_real_confirm_window_close_declines(qapp, monkeypatch):
    def close_dialog(holder):
        holder["box"].close()

    assert _run_real_confirm(qapp, monkeypatch, close_dialog) is False


def test_real_notice_dialog_completes_on_determine_click(qapp, monkeypatch):
    clicked_text = []
    monkeypatch.setattr(QDialog, "exec", _REAL_QDIALOG_EXEC)
    monkeypatch.setattr(dialogs, "information", _REAL_INFORMATION)
    real_builder = dialogs._notice_box

    def capture(*args, **kwargs):
        box = real_builder(*args, **kwargs)
        ok_button = box.button(QMessageBox.StandardButton.Ok)

        def click_ok():
            # Recorded while the dialog is alive: exec() destroys it on return.
            clicked_text.append(ok_button.text())
            ok_button.click()

        QTimer.singleShot(0, click_ok)
        return box

    monkeypatch.setattr(dialogs, "_notice_box", capture)
    dialogs.information(None, "提示", "测试数据已自动填入")
    assert clicked_text == ["确定"]


# --------------------------------------------------------------------------- #
# Production flows: recorded wording and fail-safe cancellation
# --------------------------------------------------------------------------- #


def _last_question(recorder):
    questions = [c for c in recorder if c["kind"] == "question"]
    assert questions, "expected a recorded confirmation dialog"
    return questions[-1]


def test_exit_confirmation_offers_chinese_actions(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.show()
    qapp.processEvents()

    wizard.button(QWizard.CancelButton).click()  # the fake confirms -> closes
    qapp.processEvents()

    call = _last_question(dialog_recorder)
    assert call["args"][1] == "退出确认"
    assert call["kwargs"]["positive"] == "确认退出"
    assert "取消" in call["args"][2]
    assert "请选择“否”" not in call["args"][2]


def test_save_draft_confirmation_offers_a_chinese_save_action(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")
    path = tmp_path / "本地化草稿.cfdraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )

    assert draft.save_draft() is True

    call = _last_question(dialog_recorder)
    assert call["args"][1] == "保存草稿"
    assert call["kwargs"]["positive"] == "保存"


def test_draft_overwrite_confirmation_offers_a_chinese_overwrite_action(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")
    path = tmp_path / "覆盖草稿.cfdraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )
    assert draft.save_draft() is True  # first write

    assert draft.save_draft() is True  # second write -> overwrite question
    call = _last_question(dialog_recorder)
    assert call["args"][1] == "覆盖草稿"
    assert call["kwargs"]["positive"] == "继续覆盖"


def test_replacement_confirmation_offers_a_chinese_replace_action(
    qapp, tmp_path, monkeypatch, dialog_recorder
):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")
    path = tmp_path / "替换草稿.cfdraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )
    assert draft.save_draft() is True
    assert draft.open_draft() is True  # session was replaced after confirmation
    assert draft.open_draft() is True  # restored session -> replacement prompt

    call = _last_question(dialog_recorder)
    assert call["args"][1] == "替换当前内容"
    assert call["kwargs"]["positive"] == "继续替换"


def test_demo_overwrite_confirmation_offers_a_chinese_action(qapp, dialog_recorder):
    from views.main_window import LawsuitWizard

    wizard = LawsuitWizard(demo_mode=True)
    wizard.case_selection_page.case_combo.setCurrentIndex(0)  # loan
    wizard.loan_claim_page.principal.setText("50000")  # counts as entered data

    wizard.welcome_page.fill_btn.click()

    call = _last_question(dialog_recorder)
    assert call["args"][1] == "覆盖确认"
    assert call["kwargs"]["positive"] == "确认覆盖"


def test_evidence_delete_confirmation_offers_a_chinese_action(
    qapp, dialog_recorder
):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")  # suggestion rows have content
    wizard.evidence_page.table.selectAll()
    wizard.show()
    qapp.processEvents()

    wizard.evidence_page.remove_selected_rows()  # the fake confirms -> rows go

    call = _last_question(dialog_recorder)
    assert call["args"][1] == "确认删除"
    assert call["kwargs"]["positive"] == "确认删除"


def test_declining_evidence_deletion_keeps_every_row(qapp, monkeypatch):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    rows_before = wizard.evidence_page.table.rowCount()
    wizard.evidence_page.table.selectAll()
    wizard.show()
    qapp.processEvents()

    from views import dialogs as live_dialogs

    monkeypatch.setattr(live_dialogs, "confirm", lambda *a, **kw: False)
    wizard.evidence_page.remove_selected_rows()

    assert wizard.evidence_page.table.rowCount() == rows_before


def test_declining_demo_overwrite_keeps_entered_data(qapp, monkeypatch):
    from views.main_window import LawsuitWizard

    wizard = LawsuitWizard(demo_mode=True)
    wizard.case_selection_page.case_combo.setCurrentIndex(0)  # loan
    wizard.loan_claim_page.principal.setText("50000")

    from views import dialogs as live_dialogs

    monkeypatch.setattr(live_dialogs, "confirm", lambda *a, **kw: False)
    wizard.welcome_page.fill_btn.click()

    assert wizard.loan_claim_page.principal.text() == "50000"


def test_declining_save_sensitive_confirmation_writes_nothing(
    qapp, tmp_path, monkeypatch
):
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "loan")
    path = tmp_path / "取消保存.cfdraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )

    from views import dialogs as live_dialogs

    monkeypatch.setattr(live_dialogs, "confirm", lambda *a, **kw: False)
    assert draft.save_draft() is False
    assert not path.exists()


def test_notice_flows_use_the_shared_chinese_helper(qapp, dialog_recorder):
    """Warnings in the migrated presenter layers record the same shape and
    keep their title and body, proving the notice helper preserved semantics.
    (The case-type combo defaults to a supported 案由, so an empty wizard is
    blocked by the party check first.)"""
    wizard, presenter = make_wizard()
    presenter.attempt_finish()  # empty wizard -> party-incomplete warning

    warnings = [c for c in dialog_recorder if c["kind"] == "warning"]
    assert warnings, "an empty wizard must warn when finishing"
    assert warnings[0]["args"][1] == "当事人信息不完整"
    assert "本次未导出任何文件" in warnings[0]["args"][2]
