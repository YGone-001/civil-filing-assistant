# File: views/pages/welcome.py
# Purpose: Wizard welcome page (landing, privacy notes, demo entry).
# Encoding: UTF-8
"""The wizard's landing page: one-line lead, three-document strip, offline
privacy notes and the demo-mode test-data entry point."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from views.theme import (
    DEMO_BADGE,
    DOC_CARD,
    DOC_CARD_DESC,
    DOC_CARD_ICON,
    DOC_CARD_TITLE,
    INFO_LABEL,
    PAGE_LEAD,
    PRIMARY_BUTTON,
)
from views.widgets import content_column
from views.pages.base import _TitledPage

class WelcomePage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("欢迎使用民事立案文书助手")

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # A single concise lead line describing what the tool does in one breath.
        lead = QLabel("引导填写案情，一键生成民事立案所需的三份可编辑 Word 初稿。")
        lead.setObjectName(PAGE_LEAD)
        lead.setWordWrap(True)
        layout.addWidget(lead)

        # Three-document preview strip (reuses the export-page card styling).
        docs_row = QHBoxLayout()
        docs_row.setSpacing(8)
        for icon, name, desc in (
            ("诉", "民事起诉状", "当事人、请求与事实理由"),
            ("证", "证据清单", "证据与证明目的"),
            ("送", "送达地址确认书", "法院送达地址确认"),
        ):
            chip = QWidget()
            chip.setObjectName(DOC_CARD)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(10, 10, 10, 10)
            chip_layout.setSpacing(8)
            icon_label = QLabel(icon)
            icon_label.setObjectName(DOC_CARD_ICON)
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip_layout.addWidget(icon_label)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            title_label = QLabel(name)
            title_label.setObjectName(DOC_CARD_TITLE)
            text_layout.addWidget(title_label)
            desc_label = QLabel(desc)
            desc_label.setObjectName(DOC_CARD_DESC)
            text_layout.addWidget(desc_label)
            chip_layout.addLayout(text_layout)
            chip_layout.addStretch()
            docs_row.addWidget(chip)
        layout.addLayout(docs_row)

        # Local / offline privacy notes, kept visibly distinct from the flow.
        offline_note = QLabel(
            "本地运行：案件信息仅在本机处理，生成文书时不联网上传。\n"
            "启动时会检测网络状态并给出提示，该提示仅为辅助提醒，不等于系统级防火墙隔离。\n"
            "生成完成后会尽力清理内存中的敏感信息，但无法保证彻底销毁。"
        )
        offline_note.setObjectName(INFO_LABEL)
        offline_note.setWordWrap(True)
        layout.addWidget(offline_note)

        next_hint = QLabel("点击“下一步”开始填写。")
        next_hint.setWordWrap(True)
        layout.addWidget(next_hint)

        # Demo-mode badge, hidden in production.
        self.demo_badge = QLabel("演示模式")
        self.demo_badge.setObjectName(DEMO_BADGE)
        self.demo_badge.setVisible(False)
        layout.addWidget(self.demo_badge)

        layout.addStretch()

        # Test-data entry point, only shown in demo mode (see set_demo_mode).
        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setObjectName(PRIMARY_BUTTON)
        self.fill_btn.setVisible(False)
        layout.addWidget(self.fill_btn)

        self.setLayout(content_column(layout))

    def set_demo_mode(self, enabled):
        """Show or hide the demo-mode badge and test-data button."""
        self.fill_btn.setVisible(enabled)
        self.demo_badge.setVisible(enabled)
