# File: tests/test_help_dialog.py
# Purpose: In-app usage guide content and discoverability.
# Encoding: UTF-8
"""The help dialog is reference text, but it must still be complete, reachable
from every wizard page and free of absolute legal conclusions."""

from PySide6.QtWidgets import QApplication

from helpers import make_wizard
from views.help_dialog import HelpDialog


def test_help_content_covers_the_required_sections(qapp):
    dialog = HelpDialog()
    text = dialog.browser.toPlainText()
    for phrase in (
        "适用案由与输出",
        "建议填写顺序",
        "提交前重点核对",
        "劳动报酬案件的特别提示",
        "免责声明",
    ):
        assert phrase in text, phrase
    assert "不构成法律意见" in text
    assert "六类案由" in text
    assert "劳动仲裁申请书" in text


def test_help_dialog_never_exceeds_the_available_screen(qapp):
    dialog = HelpDialog()
    screen = dialog.screen() or QApplication.primaryScreen()
    available = screen.availableGeometry()
    assert dialog.width() <= available.width()
    assert dialog.height() <= available.height()


def test_every_wizard_page_exposes_the_help_action(qapp, dialog_recorder):
    wizard, _ = make_wizard()
    assert wizard._draft_bars
    for _page, bar in wizard._draft_bars:
        assert bar.help_button.text() == "使用说明"
        assert bar.help_button.accessibleName() == "使用说明"
        assert bar.help_button.accessibleDescription()

    dialog_recorder.clear()
    wizard._draft_bars[0][1].help_button.click()
    assert any(entry["kind"] == "dialog_exec" for entry in dialog_recorder)
