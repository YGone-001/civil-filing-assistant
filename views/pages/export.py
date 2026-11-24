# File: views/pages/export.py
# Purpose: Export page (three-document cards, output directory, text preview).
# Encoding: UTF-8
"""Export and preview: the three-document card strip, output-directory
selection, the read-only text preview (built from the shared
``build_case_model`` path) and the result of the latest export."""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from views.theme import (
    DOC_CARD,
    DOC_CARD_DESC,
    DOC_CARD_ICON,
    DOC_CARD_TITLE,
    INFO_LABEL,
    SECONDARY_BUTTON,
    SPACING_MD,
    SUCCESS_LABEL,
)
from views.pages.base import _TitledPage
from views.pages.common import _wrap_in_scroll

class _PreviewDialog(QDialog):
    """A scrollable, read-only document-style preview of the complaint.

    The dialog renders an approximate page view, but it still states that the
    preview does not represent the final Word layout (fonts, tables, headers,
    page breaks). When ``html`` is omitted the plain ``text`` is shown, which
    keeps the dialog usable in tests and as a fallback.
    """

    def __init__(self, title, text, parent=None, html=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)

        disclaimer = QLabel(
            "以下为文书式预览，字体和分页仅为近似效果，不代表最终 Word 排版"
            "（表格、页眉页脚、分页等以导出文件为准）。"
        )
        disclaimer.setObjectName(INFO_LABEL)
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        self.viewer = QTextBrowser()
        self.viewer.setReadOnly(True)
        self.viewer.setOpenExternalLinks(False)
        self.viewer.setAccessibleName("起诉状预览内容")
        self.viewer.setAccessibleDescription("按当前填写内容生成的起诉状近似预览")
        if html:
            self.viewer.setHtml(html)
        else:
            self.viewer.setPlainText(text)
        layout.addWidget(self.viewer)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        # Cap the dialog to the available screen area so long previews stay
        # fully visible (including the close button) on small or high-DPI
        # displays instead of opening taller than the screen.
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is not None and available.isValid():
            self.resize(
                min(760, int(available.width() * 0.8)),
                min(680, int(available.height() * 0.8)),
            )
        else:
            self.resize(720, 560)


class ExportPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("核对与导出")
        # Ensure it acts as the final page
        self.setFinalPage(True)

        # Default output directory: the current user's desktop.
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        layout = QVBoxLayout()

        intro_row = QHBoxLayout()
        intro = QLabel("信息收集完毕，建议先预览完整起诉状，核对无误后再生成文书。")
        intro.setWordWrap(True)
        intro_row.addWidget(intro, 1)
        self.preview_btn = QPushButton("预览起诉状")
        self.preview_btn.setObjectName(SECONDARY_BUTTON)
        self.preview_btn.setAccessibleName("预览起诉状")
        self.preview_btn.clicked.connect(self.show_preview)
        intro_row.addWidget(self.preview_btn)
        layout.addLayout(intro_row)

        # --- Three document cards (horizontal strip) ----------------------
        doc_group = QGroupBox("将生成的文书")
        doc_outer = QVBoxLayout()
        doc_outer.setSpacing(SPACING_MD)
        doc_cards = QHBoxLayout()
        doc_cards.setSpacing(SPACING_MD)
        for icon, title, desc in (
            ("诉", "民事起诉状", "当事人、请求与理由"),
            ("证", "证据清单", "证据与证明目的"),
            ("送", "送达地址确认书", "法院送达地址确认"),
        ):
            card = QWidget()
            card.setObjectName(DOC_CARD)
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(8)

            icon_label = QLabel(icon)
            icon_label.setObjectName(DOC_CARD_ICON)
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(icon_label)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName(DOC_CARD_TITLE)
            text_layout.addWidget(title_label)
            desc_label = QLabel(desc)
            desc_label.setObjectName(DOC_CARD_DESC)
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)
            card_layout.addLayout(text_layout)
            card_layout.addStretch()

            doc_cards.addWidget(card, 1)

        doc_outer.addLayout(doc_cards)
        doc_note = QLabel("以上文书均为辅助生成的可编辑初稿，请人工核对后再行使用。")
        doc_note.setObjectName(INFO_LABEL)
        doc_note.setWordWrap(True)
        doc_outer.addWidget(doc_note)
        doc_group.setLayout(doc_outer)
        layout.addWidget(doc_group)

        # --- Output directory ---------------------------------------------
        dir_group = QGroupBox("保存位置")
        dir_layout = QVBoxLayout()
        self.dir_label = QLabel(self.output_dir)
        self.dir_label.setWordWrap(True)
        dir_layout.addWidget(self.dir_label)

        dir_btn_layout = QHBoxLayout()
        self.change_dir_btn = QPushButton("更改目录")
        self.change_dir_btn.setObjectName(SECONDARY_BUTTON)
        self.change_dir_btn.setAccessibleName("更改输出目录")
        self.change_dir_btn.clicked.connect(self.change_directory)
        dir_btn_layout.addWidget(self.change_dir_btn)

        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.setObjectName(SECONDARY_BUTTON)
        self.open_dir_btn.setAccessibleName("打开输出目录")
        self.open_dir_btn.clicked.connect(self.open_output_directory)
        dir_btn_layout.addWidget(self.open_dir_btn)
        dir_btn_layout.addStretch()
        dir_btn_widget = QWidget()
        dir_btn_widget.setLayout(dir_btn_layout)
        dir_layout.addWidget(dir_btn_widget)

        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # --- Latest export result (hidden until a successful export) ------
        self.result_group = QGroupBox("本次生成结果")
        result_layout = QVBoxLayout()
        self.result_label = QLabel("")
        self.result_label.setObjectName(SUCCESS_LABEL)
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        result_layout.addWidget(self.result_label)

        result_btn_layout = QHBoxLayout()
        self.open_result_btn = QPushButton("打开本次生成的文件夹")
        self.open_result_btn.setObjectName(SECONDARY_BUTTON)
        self.open_result_btn.setAccessibleName("打开本次生成的文件夹")
        self.open_result_btn.clicked.connect(self.open_last_export_directory)
        result_btn_layout.addWidget(self.open_result_btn)
        result_btn_layout.addStretch()
        result_layout.addLayout(result_btn_layout)

        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        layout.addWidget(self.result_group)

        self.last_export_dir = None

        self.setLayout(_wrap_in_scroll(layout))

    # ------------------------------------------------------------------ #
    # Output directory
    # ------------------------------------------------------------------ #

    def get_output_directory(self):
        """Return the currently configured output directory."""
        return self.output_dir

    def change_directory(self):
        """Let the user pick a different output directory via a file dialog."""
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "选择保存目录",
            self.output_dir,
        )
        if new_dir:
            self.output_dir = new_dir
            self.dir_label.setText(new_dir)

    def show_export_result(self, target_dir, files):
        """Show where the latest successful export was written."""
        self.last_export_dir = target_dir
        self.result_label.setText(
            f"已生成 {len(files)} 份文件（起诉状、证据清单、送达地址确认书）。\n"
            f"文件夹：{target_dir}\n"
            "如需修改，可返回前面的步骤调整后再次生成；新结果另存为新文件夹，不覆盖本次文件。"
        )
        self.result_group.setVisible(True)

    def open_last_export_directory(self):
        """Open the folder of the latest successful export."""
        if self.last_export_dir:
            self._open_folder(self.last_export_dir)

    def open_output_directory(self):
        """Open the configured output directory in the system file explorer."""
        self._open_folder(self.output_dir)

    @staticmethod
    def _open_folder(path):
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Preview
    # ------------------------------------------------------------------ #

    def show_preview(self):
        """Show the complete complaint in a document-style preview dialog."""
        from views import dialogs
        from views.widgets import CASE_TYPE_LABELS

        wizard = self.wizard()
        case_type = wizard.field("case_type")
        label = (
            CASE_TYPE_LABELS.get(case_type, "未知案由")
            if isinstance(case_type, str) else "未知案由"
        )

        try:
            from presenters.model_builder import build_case_model
            from utils.document_preview import build_complaint_html, build_complaint_text

            model = build_case_model(wizard)
            preview_text = build_complaint_text(model)
            preview_html = build_complaint_html(model)
        except Exception as exc:  # a preview failure must never crash the wizard
            dialogs.warning(self, "预览不可用", f"暂时无法生成“{label}”预览：\n{exc}")
            return

        # Stash the text so tests can inspect it without a modal dialog.
        self._last_preview_text = preview_text
        self._last_preview_html = preview_html

        dialog = _PreviewDialog("民事起诉状预览", preview_text, self, html=preview_html)
        dialog.exec()
        dialog.deleteLater()
