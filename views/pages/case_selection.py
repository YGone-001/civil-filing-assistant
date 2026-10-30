# File: views/pages/case_selection.py
# Purpose: Case-type selection page (card selector + labour notice).
# Encoding: UTF-8
"""Case-category card selector backing the ``case_type`` wizard field, with
the persistent labour-arbitration notice shown while "labor" is selected."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from views.theme import (
    CASE_CARD,
    CASE_CARD_BADGE,
    CASE_CARD_DESC,
    CASE_CARD_TITLE,
    PAGE_LEAD,
    REMINDER_LABEL,
    SPACING_MD,
)
from views.widgets import content_column
from views.pages.base import _TitledPage

class CaseSelectionPage(_TitledPage):
    # One-line suitability notes shown under each choice.
    CASE_DESCRIPTIONS = {
        "loan": "适用于个人之间或自然人向他人出借资金的借款纠纷。",
        "contract": "适用于买卖双方就货款、交付、验收等问题发生的合同纠纷。",
        "property": "适用于业主与物业公司之间的物业费、服务合同纠纷。",
        "labor": "适用于工资、加班费等劳动报酬追索（注意仲裁前置）。",
        "divorce": "适用于离婚、子女抚养与财产分割等婚姻家庭纠纷。",
    }

    # Single-character badges rendered in each selection card.
    CASE_MONOGRAMS = {
        "loan": "借",
        "contract": "买",
        "property": "物",
        "labor": "劳",
        "divorce": "离",
    }

    def __init__(self):
        super().__init__()
        self.set_page_title("选择案件类型")

        layout = QVBoxLayout()
        layout.setSpacing(12)

        lead = QLabel("请选择本次起诉的案由，系统将据此匹配文书模板与证据建议。")
        lead.setObjectName(PAGE_LEAD)
        lead.setWordWrap(True)
        layout.addWidget(lead)

        # Hidden backing store for the wizard field: kept out of sight but still
        # bound to the form via registerField below.
        self.case_combo = QComboBox()
        self.case_combo.setAccessibleName("案由选择")
        self.case_combo.setAccessibleDescription("选择起诉状的案件类型")
        self.case_combo.addItem("民间借贷纠纷", "loan")
        self.case_combo.addItem("买卖合同纠纷", "contract")
        self.case_combo.addItem("物业服务合同纠纷", "property")
        self.case_combo.addItem("劳动报酬/工资追索", "labor")
        self.case_combo.addItem("离婚纠纷", "divorce")
        self.case_combo.setVisible(False)

        # --- Card-style selector (two-column grid) ------------------------
        self._case_cards = []
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(SPACING_MD)
        cards_grid.setVerticalSpacing(SPACING_MD)
        cards_grid.setColumnStretch(0, 1)
        cards_grid.setColumnStretch(1, 1)
        cases = [
            ("loan", "民间借贷纠纷"),
            ("contract", "买卖合同纠纷"),
            ("property", "物业服务合同纠纷"),
            ("labor", "劳动报酬/工资追索"),
            ("divorce", "离婚纠纷"),
        ]
        for index, (key, label) in enumerate(cases):
            card = QPushButton()
            card.setObjectName(CASE_CARD)
            card.setProperty("caseCardSelected", "false")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setAccessibleName(f"案由卡片：{label}")
            card.clicked.connect(lambda _checked, k=key: self._select_case_by_key(k))

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(12)

            badge = QLabel(self.CASE_MONOGRAMS.get(key, ""))
            badge.setObjectName(CASE_CARD_BADGE)
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            card_layout.addWidget(badge)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)

            title = QLabel(label)
            title.setObjectName(CASE_CARD_TITLE)
            title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            desc = QLabel(self.CASE_DESCRIPTIONS.get(key, ""))
            desc.setObjectName(CASE_CARD_DESC)
            desc.setWordWrap(True)
            desc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            text_layout.addWidget(title)
            text_layout.addWidget(desc)
            card_layout.addLayout(text_layout, 1)

            cards_grid.addWidget(card, index // 2, index % 2)
            self._case_cards.append((key, card))

        layout.addLayout(cards_grid)

        # Persistent labour-arbitration notice, shown only while "labor" is
        # selected (replaces the previous blocking dialog).
        self.labor_notice = QLabel("")
        self.labor_notice.setObjectName(REMINDER_LABEL)
        self.labor_notice.setWordWrap(True)
        self.labor_notice.setVisible(False)
        layout.addWidget(self.labor_notice)

        layout.addStretch()
        self.setLayout(content_column(layout))

        from utils.labor_security import LaborProcedureGuard
        self.labor_guard = LaborProcedureGuard()
        self.case_combo.currentTextChanged.connect(self._on_case_type_changed)
        self.case_combo.currentIndexChanged.connect(self._sync_card_selection)
        self._refresh_case_context()
        self._sync_card_selection(self.case_combo.currentIndex())

        self.registerField("case_type", self.case_combo, "currentData")

    def _select_case_by_key(self, key):
        """Update the hidden combo when a card is clicked."""
        idx = self.case_combo.findData(key)
        if idx >= 0:
            self.case_combo.setCurrentIndex(idx)

    def _sync_card_selection(self, _index):
        """Highlight the card matching the combo's current selection."""
        current_key = self.case_combo.currentData()
        for key, card in self._case_cards:
            selected = "true" if key == current_key else "false"
            if card.property("caseCardSelected") != selected:
                card.setProperty("caseCardSelected", selected)
                style = card.style()
                if style is not None:
                    style.unpolish(card)
                    style.polish(card)

    def _on_case_type_changed(self, _text):
        self._refresh_case_context()

    def _refresh_case_context(self):
        case_data = self.case_combo.currentData()
        if case_data == "labor":
            self.labor_notice.setText(self.labor_guard.get_warning_text())
            self.labor_notice.setVisible(True)
        else:
            self.labor_notice.setText("")
            self.labor_notice.setVisible(False)
