# File: views/dialogs.py
# Purpose: Chinese-labelled message dialogs with fail-safe cancellation.
# Encoding: UTF-8
"""Message dialogs whose buttons speak the same language as their text.

Qt renders its stock message-box buttons in English (Yes / No / OK) unless the
application loads Qt's own translation files. This application's dialogs write
Chinese body text that sometimes refers to a specific button by name, so an
English button next to Chinese prose is a real usability trap documented in
Windows acceptance testing (退出确认、替换当前内容、保存草稿、覆盖确认).

This module is the single place that builds message boxes for the main window,
the presenters and the draft/evidence pages. It keeps Qt's *standard* buttons
and their semantics (result codes, escape-button handling) and only changes the
rendered labels:

* confirmation dialogs show an action-specific Chinese affirmative plus 取消;
* on destructive confirmations the safe negative action is the default button
  and the Escape button, so Esc, Enter and the window close button all decline
  and only an explicit affirmative click continues;
* information / warning / critical dialogs label their single acknowledgement
  button 确定.

No global Qt translation is installed, no dialog styling system is introduced,
and no data persistence or document-generation logic runs here.
"""

from PySide6.QtWidgets import QMessageBox

#: The safe negative action every destructive confirmation offers.
CANCEL = "取消"
#: Label of the single acknowledgement button on notice dialogs.
ACKNOWLEDGE = "确定"

__all__ = ["confirm", "critical", "information", "warning"]


def confirm(parent, title, text, *, positive, negative=CANCEL, destructive=True,
            informative=None):
    """Ask the user a yes/no question with Chinese button labels.

    The two buttons stay Qt standard Yes/No buttons, so the return value keeps
    the established ``QMessageBox.StandardButton`` semantics: ``True`` only
    when the affirmative action was explicitly chosen. Destructive questions
    (the default) make the safe negative action the default button and the
    Escape button, so cancellation can never approve the operation. *informative*
    optionally supplies the secondary explanatory text Qt renders under the
    main message.
    """
    box = _confirmation_box(parent, title, text, positive=positive, negative=negative,
                            destructive=destructive, informative=informative)
    box.exec()
    return box.standardButton(box.clickedButton()) == QMessageBox.StandardButton.Yes


def _confirmation_box(parent, title, text, *, positive, negative=CANCEL,
                      destructive=True, informative=None):
    """Build a configured (not yet executed) Chinese-labelled question box.

    Separated from :func:`confirm` so tests can inspect the real rendered
    buttons, default button and Escape button without running an event loop.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    if informative:
        box.setInformativeText(informative)
    box.setIcon(QMessageBox.Icon.Question)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    yes_button = box.button(QMessageBox.StandardButton.Yes)
    no_button = box.button(QMessageBox.StandardButton.No)
    yes_button.setText(positive)
    no_button.setText(negative)
    if destructive:
        box.setDefaultButton(no_button)
    # Esc (and, through the close event, the title-bar close button) must
    # decline even when the affirmative is the default, so the Escape button
    # is always the safe negative action.
    box.setEscapeButton(no_button)
    if not destructive:
        box.setDefaultButton(yes_button)
    return box


def _notice_box(parent, title, text, icon):
    """Build a configured (not yet executed) 确定-labelled notice box."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.button(QMessageBox.StandardButton.Ok).setText(ACKNOWLEDGE)
    return box


def _notice(parent, title, text, icon):
    """Show a single-acknowledgement dialog whose button reads 确定."""
    _notice_box(parent, title, text, icon).exec()


def information(parent, title, text):
    """Show an informational dialog with a 确定 button."""
    _notice(parent, title, text, QMessageBox.Icon.Information)


def warning(parent, title, text):
    """Show a warning dialog with a 确定 button."""
    _notice(parent, title, text, QMessageBox.Icon.Warning)


def critical(parent, title, text):
    """Show an error dialog with a 确定 button."""
    _notice(parent, title, text, QMessageBox.Icon.Critical)
