# File: views/facts_examples_dialog.py
# Purpose: Shared "范例参考" dialog for the claim pages.
# Encoding: UTF-8
"""Reference-exemplar dialog shared by the five claim pages.

The dialog is read-only: it shows sample "事实与理由" prose so the user can
compare wording while filling the structured fields. Nothing is inserted back
into the wizard and no legal conclusion is asserted - the fixed disclaimer
states that the exemplars are writing references only.
"""

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)
from views.theme import INFO_LABEL, SECONDARY_BUTTON, SPACING_MD, SPACING_SM
from utils.facts_examples import FactsExamplesLibrary

_DISCLAIMER = "以下范例仅供写作参考，不构成法律意见；文书内容仍以您填写的结构化信息为准。"


class FactsExamplesDialog(QDialog):
    """Left-hand exemplar list, right-hand read-only viewer."""

    def __init__(self, case_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("事实与理由范例参考")
        self._case_type = case_type

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)

        disclaimer = QLabel(_DISCLAIMER)
        disclaimer.setObjectName(INFO_LABEL)
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        body = QHBoxLayout()
        self.example_list = QListWidget()
        self.example_viewer = QPlainTextEdit()
        self.example_viewer.setReadOnly(True)

        right = QVBoxLayout()
        right.setSpacing(SPACING_SM)
        self.example_desc = QLabel("")
        self.example_desc.setObjectName(INFO_LABEL)
        self.example_desc.setWordWrap(True)
        right.addWidget(self.example_desc)
        right.addWidget(self.example_viewer, 1)

        body.addWidget(self.example_list, 2)
        body.addLayout(right, 3)
        layout.addLayout(body)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName(SECONDARY_BUTTON)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        for title, _text in FactsExamplesLibrary.get_facts_examples(case_type):
            self.example_list.addItem(title)

        # Connect before selecting: the row change itself must populate the
        # viewer, otherwise the dialog opens with an empty right-hand pane.
        self.example_list.currentRowChanged.connect(self._show_example)
        if self.example_list.count() > 0:
            self.example_list.setCurrentRow(0)
        else:
            self.example_viewer.setPlainText("当前案由暂无范例。")

        # Cap the dialog to the available screen area (same convention as the
        # export page's preview dialog) so it never opens taller than the screen.
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is not None and available.isValid():
            self.resize(
                min(820, int(available.width() * 0.8)),
                min(640, int(available.height() * 0.8)),
            )
        else:
            self.resize(780, 560)

    def _show_example(self, row):
        examples = FactsExamplesLibrary.get_facts_examples(self._case_type)
        if 0 <= row < len(examples):
            title, text = examples[row]
            description = FactsExamplesLibrary.get_description(title)
            self.example_desc.setText(f"适用范围：{description}" if description else "")
            self.example_desc.setVisible(bool(description))
            self.example_viewer.setPlainText(text)
