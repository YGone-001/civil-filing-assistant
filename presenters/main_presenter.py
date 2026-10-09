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
    def __init__(self, view):
        self.view = view
        self.view.accepted.connect(self.on_wizard_accepted)

    def on_wizard_accepted(self):
        """Gather data, build the model and export the three Word documents.

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
            return

        model = build_case_model(self.view)

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
            return

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
