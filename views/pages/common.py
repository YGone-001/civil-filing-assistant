# File: views/pages/common.py
# Purpose: Shared wizard-page form, status, validator and layout helpers.
# Encoding: UTF-8
"""Shared, reusable helpers for the wizard page modules.

One implementation each for status-label handling, message de-duplication,
input validators, accessibility naming and the two-column section/scroll
layout construction used by every claim page. Imported by the page modules
and re-exported through the ``views/wizard_pages.py`` compatibility facade.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from views.theme import SECTION_BOX, SPACING_LG, SPACING_MD, SPACING_SM
from views.widgets import content_column

def _set_status(label, text):
    """Set a status label's text and hide it when empty.

    Status labels carry background/border styling, so an empty string would
    otherwise render as a stray coloured box.
    """
    label.setText(text)
    label.setVisible(bool(text))


def _dedup_messages(messages):
    """Remove duplicate messages while preserving order and non-empty values."""
    seen = set()
    result = []
    for msg in messages:
        msg = msg.strip()
        if msg and msg not in seen:
            seen.add(msg)
            result.append(msg)
    return result

# Phone input accepts only digits and the common grouping/prefix characters so
# that obviously invalid text (letters, brackets, etc.) cannot be entered. The
# precise digit-count check happens in PartyPage.validate_parties() so that a
# legitimate landline or extension is not rejected outright.
_PHONE_INPUT_PATTERN = QRegularExpression(r"^[0-9+\-() ]{0,20}$")

# Amount / percentage inputs (元, %, 倍数等) accept a non-negative decimal with up
# to two fraction digits. Empty is allowed so optional fields can stay blank; the
# mandatory check is enforced separately by the ``*`` field marker. Letters and
# leading signs are rejected at the text-entry level.
_DECIMAL_INPUT_PATTERN = QRegularExpression(r"^(?:\d{1,12}(?:\.\d{0,2})?)?$")


def _decimal_validator(line_edit):
    """Restrict ``line_edit`` to non-negative decimals (empty allowed)."""
    line_edit.setValidator(QRegularExpressionValidator(_DECIMAL_INPUT_PATTERN, line_edit))


def _set_label_field_accessibility(label, field, prefix=""):
    """Give a labelled text input an explicit, screen-reader-friendly name.

    Qt does not automatically expose a form label as an accessible name, so the
    label text (without its trailing colon) is copied onto the input, prefixed
    by the party number where applicable.  Shared by every form builder here so
    the convention cannot drift between the party cards and the case-fact grids.
    """
    if not isinstance(label, QLabel) or not isinstance(
        field, (QLineEdit, QTextEdit, QPlainTextEdit)
    ):
        return
    label_text = label.text().replace(":", "").replace("：", "").strip()
    if not label_text:
        return
    name = f"{prefix}{label_text}" if prefix else label_text
    field.setAccessibleName(name)
    field.setAccessibleDescription(f"填写{name}")


def _set_form_accessibility(form, prefix=""):
    """Apply the labelled-input convention to every row of a ``QFormLayout``."""
    for row in range(form.rowCount()):
        label_item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        field_item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
        if label_item is None or field_item is None:
            continue
        _set_label_field_accessibility(label_item.widget(), field_item.widget(), prefix)


def _set_page_form_accessibility(page):
    """Apply the labelled-input convention to every form on a wizard page."""
    for form in page.findChildren(QFormLayout):
        _set_form_accessibility(form)


class _TwoColumnForm:
    """A compact section form that pairs labelled fields two per row.

    It mirrors the ``QFormLayout.addRow`` call pattern used across the case-fact
    pages — ``addRow("标签:", 字段)``, ``addRow("", 说明标签)`` and
    ``addRow(部件)`` all work — but lays two consecutive labelled fields side by
    side so short inputs (dates, amounts, names) do not stretch edge to edge.
    Full-width rows (hints, warnings, button strips) still span the whole grid.

    ``QFormLayout`` cannot expose its label as Qt's accessible name, so this
    grid assigns the accessible name/description itself, using the same
    convention as :func:`_set_label_field_accessibility`.
    """

    _NAMEABLE = (QLineEdit, QTextEdit, QPlainTextEdit)

    def __init__(self, box):
        self.grid = QGridLayout(box)
        self.grid.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_MD)
        self.grid.setHorizontalSpacing(SPACING_LG)
        self.grid.setVerticalSpacing(SPACING_MD)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(3, 1)
        self._row = 0
        self._slot = 0

    @staticmethod
    def _as_widget(obj):
        """Return *obj* as a widget, wrapping a bare layout in a container."""
        if isinstance(obj, QWidget):
            return obj
        holder = QWidget()
        holder.setLayout(obj)
        return holder

    def _add_field(self, label_text, field):
        column = self._slot * 2
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(label, self._row, column)
        self.grid.addWidget(self._as_widget(field), self._row, column + 1)
        if isinstance(field, self._NAMEABLE):
            _set_label_field_accessibility(label, field)
        if self._slot == 1:
            self._row += 1
            self._slot = 0
        else:
            self._slot = 1

    def _add_full(self, widget):
        if self._slot == 1:
            self._row += 1
            self._slot = 0
        self.grid.addWidget(self._as_widget(widget), self._row, 0, 1, 4)
        self._row += 1

    def addRow(self, *args):
        """Add a row, accepting ``(label, field)``, ``("", widget)`` or ``(widget)``."""
        if len(args) == 1:
            self._add_full(args[0])
            return
        label_text, field = args
        if not label_text:
            self._add_full(field)
            return
        self._add_field(label_text, field)


def _section(root, title):
    """Append a titled group box to ``root`` and return its two-column form."""
    box = QGroupBox(title)
    box.setObjectName(SECTION_BOX)
    form = _TwoColumnForm(box)
    root.addWidget(box)
    return form


def _wrap_in_scroll(root_layout):
    """Wrap *root_layout* in a resizable QScrollArea inside the content column.

    Callers do ``self.setLayout(_wrap_in_scroll(root))`` instead of
    ``self.setLayout(root)`` so that long forms stay usable on small screens
    and high-DPI scaling factors.  The scroll area is placed inside the shared
    centered content column, so the form keeps a readable line length on wide
    windows while still scrolling when the window is short.
    """
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    # Keep the section boxes at their natural height: without a trailing
    # stretch the last group box would grow to absorb the leftover space and
    # render as a tall, mostly empty panel.
    root_layout.addStretch(1)
    content = QWidget()
    content.setLayout(root_layout)
    scroll.setWidget(content)

    column = QVBoxLayout()
    column.setContentsMargins(0, 0, 0, 0)
    column.addWidget(scroll)
    return content_column(column)
