# File: views/widgets.py
# Purpose: Small reusable view components shared across wizard pages
# Encoding: UTF-8

from PySide6.QtCore import QDate, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.validation import DateStatus, parse_full_date
from views.theme import (
    CASE_CONTEXT_LABEL,
    COLOR_PRIMARY,
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
    "rental": "租赁合同纠纷",
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


def _calendar_icon():
    """A small, theme-coloured calendar glyph for the date action.

    Qt ships no standard calendar icon, so the glyph is painted in memory. It
    keeps the date affordance visually consistent with the application's single
    primary accent instead of introducing an unrelated stock icon.
    """
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(COLOR_PRIMARY))
    pen.setWidthF(1.3)
    painter.setPen(pen)
    painter.drawRoundedRect(2, 3, 12, 11, 2, 2)
    painter.drawLine(2, 6, 14, 6)
    painter.drawLine(5, 2, 5, 4)
    painter.drawLine(11, 2, 11, 4)
    painter.end()
    return QIcon(pixmap)


class _CalendarPopup(QCalendarWidget):
    """A lightweight popup calendar that reports the chosen date."""

    date_selected = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.clicked.connect(self._choose)

    def _choose(self, date):
        if date.isValid():
            self.date_selected.emit(date)
        self.hide()


class DateLineEdit(QLineEdit):
    """A text date field with a calendar popup.

    Drafts, wizard fields and the draft adapter all read and write plain text,
    so this remains a ``QLineEdit`` rather than a ``QDateEdit``. The calendar
    only offers dates; the text stays editable and keeps being validated by the
    shared full-date parser, which preserves the existing error messages.
    """

    def __init__(self, parent=None, restrict_future=False):
        super().__init__(parent)
        self._restrict_future = bool(restrict_future)
        self._popup = None
        self._calendar_action = self.addAction(
            _calendar_icon(), QLineEdit.ActionPosition.TrailingPosition
        )
        self._calendar_action.setText("选择日期")
        self._calendar_action.setToolTip("选择日期")
        self._calendar_action.triggered.connect(self._open_calendar)

    def restrict_future(self):
        """Return whether the popup refuses dates after today."""
        return self._restrict_future

    def _ensure_calendar_popup(self):
        if self._popup is None:
            popup = _CalendarPopup(self)
            popup.date_selected.connect(self._apply_calendar_date)
            self._popup = popup
        if self._restrict_future:
            self._popup.setMaximumDate(QDate.currentDate())
        return self._popup

    def _apply_calendar_date(self, date):
        if date.isValid():
            self.setText(date.toString("yyyy-MM-dd"))

    def _open_calendar(self):
        popup = self._ensure_calendar_popup()
        validation = parse_full_date(self.text())
        if validation.status == DateStatus.VALID and validation.value is not None:
            value = validation.value
            popup.setSelectedDate(QDate(value.year, value.month, value.day))
        else:
            selected = QDate.currentDate()
            if self._restrict_future:
                selected = min(selected, popup.maximumDate())
            popup.setSelectedDate(selected)

        # Prefer opening below the field, but keep the popup inside the screen
        # and flip it above when the field is near the bottom edge.
        popup.adjustSize()
        position = self.mapToGlobal(QPoint(0, self.height()))
        screen = QApplication.screenAt(position)
        if screen is not None:
            available = screen.availableGeometry()
            size = popup.sizeHint()
            x = min(max(position.x(), available.left()),
                    available.right() - size.width())
            y = position.y()
            if y + size.height() > available.bottom():
                y = self.mapToGlobal(QPoint(0, 0)).y() - size.height()
            position = QPoint(x, y)
        popup.move(position)
        popup.show()

    def hideEvent(self, event):
        if self._popup is not None:
            self._popup.hide()
        super().hideEvent(event)


class DraftActionBar(QWidget):
    """The 使用说明 / 保存草稿 / 打开草稿 actions shown under every wizard page.

    The buttons live in the page's own content column rather than in
    ``QWizard``'s button box: a custom wizard button is owned by an internal
    container that Qt rebuilds on style changes, and holding on to such a
    widget across a window swap corrupted the widget tree in testing. An
    ordinary layout-owned widget follows the same ownership rules as every
    other control in this application.

    The bar carries no behaviour of its own; the wizard re-emits the draft
    clicks as ``save_draft_requested`` / ``open_draft_requested`` and opens the
    usage guide from ``help_requested``, so the presenter only has to listen to
    one pair of signals no matter how many pages exist.
    """

    help_requested = Signal()

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
        self.help_button = QPushButton("使用说明")
        self.help_button.setObjectName(SECONDARY_BUTTON)
        self.help_button.setAccessibleName("使用说明")
        self.help_button.setAccessibleDescription("查看填写顺序、核对要点与免责声明")
        self.help_button.clicked.connect(self.help_requested.emit)

        layout.addWidget(self.save_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.help_button)
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