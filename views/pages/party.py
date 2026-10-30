# File: views/pages/party.py
# Purpose: Dynamic plaintiff/defendant management page.
# Encoding: UTF-8
"""Dynamic party cards (add/delete/renumber, person/company toggle,
progressive validation and accessible naming) backing the party page."""

import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from views.theme import (
    DANGER_BUTTON,
    ERROR_LABEL,
    REMINDER_LABEL,
    SECONDARY_BUTTON,
    SECTION_LABEL,
    SPACING_LG,
    SPACING_MD,
)
from views.widgets import content_column
from views.pages.base import _TitledPage
from views.pages.common import (
    _PHONE_INPUT_PATTERN,
    _dedup_messages,
    _set_label_field_accessibility,
    _set_status,
)

class PartyPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写当事人信息")

        main_layout = QVBoxLayout()

        # Live validation / guidance message for the party list.
        self.msg_label = QLabel("")
        self.msg_label.setObjectName(ERROR_LABEL)
        self.msg_label.setWordWrap(True)
        self.msg_label.setVisible(False)
        main_layout.addWidget(self.msg_label)

        # Setup Scroll Area for dynamic lists
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        # Containers for dynamic fields
        self.plaintiff_widgets = []
        self.defendant_widgets = []

        # Store credit_code_edit and legal_rep_edit as instance variables
        self.credit_code_edit = None
        self.legal_rep_edit = None

        # Store current case type
        self.current_case_type = None

        # Flag to prevent multiple initialization
        self.is_initialized = False

        # Progressive validation: nothing is flagged until the user interacts
        # (leaves a field or clicks Next); reset on each fresh entry.
        self._touched = False

        # Plaintiff section heading
        self.plaintiff_section_label = QLabel("原告")
        self.plaintiff_section_label.setObjectName(SECTION_LABEL)
        self.scroll_layout.addWidget(self.plaintiff_section_label)

        # Add Plaintiff Button (kept to its content width instead of stretching
        # full width, so it reads as an inline action rather than a panel).
        self.add_p_btn = QPushButton("添加原告")
        self.add_p_btn.setObjectName(SECONDARY_BUTTON)
        self.add_p_btn.setAccessibleName("添加原告")
        self.add_p_btn.setAccessibleDescription("添加一名原告当事人卡片")
        self.add_p_btn.clicked.connect(lambda: self.add_party_ui(0))
        self._add_p_row = self._button_row(self.add_p_btn)
        self.scroll_layout.addWidget(self._add_p_row)

        # Defendant section heading
        self.defendant_section_label = QLabel("被告")
        self.defendant_section_label.setObjectName(SECTION_LABEL)
        self.scroll_layout.addWidget(self.defendant_section_label)

        # Add Defendant Button
        self.add_d_btn = QPushButton("添加被告")
        self.add_d_btn.setObjectName(SECONDARY_BUTTON)
        self.add_d_btn.setAccessibleName("添加被告")
        self.add_d_btn.setAccessibleDescription("添加一名被告当事人卡片")
        self.add_d_btn.clicked.connect(lambda: self.add_party_ui(1))
        self._add_d_row = self._button_row(self.add_d_btn)
        self.scroll_layout.addWidget(self._add_d_row)

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(content_column(main_layout))

    def initializePage(self):
        """Called when the page is shown, recreate UI based on selected case type"""
        case_type = self.field("case_type")

        # Only recreate UI if case type has changed or not initialized yet
        if self.is_initialized and self.current_case_type == case_type:
            return

        # Clear existing widgets if they exist
        for widget in self.plaintiff_widgets:
            widget["group"].deleteLater()
        for widget in self.defendant_widgets:
            widget["group"].deleteLater()

        self.plaintiff_widgets.clear()
        self.defendant_widgets.clear()

        # Update current case type
        self.current_case_type = case_type
        self.is_initialized = True

        # Fresh entry: hide any previously shown errors until interaction.
        self._touched = False

        # Initialize with at least 1 plaintiff and 1 defendant
        self.add_party_ui(0)
        self.add_party_ui(1)
        self._rebuild_party_tab_order()

    @staticmethod
    def _button_row(button):
        """Wrap *button* in a left-aligned row so it keeps its content width."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(button)
        layout.addStretch(1)
        return row

    @staticmethod
    def _apply_field_names(name_fields, prefix):
        """(Re)apply numbered accessible names to a card's labelled inputs."""
        for label, field in name_fields:
            _set_label_field_accessibility(label, field, prefix)

    def add_party_ui(self, party_type):
        is_plaintiff = (party_type == 0)
        kind = "原告" if is_plaintiff else "被告"
        number = (len(self.plaintiff_widgets) + 1) if is_plaintiff else (len(self.defendant_widgets) + 1)

        group = QGroupBox(f"{kind}{number}")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(SPACING_MD)

        name_edit = QLineEdit()
        id_edit = QLineEdit()
        addr_edit = QLineEdit()
        phone_edit = QLineEdit()

        from PySide6.QtWidgets import QCheckBox
        is_company_check = QCheckBox("该当事人为单位/企业（非自然人）")
        is_company_check.setChecked(False)

        # Company-specific widgets are always created so that a corporate party
        # works for every case type and the extraction code never touches a
        # ``None`` widget. They stay hidden until the toggle is switched.
        credit_code_edit = QLineEdit()
        credit_code_edit.setPlaceholderText("统一社会信用代码")
        credit_code_edit.setVisible(False)

        legal_rep_edit = QLineEdit()
        legal_rep_edit.setPlaceholderText("法定代表人姓名")
        legal_rep_edit.setVisible(False)

        # Per-card delete action, pinned to the card's top-right corner so it is
        # no longer a full-width click target sitting next to the input fields.
        delete_btn = QPushButton("删除")
        delete_btn.setObjectName(DANGER_BUTTON)
        delete_btn.setAccessibleName(f"删除{kind}卡片")

        header = QHBoxLayout()
        header.addWidget(is_company_check)
        header.addStretch(1)
        header.addWidget(delete_btn)
        group_layout.addLayout(header)

        # Two-column field grid: the identity and contact pairs each share a row
        # so the card stays compact instead of stacking six single-column rows.
        name_label = QLabel("姓名/名称:")
        id_label = QLabel("身份证号:")
        credit_code_label = QLabel("统一社会信用代码:")
        legal_rep_label = QLabel("法定代表人:")
        addr_label = QLabel("住址/住所地:")
        phone_label = QLabel("电话:")
        for label in (name_label, id_label, credit_code_label, legal_rep_label,
                      addr_label, phone_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING_LG)
        grid.setVerticalSpacing(SPACING_MD)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # Personal mode: 姓名 | 身份证号, then 住址 | 电话.
        grid.addWidget(name_label, 0, 0)
        grid.addWidget(name_edit, 0, 1)
        grid.addWidget(id_label, 0, 2)
        grid.addWidget(id_edit, 0, 3)
        grid.addWidget(addr_label, 1, 0)
        grid.addWidget(addr_edit, 1, 1)
        grid.addWidget(phone_label, 1, 2)
        grid.addWidget(phone_edit, 1, 3)
        # Company mode adds a third row that collapses while every cell is hidden.
        grid.addWidget(credit_code_label, 2, 0)
        grid.addWidget(credit_code_edit, 2, 1)
        grid.addWidget(legal_rep_label, 2, 2)
        grid.addWidget(legal_rep_edit, 2, 3)
        group_layout.addLayout(grid)

        phone_validator = QRegularExpressionValidator(_PHONE_INPUT_PATTERN)
        phone_edit.setValidator(phone_validator)

        case_type = self.field("case_type")
        is_property_case = (case_type == "property")

        # Only create addr_hint for property cases
        if is_property_case and not is_plaintiff:
            addr_hint = QLabel("提示：若被告搬家，请填写现居住满一年的地址，以便法院送达。")
            addr_hint.setObjectName(REMINDER_LABEL)
            addr_hint.setWordWrap(True)
            group_layout.addWidget(addr_hint)

        # 个人/企业 toggle. Toggling swaps the personal ID field for the company
        # credit-code / legal-representative fields; each caption travels with
        # its field so no dangling identity label is ever left behind.
        is_company_check.toggled.connect(
            lambda checked: self._toggle_company_fields(
                checked,
                id_edit,
                credit_code_edit,
                legal_rep_edit,
                id_label,
                credit_code_label,
                legal_rep_label,
            )
        )

        name_fields = [
            (name_label, name_edit),
            (id_label, id_edit),
            (credit_code_label, credit_code_edit),
            (legal_rep_label, legal_rep_edit),
            (addr_label, addr_edit),
            (phone_label, phone_edit),
        ]

        widget = {
            "group": group,
            "name": name_edit,
            "id": id_edit,
            "addr": addr_edit,
            "phone": phone_edit,
            "is_company": is_company_check,
            "credit_code": credit_code_edit,
            "legal_rep": legal_rep_edit,
            "id_label": id_label,
            "credit_code_label": credit_code_label,
            "legal_rep_label": legal_rep_label,
            "delete_btn": delete_btn,
            "name_fields": name_fields,
        }
        delete_btn.clicked.connect(lambda _=False, t=party_type, d=widget: self._remove_party(t, d))

        # Insert the card above its side's add button.
        if is_plaintiff:
            insert_idx = self.scroll_layout.indexOf(self._add_p_row)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.plaintiff_widgets.append(widget)
        else:
            insert_idx = self.scroll_layout.indexOf(self._add_d_row)
            self.scroll_layout.insertWidget(insert_idx, group)
            self.defendant_widgets.append(widget)

        # Apply the initial natural-person state to both fields and labels.
        self._toggle_company_fields(
            False,
            id_edit,
            credit_code_edit,
            legal_rep_edit,
            id_label,
            credit_code_label,
            legal_rep_label,
        )
        self._apply_field_names(name_fields, f"{kind}{number}")

        # Keep the live guidance and the wizard "Next" button state in sync, and
        # mark the page as touched when the user leaves a field.
        for w in (name_edit, phone_edit, credit_code_edit, legal_rep_edit):
            w.textChanged.connect(lambda _text: self._refresh_validation_message())
            w.editingFinished.connect(self._on_field_edited)

        self._refresh_validation_message()
        self._rebuild_party_tab_order()

    def _toggle_company_fields(
        self,
        checked,
        id_edit,
        credit_code_edit,
        legal_rep_edit,
        id_label,
        credit_code_label,
        legal_rep_label,
    ):
        if id_edit is not None:
            id_edit.setVisible(not checked)
        if id_label is not None:
            id_label.setVisible(not checked)
        if credit_code_edit is not None:
            credit_code_edit.setVisible(checked)
        if credit_code_label is not None:
            credit_code_label.setVisible(checked)
        if legal_rep_edit is not None:
            legal_rep_edit.setVisible(checked)
        if legal_rep_label is not None:
            legal_rep_label.setVisible(checked)
        self._refresh_validation_message()

    def _renumber_parties(self):
        """Keep card numbers contiguous after additions/removals."""
        for idx, w in enumerate(self.plaintiff_widgets, 1):
            w["group"].setTitle(f"原告{idx}")
            self._apply_field_names(w["name_fields"], f"原告{idx}")
        for idx, w in enumerate(self.defendant_widgets, 1):
            w["group"].setTitle(f"被告{idx}")
            self._apply_field_names(w["name_fields"], f"被告{idx}")

    def _rebuild_party_tab_order(self):
        """Keep keyboard traversal aligned with the visible party-card order."""
        sequence = []
        for card in self.plaintiff_widgets:
            sequence.extend(
                card[key]
                for key in ("name", "id", "credit_code", "legal_rep", "addr", "phone",
                            "is_company", "delete_btn")
            )
        sequence.append(self.add_p_btn)
        for card in self.defendant_widgets:
            sequence.extend(
                card[key]
                for key in ("name", "id", "credit_code", "legal_rep", "addr", "phone",
                            "is_company", "delete_btn")
            )
        sequence.append(self.add_d_btn)
        for previous, following in zip(sequence, sequence[1:]):
            QWidget.setTabOrder(previous, following)

    def _remove_party(self, party_type, widget):
        widgets = self.plaintiff_widgets if party_type == 0 else self.defendant_widgets
        try:
            widgets.remove(widget)
        except ValueError:
            return
        widget["group"].deleteLater()
        self._renumber_parties()
        self._rebuild_party_tab_order()
        self._refresh_validation_message()

    def remove_party_ui(self, party_type, index):
        """Remove the party card at ``index`` (0-based) for tests and scripts."""
        widgets = self.plaintiff_widgets if party_type == 0 else self.defendant_widgets
        if 0 <= index < len(widgets):
            self._remove_party(party_type, widgets[index])

    @staticmethod
    def _widget_text(widget):
        """Safely read a widget's text, returning ``""`` for missing widgets."""
        return widget.text() if widget is not None else ""

    def _iter_parties(self):
        """Yield ``(kind, index, widgets)`` for every plaintiff and defendant."""
        for idx, w in enumerate(self.plaintiff_widgets, 1):
            yield "原告", idx, w
        for idx, w in enumerate(self.defendant_widgets, 1):
            yield "被告", idx, w

    def _has_named_party(self, widgets):
        return any(self._widget_text(w["name"]).strip() for w in widgets)

    def isComplete(self):
        """Require at least one named plaintiff and one named defendant.

        ``validatePage`` additionally blocks an explicitly added empty card,
        preventing the model builder from silently skipping that party.
        """
        return (
            self._has_named_party(self.plaintiff_widgets)
            and self._has_named_party(self.defendant_widgets)
        )

    def validate_parties(self):
        """Return a list of human-readable party-input issues.

        Each empty party card yields exactly one "不能为空" message (no
        side-level duplicate), so the summary is de-duplicated. Softer format
        warnings (phone length or unified social credit code) follow and only
        advise — they never block generation.
        """
        issues = []

        # A side-level message only when a side has no card left at all (e.g.
        # every card was deleted). Otherwise per-card messages below cover it,
        # so a normal blank card never produces a duplicated side-level warning.
        if not self.plaintiff_widgets:
            issues.append("请至少填写一名原告的姓名/名称。")
        if not self.defendant_widgets:
            issues.append("请至少填写一名被告的姓名/名称。")

        for kind, idx, w in self._iter_parties():
            name = self._widget_text(w["name"]).strip()
            if not name:
                issues.append(f"{kind}{idx}的姓名/名称不能为空。")
                continue

            phone = self._widget_text(w["phone"]).strip()
            if phone:
                digits = re.sub(r"\D", "", phone)
                if not 7 <= len(digits) <= 15:
                    issues.append(f"{kind}{idx}“{name}”的电话号码位数可能不正确，建议核对（仅提示，不阻止生成）。")

            if w["is_company"].isChecked():
                code = self._widget_text(w["credit_code"]).strip()
                if code and not re.fullmatch(r"[0-9A-HJ-NPQRTUWXY]{18}", code):
                    issues.append(f"{kind}{idx}“{name}”的统一社会信用代码格式可能不正确，建议核对（仅提示，不阻止生成）。")

        return issues

    def _refresh_validation_message(self):
        issues = _dedup_messages(self.validate_parties())
        # Progressive validation: nothing is shown until the page is touched.
        _set_status(self.msg_label, "\n".join(issues) if self._touched else "")
        # Notify the wizard so the "Next" button reflects the current state.
        self.completeChanged.emit()

    def _on_field_edited(self):
        """Mark the page touched when a field loses focus, then refresh errors."""
        self._touched = True
        self._refresh_validation_message()

    def _first_invalid_name_widget(self):
        """Return the first empty name field (the one that blocks the page)."""
        for w in self.plaintiff_widgets + self.defendant_widgets:
            if not self._widget_text(w["name"]).strip():
                return w["name"]
        return None

    def _has_missing_party_name(self):
        """Return whether any existing party card lacks its required name."""
        return any(
            not self._widget_text(w["name"]).strip()
            for w in self.plaintiff_widgets + self.defendant_widgets
        )

    def focus_first_invalid(self):
        """Move focus to the first blocking field; return whether it existed."""
        widget = self._first_invalid_name_widget()
        if widget is not None:
            widget.setFocus()
            return True
        return False

    def validatePage(self):
        """Run on Next: reveal errors, focus the first invalid field, and block
        navigation while the page is incomplete."""
        self._touched = True
        issues = _dedup_messages(self.validate_parties())
        _set_status(self.msg_label, "\n".join(issues))
        self.focus_first_invalid()
        # ``isComplete`` keeps the standard QWizard button state responsive
        # once each side has a named party. A deliberately added but blank
        # extra card must still block the transition here; otherwise the model
        # builder would silently skip it during export.
        return self.isComplete() and not self._has_missing_party_name()

    def get_party_data(self):
        """Extract all party data to pass to presenter.

        Company-specific widgets are always present, but extraction is written
        defensively so that an absent widget can never raise.
        """
        def build(widgets):
            result = []
            for w in widgets:
                result.append({
                    "name": self._widget_text(w["name"]),
                    "id_number": self._widget_text(w["id"]),
                    "address": self._widget_text(w["addr"]),
                    "phone": self._widget_text(w["phone"]),
                    "is_company": w["is_company"].isChecked(),
                    "credit_code": self._widget_text(w["credit_code"]),
                    "legal_representative": self._widget_text(w["legal_rep"]),
                })
            return result

        return {
            "plaintiffs": build(self.plaintiff_widgets),
            "defendants": build(self.defendant_widgets),
        }
