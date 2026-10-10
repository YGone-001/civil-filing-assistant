# File: presenters/main_presenter.py
# Purpose: Bridge between View (QWizard) and Model/Utils
# Encoding: UTF-8

import os

from PySide6.QtWidgets import QMessageBox

from presenters.model_builder import build_case_model
from utils.doc_generator import DocumentGenerator
from utils.security_check import SecurityGuard
from utils.batch_manager import BatchExportManager


class MainPresenter:
    # Explicit Finish-lifecycle outcomes. The wizard only advances to its Qt
    # accepted (closed) state when the pre-accept export reports SUCCESS; any
    # other outcome keeps the wizard open for correction and retry.
    FINISH_SUCCESS = "SUCCESS"
    FINISH_VALIDATION_FAILED = "VALIDATION_FAILED"
    FINISH_EXPORT_FAILED = "EXPORT_FAILED"

    def __init__(self, view):
        self.view = view
        self._export_in_progress = False
        # The wizard owns its own accept() lifecycle (the real "Finish" button
        # routes through it); it asks the presenter whether the pre-accept
        # export step succeeded before committing to accept.
        self.view.set_finish_handler(self._on_finish_requested)

    def _on_finish_requested(self):
        """Return True only when the wizard may advance to its accepted state."""
        return self.attempt_finish() == self.FINISH_SUCCESS

    def attempt_finish(self):
        """Run validation and export; return one of the ``FINISH_*`` codes.

        A reentrant call while an export is already in progress is ignored, so a
        single Finish action can never trigger duplicate exports.
        """
        if self._export_in_progress:
            return self.FINISH_EXPORT_FAILED
        self._export_in_progress = True
        try:
            return self._perform_export()
        finally:
            self._export_in_progress = False

    def on_wizard_accepted(self):
        """Backwards-compatible entry point kept for existing callers and tests.

        The wizard's real Finish flow calls :meth:`attempt_finish` through the
        registered finish handler instead of relying on this method.
        """
        self.attempt_finish()

    def _perform_export(self):
        """Validate the input, build the model and export the three documents.

        A failed export must never terminate the application: the wizard stays
        open so the user can correct the input and retry.
        """
        case_type = self.view.field("case_type")

        # Never silently drop incomplete parties and then produce a document
        # that misrepresents the case; block export instead.
        if not self.view.party_page.isComplete():
            QMessageBox.warning(
                self.view,
                "当事人信息不完整",
                "请至少填写一名原告和一名被告的姓名/名称后再生成文书。\n"
                "为避免生成与案情不符的文书，本次未导出任何文件。",
            )
            return self.FINISH_VALIDATION_FAILED

        model = build_case_model(self.view)

        # Explicitly confirmed facts that contradict each other must block export
        # so that no self-contradictory document is published; the wizard stays
        # open so the user can correct the input and retry.
        conflict = getattr(model, "delivery_receipt_conflict", None)
        if callable(conflict) and conflict():
            QMessageBox.warning(
                self.view,
                "信息相互矛盾",
                "“未交货”与“已签收”不能同时成立。\n"
                "请返回修改交货状态或签收状态后再生成文书；本次未导出任何文件。",
            )
            return self.FINISH_VALIDATION_FAILED

        if case_type == "property":
            self._warn_property_mismatch(model)

        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            manager = BatchExportManager(DocumentGenerator())
            target_dir, files = manager.run_batch_export(model, desktop_path)
        except Exception as exc:
            # A failed export must not be reported as success, must not leave
            # the process, and must leave the application usable for retry.
            QMessageBox.critical(
                self.view,
                "生成失败",
                "生成文档时发生错误：\n"
                f"{exc}\n\n"
                "未生成完整的文书文件。您可以修改信息后重新点击“完成”重试。",
            )
            return self.FINISH_EXPORT_FAILED

        # Best-effort in-process cleanup of sensitive model strings. Python
        # cannot guarantee that the underlying memory is irreversibly erased,
        # and this does not delete any file already written to disk.
        SecurityGuard.wipe_memory(model)

        QMessageBox.information(
            self.view,
            "生成成功",
            "立案材料已生成完成（起诉状 / 证据清单 / 送达地址确认书）。\n\n"
            f"文件夹位置：\n{target_dir}\n\n"
            f"本次共生成 {len(files)} 份文件。\n\n"
            "说明：程序仅对内存中的字段做了尽力清理，不会自动删除已生成的文件，"
            "请自行妥善保存或销毁。",
        )
        return self.FINISH_SUCCESS

    def _warn_property_mismatch(self, model):
        """Warn (without overwriting) when a hand-entered total differs a lot."""
        from decimal import Decimal, InvalidOperation

        try:
            model.months = model._calc_months()
            computed = model._calc_total()
            user_total_text = (model.total_principal or "").strip()
            if not user_total_text or computed is None:
                return
            user_total = Decimal(user_total_text)
            if user_total == 0:
                return
            diff = abs(user_total - computed) / user_total
            if diff > Decimal("0.01"):
                QMessageBox.warning(
                    self.view,
                    "提示",
                    "物业费自填总金额与系统按整月计算的结果差异超过 1%，"
                    "系统未覆盖您填写的金额，请人工核对（仍将继续生成文书）。",
                )
        except (InvalidOperation, ValueError, ArithmeticError):
            return
