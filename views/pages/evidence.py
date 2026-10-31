# File: views/pages/evidence.py
# Purpose: Evidence table page (per-category suggestions and state machine).
# Encoding: UTF-8
"""Evidence management: per-category suggestion loading, stashed rows across
category switches, the four-state per-case evidence state machine and item
data based suggested-row markers."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from views.theme import COLOR_SUGGESTED_ROW_BG, DANGER_BUTTON, INFO_LABEL, SECONDARY_BUTTON
from views.widgets import content_column
from views.pages.base import _TitledPage

class EvidencePage(_TitledPage):
    # A faint background tint for rows loaded from EvidenceLibrary so the user
    # can tell suggested evidence apart from rows they added themselves.  The
    # tint is purely visual — get_evidence_items() returns the same structure.
    _SUGGESTED_TINT = QBrush(QColor(COLOR_SUGGESTED_ROW_BG))

    def __init__(self):
        super().__init__()
        self.set_page_title("证据清单（选填）")

        layout = QVBoxLayout()
        self.desc_label = QLabel("请列出您准备提交的证据。")
        layout.addWidget(self.desc_label)

        self.edit_hint = QLabel("双击任意单元格即可编辑证据名称或证明目的。")
        self.edit_hint.setObjectName(INFO_LABEL)
        self.edit_hint.setWordWrap(True)
        layout.addWidget(self.edit_hint)

        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("添加证据")
        self.add_row_btn.setObjectName(SECONDARY_BUTTON)
        self.add_row_btn.setAccessibleName("添加证据行")
        self.add_row_btn.clicked.connect(self.add_row)
        self.remove_row_btn = QPushButton("删除选中行")
        self.remove_row_btn.setObjectName(DANGER_BUTTON)
        self.remove_row_btn.setAccessibleName("删除选中的证据行")
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.remove_row_btn)
        btn_layout.addStretch(1)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        layout.addWidget(btn_widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["证据名称", "证明目的"])
        # Comfortable row density and zebra striping keep multi-row evidence
        # lists scannable; both are presentation-only.
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setAlternatingRowColors(True)
        self.table.setAccessibleName("证据清单表格")
        self.table.setAccessibleDescription("可编辑表格，双击单元格编辑证据名称和证明目的")
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked | QTableWidget.EditTrigger.EditKeyPressed)
        layout.addWidget(self.table)

        # Number of rows that came from EvidenceLibrary suggestions.  Rows beyond
        # this count were added by the user and are not tinted.  The count is
        # maintained from per-item suggested flags, so it stays correct after
        # arbitrary deletion and insertion.
        self._suggested_count = 0

        # Per-category evidence state.  Rows are stashed when the user switches
        # category and restored verbatim when they switch back, all in memory:
        #   NOT_INITIALIZED              -> the category was never shown
        #   INITIALIZED_WITH_SUGGESTIONS -> only library suggestions are present
        #   USER_MODIFIED                -> the user kept/edited/added rows
        #   USER_EXPLICITLY_CLEARED      -> the user deleted every row
        self.NOT_INITIALIZED = "NOT_INITIALIZED"
        self.INITIALIZED_WITH_SUGGESTIONS = "INITIALIZED_WITH_SUGGESTIONS"
        self.USER_MODIFIED = "USER_MODIFIED"
        self.USER_EXPLICITLY_CLEARED = "USER_EXPLICITLY_CLEARED"
        self._loaded_case_type = None
        self._stashed_rows = {}
        self._case_state = {}
        self._loading_rows = False
        self.table.itemChanged.connect(self._on_item_changed)

        self.setLayout(content_column(layout))

    def initializePage(self):
        super().initializePage()
        try:
            case_type = self.wizard().field("case_type")
            if case_type == self._loaded_case_type:
                # Same-category re-entry (e.g. Back then Next): keep the rows
                # exactly as they are, so a deliberately emptied list stays
                # empty and user edits are never restored over.
                return
            if self._loaded_case_type is not None:
                # Switching category: stash the current rows under their own
                # category so nothing leaks into the new one and edits remain
                # recoverable when the user switches back this session.
                self._stashed_rows[self._loaded_case_type] = self._collect_rows()
            self._load_case_evidence(case_type)
        except Exception:
            return

    def _set_case_description(self, case_type):
        if case_type == "contract":
            self.desc_label.setText("买卖合同纠纷常见证据（可按需修改/增删）：")
        elif case_type == "loan":
            self.desc_label.setText("民间借贷纠纷常见证据（可按需修改/增删）：")
        elif case_type == "property":
            self.desc_label.setText("物业服务合同纠纷常见证据（可按需修改/增删）：")
        elif case_type == "labor":
            self.desc_label.setText("劳动报酬/工资追索常见证据（可按需修改/增删）：")
        elif case_type == "divorce":
            self.desc_label.setText("离婚纠纷常见证据（可按需修改/增删）：")
        else:
            self.desc_label.setText("常见证据（可按需修改/增删）：")

    def _load_case_evidence(self, case_type):
        """(Re)load the evidence table for *case_type*.

        Previously stashed rows for the category are restored verbatim
        (including their suggested/user markers); on first visit the category's
        library suggestions are loaded. Rows from another category are never
        carried over.
        """
        from utils.evidence_library import EvidenceLibrary

        self._loading_rows = True
        try:
            self._loaded_case_type = case_type
            self.table.setRowCount(0)
            self._suggested_count = 0
            self._set_case_description(case_type)
            stashed = self._stashed_rows.get(case_type)
            if stashed is not None:
                for name, target, suggested in stashed:
                    self.add_row(name, target, suggested=suggested, auto_edit=False)
                self._case_state[case_type] = (
                    self.USER_EXPLICITLY_CLEARED if not stashed else self.USER_MODIFIED
                )
                return
            for name, target in EvidenceLibrary.get_default_evidence(case_type):
                self.add_row(name, target, suggested=True, auto_edit=False)
            self._case_state[case_type] = (
                self.INITIALIZED_WITH_SUGGESTIONS if self.table.rowCount() else self.NOT_INITIALIZED
            )
        finally:
            self._loading_rows = False

    def _is_suggested_row(self, row):
        item = self.table.item(row, 0)
        return bool(item is not None and item.data(Qt.ItemDataRole.UserRole))

    def _collect_rows(self):
        """Snapshot the table as ``(name, target, suggested)`` tuples."""
        rows = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            target_item = self.table.item(r, 1)
            name = name_item.text() if name_item else ""
            target = target_item.text() if target_item else ""
            rows.append((name, target, self._is_suggested_row(r)))
        return rows

    def _on_item_changed(self, *_):
        if self._loading_rows:
            return
        self._refresh_state_after_edit()

    def _refresh_state_after_edit(self):
        """Record user interaction with the current category's evidence list."""
        if self._loaded_case_type is None:
            return
        if self.table.rowCount() == 0:
            self._case_state[self._loaded_case_type] = self.USER_EXPLICITLY_CLEARED
        else:
            self._case_state[self._loaded_case_type] = self.USER_MODIFIED

    def get_case_state(self, case_type=None):
        """Return the recorded evidence state for a category (tests/introspection)."""
        return self._case_state.get(case_type or self._loaded_case_type)

    def clear_all_rows(self):
        """Remove every row (new-case/demo entry) and record the cleared state."""
        self.table.setRowCount(0)
        self._suggested_count = 0
        if self._loaded_case_type is not None:
            self._case_state[self._loaded_case_type] = self.USER_EXPLICITLY_CLEARED

    def add_row(self, name="", target="", suggested=False, auto_edit=True):
        """Append a row and optionally start editing the first cell.

        ``suggested=True`` tints the row (and flags it as suggested via item
        data, so the marker survives arbitrary deletions) so the user can
        distinguish EvidenceLibrary defaults from rows they added.
        ``auto_edit=True`` puts the cursor straight into the first cell so the
        user can type without a second click.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(str(name))
        target_item = QTableWidgetItem(str(target))
        if suggested:
            name_item.setData(Qt.ItemDataRole.UserRole, True)
            name_item.setBackground(self._SUGGESTED_TINT)
            target_item.setBackground(self._SUGGESTED_TINT)
            self._suggested_count += 1
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, target_item)
        if auto_edit and not suggested:
            self.table.setCurrentItem(name_item)
            self.table.editItem(name_item)
        if not self._loading_rows:
            self._refresh_state_after_edit()

    def remove_selected_rows(self):
        """Remove selected rows, confirming only when content would be lost."""
        from PySide6.QtWidgets import QMessageBox

        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            return

        has_content = False
        for r in rows:
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and item.text().strip():
                    has_content = True
                    break
            if has_content:
                break

        if has_content:
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"将删除 {len(rows)} 行证据，确定吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        removed_suggested = 0
        for r in rows:
            if self._is_suggested_row(r):
                removed_suggested += 1
            self.table.removeRow(r)
        self._suggested_count = max(0, self._suggested_count - removed_suggested)
        if not self._loading_rows:
            self._refresh_state_after_edit()

    def get_evidence_items(self):
        items = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            target_item = self.table.item(r, 1)
            name = name_item.text().strip() if name_item else ""
            target = target_item.text().strip() if target_item else ""
            if name or target:
                items.append((name, target))
        return items

    # ------------------------------------------------------------------ #
    # Draft snapshot / restore
    # ------------------------------------------------------------------ #

    def has_user_evidence(self):
        """Read-only: does any category hold user-modified evidence state?

        Every mutation path (``add_row``, ``remove_selected_rows``,
        ``itemChanged``) already records ``USER_MODIFIED`` or
        ``USER_EXPLICITLY_CLEARED`` for the category it happened in, and the
        record survives a category switch. Reading those records answers "has
        the user touched evidence at all?" without loading, initialising or
        re-stashing anything - a plain library-suggestion page stays
        ``INITIALIZED_WITH_SUGGESTIONS`` and is not user input.

        Deliberately does not consult ``_stashed_rows``: rows are only stashed
        when a category is left, and the state they belong to was recorded when
        they were edited.
        """
        for state in self._case_state.values():
            if state in (self.USER_MODIFIED, self.USER_EXPLICITLY_CLEARED):
                return True
        return False

    def snapshot_evidence(self, case_type):
        """Return the ``{state, rows}`` record to persist for *case_type*.

        The state label is persisted alongside the rows because "no rows" is
        ambiguous on its own: a deliberately emptied list, an untouched page
        and a page that still holds its library suggestions all render as an
        empty table in some situations but must be restored differently.

        Rows belonging to a *different* category are never reported: switching
        the case type without visiting this page again leaves the previous
        category's rows in the table, and those must not travel into the new
        case's draft.
        """
        if self._loaded_case_type != case_type:
            return {"state": self.NOT_INITIALIZED, "rows": []}
        rows = [
            {"name": name, "target": target, "suggested": suggested}
            for name, target, suggested in self._collect_rows()
        ]
        return {
            "state": self._case_state.get(case_type, self.NOT_INITIALIZED),
            "rows": rows,
        }

    def restore_evidence(self, case_type, state, rows):
        """Replace the table with a restored snapshot.

        This is the inverse of :meth:`snapshot_evidence` and deliberately does
        *not* go through :meth:`initializePage`: a restored empty list must stay
        empty instead of being repopulated with library suggestions. Recording
        ``_loaded_case_type`` makes the next ``initializePage()`` a no-op for
        the restored category, exactly like a same-category re-entry.

        The one exception is the "never opened" state: a page the user never
        visited is left unloaded, so opening it for the first time still shows
        that category's suggestions, exactly as in a fresh session.
        """
        self._loading_rows = True
        try:
            self._stashed_rows = {}
            self.table.setRowCount(0)
            self._suggested_count = 0
            self._set_case_description(case_type)
            if state == self.NOT_INITIALIZED and not rows:
                self._loaded_case_type = None
                self._case_state.pop(case_type, None)
                return
            self._loaded_case_type = case_type
            for row in rows:
                self.add_row(
                    row["name"], row["target"], suggested=row["suggested"], auto_edit=False
                )
            self._case_state[case_type] = state
        finally:
            self._loading_rows = False
