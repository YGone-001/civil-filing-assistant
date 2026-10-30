# File: views/pages/export.py
# Purpose: Export page (three-document cards, output directory, text preview).
# Encoding: UTF-8
"""Export and preview: the three-document card strip, output-directory
selection, the read-only text preview (built from the shared
``build_case_model`` path) and the exit notice."""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
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
)
from views.widgets import content_column
from views.pages.base import _TitledPage

class _PreviewDialog(QDialog):
    """A scrollable, read-only preview of the case text before export.

    The dialog explicitly states that the preview is plain text only and does
    not represent the final Word layout (fonts, tables, headers, page breaks).
    """

    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)

        disclaimer = QLabel(
            "以下预览仅展示文本内容，不代表最终 Word 排版"
            "（字体、表格、页眉页脚、分页等）。"
        )
        disclaimer.setObjectName(INFO_LABEL)
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        layout.addWidget(viewer)

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

        intro = QLabel("信息收集完毕，请核对以下内容后生成文书。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

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

        # --- Actions (content-width, right-aligned single row) ------------
        action_group = QGroupBox("操作")
        action_row = QHBoxLayout()
        action_row.addStretch(1)

        self.preview_btn = QPushButton("预览关键信息")
        self.preview_btn.setObjectName(SECONDARY_BUTTON)
        self.preview_btn.setAccessibleName("预览关键信息")
        self.preview_btn.clicked.connect(self.show_preview)
        action_row.addWidget(self.preview_btn)

        # Exit (secondary, not destructive) ----------------------------
        self.secure_exit_btn = QPushButton("退出程序（不删除已生成文件）")
        self.secure_exit_btn.setObjectName(SECONDARY_BUTTON)
        self.secure_exit_btn.setAccessibleName("退出程序")
        self.secure_exit_btn.clicked.connect(self.secure_exit)
        action_row.addWidget(self.secure_exit_btn)

        action_group.setLayout(action_row)
        layout.addWidget(action_group)

        self.setLayout(content_column(layout))

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

    def open_output_directory(self):
        """Open the configured output directory in the system file explorer."""
        path = self.output_dir
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
        """Show a case-specific preview in a scrollable dialog."""
        from PySide6.QtWidgets import QMessageBox

        from views.widgets import CASE_TYPE_LABELS

        wizard = self.wizard()
        case_type = wizard.field("case_type")
        label = (
            CASE_TYPE_LABELS.get(case_type, "未知案由")
            if isinstance(case_type, str) else "未知案由"
        )

        try:
            from presenters.model_builder import build_case_model
            model = build_case_model(wizard)
            claims = model.render_claims()
            facts = model.render_facts()
        except Exception as exc:  # a preview failure must never crash the wizard
            QMessageBox.warning(self, "预览不可用", f"暂时无法生成“{label}”预览：\n{exc}")
            return

        claims_text = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))

        evidence_lines = []
        for i, ev in enumerate(getattr(model, "evidences", []), 1):
            name = getattr(ev, "name", str(ev))
            target = getattr(ev, "target", "")
            if target:
                evidence_lines.append(f"{i}. {name} —— {target}")
            else:
                evidence_lines.append(f"{i}. {name}")
        evidence_text = "\n".join(evidence_lines) if evidence_lines else "（未填写证据）"

        preview_text = (
            f"案由：{label}\n\n"
            f"【诉讼请求（预览）】\n{claims_text}\n\n"
            f"【事实与理由（预览）】\n{facts}\n\n"
            f"【证据清单（预览）】\n{evidence_text}"
        )

        # Stash the text so tests can inspect it without a modal dialog.
        self._last_preview_text = preview_text

        dialog = _PreviewDialog("关键信息预览", preview_text, self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    # Exit
    # ------------------------------------------------------------------ #

    def secure_exit(self):
        """Close the wizard without claiming that files or memory were destroyed."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "退出",
            "程序将关闭。案件信息存在于本机内存与已生成的 Word 文件中；"
            "关闭程序不会自动删除已生成的文件，请按需自行妥善保存或销毁。",
        )
        self.wizard().close()
