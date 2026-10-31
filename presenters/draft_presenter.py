# File: presenters/draft_presenter.py
# Purpose: Orchestrates explicit draft save/open between the wizard and storage.
# Encoding: UTF-8
"""User-initiated draft save and open.

This layer owns everything the user sees and everything that changes the
application state; it deliberately contains no cryptography, no JSON and no
widget field knowledge:

* ``drafts`` validates and encrypts,
* ``views.draft_io`` reads and writes the wizard's widgets,
* this presenter decides *when* those happen, asks for confirmation, and swaps
  in a fully restored wizard only after a load has completely succeeded.

Both actions are strictly manual. Nothing here runs on a timer, on window
close, or on navigation; an application that is closed without pressing
"保存草稿" leaves no trace on disk.
"""

import datetime
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from drafts import (
    DRAFT_EXTENSION,
    DRAFT_FILE_FILTER,
    DraftError,
    load_draft,
    save_draft,
    validate_document,
)
from presenters.model_builder import is_supported_case_type
from views.draft_io import (
    apply_draft,
    capture_draft,
    has_meaningful_session,
    page_name,
)
from views.widgets import CASE_TYPE_LABELS


class DraftPresenter:
    """Wires the wizard's 保存草稿 / 打开草稿 actions to encrypted storage."""

    SAVE_TITLE = "保存草稿"
    OPEN_TITLE = "打开草稿"

    def __init__(self, wizard, presenter, wizard_factory=None, protector=None):
        self.presenter = presenter
        self._wizard_factory = wizard_factory or self._default_wizard_factory
        self._protector = protector
        self.wizard = None
        self.attach(wizard)

    # ------------------------------------------------------------------ #
    # Wiring
    # ------------------------------------------------------------------ #

    def attach(self, wizard):
        """Connect the draft actions of *wizard* (idempotent per wizard).

        The wizard re-emits the per-page button clicks as two signals, so one
        connection covers every page. ``UniqueConnection`` makes re-attaching
        the same wizard a no-op, which keeps the swap path from stacking
        duplicate handlers on a replacement window.
        """
        for signal, slot in (
            (wizard.save_draft_requested, self.save_draft),
            (wizard.open_draft_requested, self.open_draft),
        ):
            signal.connect(slot, Qt.ConnectionType.UniqueConnection)
        self.wizard = wizard

    @staticmethod
    def _default_wizard_factory(demo_mode=False):
        # Imported lazily so this presenter does not import the view package at
        # module import time (and to keep the composition root in charge).
        from views.main_window import LawsuitWizard

        return LawsuitWizard(demo_mode=demo_mode)

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save_draft(self):
        """Run the full save flow; return ``True`` only after a durable write."""
        wizard = self.wizard
        case_type = wizard.field("case_type")
        if not is_supported_case_type(case_type):
            QMessageBox.warning(
                self.wizard,
                self.SAVE_TITLE,
                "请先选择案件类型后再保存草稿。\n本次未写入任何文件。",
            )
            return False

        if not self._confirm_sensitive_save():
            return False

        path = self._ask_save_path()
        if not path:
            return False

        if os.path.exists(path) and not self._confirm_overwrite(path):
            return False

        try:
            document = validate_document(capture_draft(wizard, page_name(wizard)))
            save_draft(path, document, protector=self._protector)
        except DraftError as exc:
            QMessageBox.warning(
                self.wizard,
                "保存草稿失败",
                f"{exc}\n\n当前填写内容仍保留在程序中，本次未写入草稿文件。",
            )
            return False
        except Exception:
            # Never surface a raw exception: it may embed field values.
            QMessageBox.warning(
                self.wizard,
                "保存草稿失败",
                "保存草稿时发生未预期的错误，本次未写入草稿文件。\n"
                "当前填写内容仍保留在程序中。",
            )
            return False

        QMessageBox.information(
            self.wizard,
            "草稿已保存",
            "草稿已加密保存到：\n"
            f"{path}\n\n"
            "请注意：\n"
            "· 草稿使用 Windows 当前用户加密，只能在同一 Windows 用户账户下打开；"
            "更换账户、电脑或系统配置后可能无法恢复。\n"
            "· 草稿是可继续填写的中间文件，不是法院文书，也不是通用备份。\n"
            "· 程序不会自动保存，退出前请自行保存草稿。",
        )
        return True

    def _confirm_sensitive_save(self):
        answer = QMessageBox.question(
            self.wizard,
            self.SAVE_TITLE,
            "草稿将包含当事人姓名、证件号码、联系方式、案件事实与证据等敏感信息，"
            "并以 Windows 当前用户加密的方式写入您选择的本地文件。\n\n"
            "加密只保护文件内容：使用同一 Windows 账户的其他程序仍可能读取；"
            "草稿也不能在更换账户或电脑后保证打开。\n\n"
            "是否继续保存草稿？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _confirm_overwrite(self, path):
        answer = QMessageBox.question(
            self.wizard,
            "覆盖草稿",
            "该位置已存在同名文件：\n"
            f"{path}\n\n"
            "覆盖后原有草稿将被替换。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_file_path(self):
        """Suggest a neutral filename that never embeds a party name."""
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return os.path.join(os.path.expanduser("~"), f"案件草稿_{stamp}{DRAFT_EXTENSION}")

    def _ask_save_path(self):
        path, _selected = QFileDialog.getSaveFileName(
            self.wizard,
            self.SAVE_TITLE,
            self._default_file_path(),
            DRAFT_FILE_FILTER,
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return ""
        return self._with_extension(path)

    @staticmethod
    def _with_extension(path):
        if path.lower().endswith(DRAFT_EXTENSION):
            return path
        return path + DRAFT_EXTENSION

    # ------------------------------------------------------------------ #
    # Open
    # ------------------------------------------------------------------ #

    def open_draft(self):
        """Run the full open flow; the live session only changes on success."""
        path = self._ask_open_path()
        if not path:
            return False

        try:
            document = load_draft(path, protector=self._protector)
        except DraftError as exc:
            QMessageBox.warning(
                self.wizard,
                "无法打开草稿",
                f"{exc}\n\n当前填写内容未做任何更改。",
            )
            return False
        except Exception:
            QMessageBox.warning(
                self.wizard,
                "无法打开草稿",
                "草稿文件无法读取或解析。\n当前填写内容未做任何更改。",
            )
            return False

        if self._has_unsaved_session() and not self._confirm_replace_session():
            return False

        try:
            new_wizard, result = self._build_restored_wizard(document)
        except Exception:
            QMessageBox.warning(
                self.wizard,
                "无法打开草稿",
                "草稿内容无法完整还原。\n当前填写内容未做任何更改。",
            )
            return False

        self._swap_wizard(new_wizard)
        QMessageBox.information(
            self.wizard,
            "草稿已打开",
            self._restored_message(document, result, path),
        )
        return True

    def _ask_open_path(self):
        path, _selected = QFileDialog.getOpenFileName(
            self.wizard,
            self.OPEN_TITLE,
            os.path.expanduser("~"),
            DRAFT_FILE_FILTER,
        )
        return path or ""

    def _build_restored_wizard(self, document):
        """Build and restore an isolated replacement wizard.

        The live wizard is never touched here: if any step of the restoration
        fails, the exception propagates and the caller keeps the current
        session exactly as it was.
        """
        demo_mode = bool(getattr(self.wizard, "demo_mode", False))
        new_wizard = self._wizard_factory(demo_mode=demo_mode)
        # A wizard only accepts setCurrentId() once it has started.
        new_wizard.restart()
        result = apply_draft(new_wizard, document)
        return new_wizard, result

    def _swap_wizard(self, new_wizard):
        """Adopt *new_wizard* and retire the previous one.

        The replacement is shown before the old window closes so the Qt event
        loop never observes zero visible windows; otherwise
        ``quitOnLastWindowClosed`` would terminate the application.
        """
        old_wizard = self.wizard
        self.presenter.rebind_view(new_wizard)
        self.attach(new_wizard)
        new_wizard.show()
        old_wizard.close()

    def _has_unsaved_session(self):
        """Return whether the current session holds state worth protecting.

        The contract lives in :func:`views.draft_io.has_meaningful_session` so
        the draft guard and the demo-fill guard cannot disagree about what
        counts as user input. An inspection failure is reported as "has data":
        refusing to warn is a data-loss risk, warning needlessly is not.
        """
        try:
            return has_meaningful_session(self.wizard)
        except Exception:
            return True

    def _confirm_replace_session(self):
        answer = QMessageBox.question(
            self.wizard,
            "替换当前内容",
            "当前窗口包含已填写或已修改的案件信息。\n"
            "打开其他草稿将替换当前窗口中的内容。\n"
            "如需保留当前修改，请先保存草稿。\n\n"
            "是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _restored_message(self, document, result, path):
        label = CASE_TYPE_LABELS.get(document.case_type, "未知案由")
        lines = [
            f"已从草稿恢复案件信息（{label}）。",
            "",
            f"草稿文件：\n{path}",
        ]
        if result.note:
            lines.extend(["", result.note])
        if document.case_type == "contract" and document.fields.get("c_penalty_amount", "").strip():
            lines.extend([
                "",
                "提示：违约金金额按原样恢复，但草稿不保留辅助计算的校验记录。"
                "如需在文书中说明计算依据，请重新使用“辅助计算”按钮后再生成。",
            ])
        lines.extend(["", "请核对内容后继续填写。"])
        return "\n".join(lines)
