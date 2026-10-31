# File: views/widgets.py
# Purpose: Small reusable view components shared across wizard pages
# Encoding: UTF-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from views.theme import (
    CASE_CONTEXT_LABEL,
    CONTENT_MAX_WIDTH,
    DRAFT_ACTION_BAR,
    PAGE_CONTENT_COLUMN,
    PAGE_TITLE_LABEL,
    SECONDARY_BUTTON,
    STEP_CHIP,
    STEP_CONNECTOR,
    STEP_INDICATOR,
)

# The five fixed wizard steps (1-based, shown to the user in Chinese).
STEP_NAMES = ["选择案由", "当事人", "案情与请求", "证据", "核对与导出"]

# Case-type labels used for the persistent case context hint. Kept here so the
# wizard and its pages share a single source instead of duplicating the mapping.
CASE_TYPE_LABELS = {
    "loan": "民间借贷纠纷",
    "contract": "买卖合同纠纷",
    "property": "物业服务合同纠纷",
    "labor": "劳动报酬/工资追索",
    "divorce": "离婚纠纷",
}


def _repolish(widget):
    """Force a widget to re-apply its stylesheet after a dynamic property change."""
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)


def content_column(column_layout, max_width=CONTENT_MAX_WIDTH):
    """Center *column_layout* in a single max-width column.

    Returns the wizard page's top-level layout. That layout still fills the page
    (so the scroll containers and the fixed navigation bar keep working); the
    inner content column takes roughly four fifths of the window width
    (stretch 8 versus 1 for each side stretch) and is capped at ``max_width``.
    This keeps form line lengths readable on wide windows, gives the long claim
    forms enough width at the minimum window size, and keeps the column
    centered. The column widget is tagged with ``PAGE_CONTENT_COLUMN`` so the
    wizard can place the step indicator inside the same column.
    """
    holder = QWidget()
    holder.setObjectName(PAGE_CONTENT_COLUMN)
    holder.setLayout(column_layout)
    holder.setMaximumWidth(max_width)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addStretch(1)
    row.addWidget(holder, 8)
    row.addStretch(1)

    outer = QVBoxLayout()
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addLayout(row)
    return outer


def page_title(text):
    """A wizard page heading rendered inside the centered content column.

    Replaces Qt's full-width ModernStyle banner title so the heading shares the
    same left edge as the form below it.
    """
    label = QLabel(text)
    label.setObjectName(PAGE_TITLE_LABEL)
    return label


class DraftActionBar(QWidget):
    """The 保存草稿 / 打开草稿 actions shown under every wizard page.

    The buttons live in the page's own content column rather than in
    ``QWizard``'s button box: a custom wizard button is owned by an internal
    container that Qt rebuilds on style changes, and holding on to such a
    widget across a window swap corrupted the widget tree in testing. An
    ordinary layout-owned widget follows the same ownership rules as every
    other control in this application.

    The bar carries no behaviour of its own; the wizard re-emits the clicks as
    ``save_draft_requested`` / ``open_draft_requested`` so the presenter only
    has to listen to one pair of signals no matter how many pages exist.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(DRAFT_ACTION_BAR)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.save_button = QPushButton("保存草稿")
        self.save_button.setObjectName(SECONDARY_BUTTON)
        self.save_button.setAccessibleName("保存草稿")
        self.save_button.setAccessibleDescription(
            "将当前填写内容加密保存为本地草稿文件，可稍后继续填写"
        )
        self.open_button = QPushButton("打开草稿")
        self.open_button.setObjectName(SECONDARY_BUTTON)
        self.open_button.setAccessibleName("打开草稿")
        self.open_button.setAccessibleDescription("打开此前保存的本地草稿并继续填写")

        layout.addWidget(self.save_button)
        layout.addWidget(self.open_button)
        layout.addStretch(1)


class StepIndicator(QWidget):
    """A persistent five-step progress strip with a case-context hint.

    The current step is highlighted via the ``stepState`` dynamic property
    (``current`` / ``done`` / ``todo``) matched by the global stylesheet, so no
    colour values appear in the view code itself.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(STEP_INDICATOR)

        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(4)

        self._chips = []
        self._connectors = []
        for index, name in enumerate(STEP_NAMES, start=1):
            if index > 1:
                connector = QLabel()
                connector.setObjectName(STEP_CONNECTOR)
                connector.setProperty("stepState", "todo")
                connector.setFixedSize(12, 2)
                chips_layout.addWidget(connector, 0, Qt.AlignVCenter)
                self._connectors.append(connector)

            chip = QLabel(f"{index} {name}")
            chip.setObjectName(STEP_CHIP)
            chip.setProperty("stepState", "todo")
            chip.setWordWrap(False)
            chips_layout.addWidget(chip)
            self._chips.append(chip)

        self.case_label = QLabel("")
        self.case_label.setObjectName(CASE_CONTEXT_LABEL)
        self.case_label.setWordWrap(True)
        self.case_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)
        layout.addLayout(chips_layout)
        layout.addWidget(self.case_label)

        self._current = 0

    @staticmethod
    def _apply_state(widget, state):
        """Set a widget's ``stepState`` and re-polish on change."""
        if widget.property("stepState") != state:
            widget.setProperty("stepState", state)
            _repolish(widget)

    def set_current(self, index):
        """Highlight step ``index`` (1..5); ``0`` means "not started"."""
        self._current = index
        for position, chip in enumerate(self._chips, start=1):
            if position < index:
                state = "done"
            elif position == index:
                state = "current"
            else:
                state = "todo"
            self._apply_state(chip, state)
            # A completed step swaps its number for a check mark as a clear cue,
            # while the step name stays present for accessibility and tests.
            marker = "✓" if state == "done" else str(position)
            text = f"{marker} {STEP_NAMES[position - 1]}"
            if chip.text() != text:
                chip.setText(text)

        # Connector between step N and N+1 is "done" once step N is completed.
        for position, connector in enumerate(self._connectors, start=1):
            self._apply_state(connector, "done" if position < index else "todo")

    def set_case_label(self, text):
        """Show the current case type, or hide it when empty."""
        self.case_label.setText(text or "")
        self.case_label.setVisible(bool(text))

    def current(self):
        return self._current