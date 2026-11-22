# File: views/pages/party.py
# Purpose: Dynamic plaintiff/defendant management page.
# Encoding: UTF-8
"""Dynamic party cards (add/delete/renumber, person/company toggle,
progressive validation and accessible naming) backing the party page."""

import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
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
from models.case_model import AGENT_TYPES
from models.validation import DateStatus, parse_full_date
from views.theme import (
    DANGER_BUTTON,
    ERROR_LABEL,
    PARTY_CARD,
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

#: Ethnicity options for the natural-person party cards (56 recognised groups
#: plus a free-text "其他" companion), mirroring the historical generator.
ETHNICITY_OTHER = "其他"
ETHNICITY_OPTIONS = (
    "汉", "蒙古", "回", "藏", "维吾尔", "苗", "彝", "壮", "布依", "朝鲜",
    "满", "侗", "瑶", "白", "土家", "哈尼", "哈萨克", "傣", "黎", "傈僳",
    "佤", "畲", "高山", "拉祜", "水", "东乡", "纳西", "景颇", "柯尔克孜",
    "土", "达斡尔", "仫佬", "羌", "布朗", "撒拉", "毛南", "仡佬", "锡伯",
    "阿昌", "普米", "塔吉克", "怒", "乌孜别克", "俄罗斯", "鄂温克", "德昂",
    "保安", "裕固", "京", "塔塔尔", "独龙", "鄂伦春", "赫哲", "门巴",
    "珞巴", "基诺", ETHNICITY_OTHER,
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

        self._build_agent_section()

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(content_column(main_layout))

    def initializePage(self):
        """Create the first cards once; later visits keep every entered party.

        Parties do not depend on the case category, so switching the category
        and coming back must never discard them. Only the property-specific
        defendant address hint follows the current category.
        """
        case_type = self.field("case_type")
        self.current_case_type = case_type
        self._update_case_hints()

        if self.is_initialized:
            return
        self.is_initialized = True

        # Fresh entry: hide any previously shown errors until interaction.
        self._touched = False

        # Initialize with at least 1 plaintiff and 1 defendant
        self.add_party_ui(0)
        self.add_party_ui(1)
        self._rebuild_party_tab_order()

    def _update_case_hints(self):
        """Show the moved-defendant address hint only for property cases."""
        show = self.current_case_type == "property"
        for widget in self.defendant_widgets:
            widget["addr_hint"].setVisible(show)

    def _build_agent_section(self):
        """Build the optional litigation-agent section below the party lists.

        The section stays hidden until the user asks for it; ``get_agent_data``
        reports ``None`` while it is closed so a never-opened section is
        indistinguishable from "no agent" in the draft payload.
        """
        self.agent_section_label = QLabel("诉讼代理人（可选）")
        self.agent_section_label.setObjectName(SECTION_LABEL)
        self.scroll_layout.addWidget(self.agent_section_label)

        self.agent_toggle_btn = QPushButton("添加代理人")
        self.agent_toggle_btn.setObjectName(SECONDARY_BUTTON)
        self.agent_toggle_btn.setAccessibleName("添加代理人")
        self.agent_toggle_btn.setAccessibleDescription("添加或移除诉讼代理人信息")
        self.agent_toggle_btn.clicked.connect(self._toggle_agent_section)
        self._agent_toggle_row = self._button_row(self.agent_toggle_btn)
        self.scroll_layout.addWidget(self._agent_toggle_row)

        self.agent_frame = QGroupBox("诉讼代理人")
        agent_grid = QGridLayout(self.agent_frame)
        agent_grid.setHorizontalSpacing(SPACING_LG)
        agent_grid.setVerticalSpacing(SPACING_MD)
        agent_grid.setColumnStretch(1, 1)
        agent_grid.setColumnStretch(3, 1)

        agent_name_label = QLabel("姓名:")
        self.agent_type_label = QLabel("代理类型:")
        self.agent_org_label = QLabel("所在单位/律师事务所:")
        agent_phone_label = QLabel("电话:")
        for label in (agent_name_label, self.agent_type_label,
                      self.agent_org_label, agent_phone_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.agent_name_edit = QLineEdit()
        self.agent_type_combo = QComboBox()
        self.agent_type_combo.addItem("")
        for role in AGENT_TYPES:
            self.agent_type_combo.addItem(role)
        self.agent_org_edit = QLineEdit()
        self.agent_phone_edit = QLineEdit()
        self.agent_phone_edit.setValidator(QRegularExpressionValidator(_PHONE_INPUT_PATTERN))

        agent_grid.addWidget(agent_name_label, 0, 0)
        agent_grid.addWidget(self.agent_name_edit, 0, 1)
        agent_grid.addWidget(self.agent_type_label, 0, 2)
        agent_grid.addWidget(self.agent_type_combo, 0, 3)
        agent_grid.addWidget(self.agent_org_label, 1, 0)
        agent_grid.addWidget(self.agent_org_edit, 1, 1)
        agent_grid.addWidget(agent_phone_label, 1, 2)
        agent_grid.addWidget(self.agent_phone_edit, 1, 3)

        self.agent_frame.setVisible(False)
        self.scroll_layout.addWidget(self.agent_frame)

        for edit in (self.agent_name_edit, self.agent_org_edit, self.agent_phone_edit):
            edit.textChanged.connect(lambda _text: self._refresh_validation_message())

        # Explicit open/closed state: ``isVisible()`` also reports False while
        # the page itself is not yet on screen, so it cannot carry this state.
        self._agent_section_open = False
        self._agent_widgets = {
            "name": self.agent_name_edit,
            "type": self.agent_type_combo,
            "org": self.agent_org_edit,
            "phone": self.agent_phone_edit,
        }
        self._agent_name_fields = [
            (agent_name_label, self.agent_name_edit),
            (self.agent_type_label, self.agent_type_combo),
            (self.agent_org_label, self.agent_org_edit),
            (agent_phone_label, self.agent_phone_edit),
        ]
        self._apply_field_names(self._agent_name_fields, "诉讼代理人")

    def _toggle_agent_section(self):
        """Open or close the agent section; closing also clears its fields."""
        self._agent_section_open = not self._agent_section_open
        self.agent_frame.setVisible(self._agent_section_open)
        self.agent_toggle_btn.setText("移除代理人" if self._agent_section_open else "添加代理人")
        if not self._agent_section_open:
            self.agent_name_edit.clear()
            self.agent_type_combo.setCurrentIndex(0)
            self.agent_org_edit.clear()
            self.agent_phone_edit.clear()
        self._refresh_validation_message()

    def get_agent_data(self):
        """Return the agent record, or ``None`` while the section is closed."""
        if not self._agent_section_open:
            return None

        def combo_text(combo):
            return (combo.currentText() or "").strip()

        return {
            "name": self._widget_text(self.agent_name_edit).strip(),
            "type": combo_text(self.agent_type_combo),
            "org": self._widget_text(self.agent_org_edit).strip(),
            "phone": self._widget_text(self.agent_phone_edit).strip(),
        }

    def set_agent_data(self, data):
        """Fill the agent section from a draft record and open it."""
        self.agent_name_edit.setText((data.get("name") or "").strip())
        role = (data.get("type") or "").strip()
        index = self.agent_type_combo.findText(role)
        self.agent_type_combo.setCurrentIndex(index if index >= 0 else 0)
        self.agent_org_edit.setText((data.get("org") or "").strip())
        self.agent_phone_edit.setText((data.get("phone") or "").strip())
        if not self._agent_section_open:
            self._toggle_agent_section()

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
        # PARTY_CARD gives the card its rounded, primary-accented treatment in
        # the global stylesheet without changing any behaviour.
        group.setObjectName(PARTY_CARD)
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
        gender_label = QLabel("性别:")
        birth_label = QLabel("出生日期:")
        ethnicity_label = QLabel("民族:")
        ethnicity_other_label = QLabel("其他民族:")
        occupation_label = QLabel("职业:")
        for label in (name_label, id_label, credit_code_label, legal_rep_label,
                      addr_label, phone_label, gender_label, birth_label,
                      ethnicity_label, ethnicity_other_label, occupation_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING_LG)
        grid.setVerticalSpacing(SPACING_MD)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # Natural-person detail widgets follow the historical generator's card:
        # they collapse with the rest of the personal fields in company mode.
        gender_combo = QComboBox()
        gender_combo.addItem("")
        gender_combo.addItem("男")
        gender_combo.addItem("女")
        birth_edit = QLineEdit()
        birth_edit.setPlaceholderText("格式 YYYY-MM-DD")
        ethnicity_combo = QComboBox()
        for option in ETHNICITY_OPTIONS:
            ethnicity_combo.addItem(option)
        ethnicity_other_edit = QLineEdit()
        ethnicity_other_edit.setPlaceholderText("请输入民族名称")
        occupation_edit = QLineEdit()

        # Personal mode: 姓名 | 身份证号, then 住址 | 电话, then the detail rows.
        grid.addWidget(name_label, 0, 0)
        grid.addWidget(name_edit, 0, 1)
        grid.addWidget(id_label, 0, 2)
        grid.addWidget(id_edit, 0, 3)
        grid.addWidget(addr_label, 1, 0)
        grid.addWidget(addr_edit, 1, 1)
        grid.addWidget(phone_label, 1, 2)
        grid.addWidget(phone_edit, 1, 3)
        grid.addWidget(gender_label, 2, 0)
        grid.addWidget(gender_combo, 2, 1)
        grid.addWidget(birth_label, 2, 2)
        grid.addWidget(birth_edit, 2, 3)
        grid.addWidget(ethnicity_label, 3, 0)
        grid.addWidget(ethnicity_combo, 3, 1)
        grid.addWidget(occupation_label, 3, 2)
        grid.addWidget(occupation_edit, 3, 3)
        grid.addWidget(ethnicity_other_label, 4, 0)
        grid.addWidget(ethnicity_other_edit, 4, 1)
        # Company mode adds a row that collapses while every cell is hidden.
        grid.addWidget(credit_code_label, 5, 0)
        grid.addWidget(credit_code_edit, 5, 1)
        grid.addWidget(legal_rep_label, 5, 2)
        grid.addWidget(legal_rep_edit, 5, 3)
        group_layout.addLayout(grid)

        phone_validator = QRegularExpressionValidator(_PHONE_INPUT_PATTERN)
        phone_edit.setValidator(phone_validator)

        # Defendant cards carry the property-case address hint; its visibility
        # follows the current category so a category switch keeps the card.
        addr_hint = None
        if not is_plaintiff:
            addr_hint = QLabel("提示：若被告搬家，请填写现居住满一年的地址，以便法院送达。")
            addr_hint.setObjectName(REMINDER_LABEL)
            addr_hint.setWordWrap(True)
            addr_hint.setVisible(self.field("case_type") == "property")
            group_layout.addWidget(addr_hint)

        # 个人/企业 toggle. Toggling swaps the personal ID field for the company
        # credit-code / legal-representative fields; each caption travels with
        # its field so no dangling identity label is ever left behind. The
        # natural-person detail fields collapse together with the identity row.
        personal_fields = (
            gender_label, gender_combo,
            birth_label, birth_edit,
            ethnicity_label, ethnicity_combo,
            ethnicity_other_label, ethnicity_other_edit,
            occupation_label, occupation_edit,
        )
        is_company_check.toggled.connect(
            lambda checked: self._toggle_company_fields(
                checked,
                id_edit,
                credit_code_edit,
                legal_rep_edit,
                id_label,
                credit_code_label,
                legal_rep_label,
                personal_fields,
                card=widget,
            )
        )
        # The company/natural-person form is case-relevant beyond this page
        # (the labour complaint is an employee-side template), so the change
        # must reach the wizard's page-completeness listeners immediately.
        is_company_check.toggled.connect(lambda *_: self.completeChanged.emit())

        # The free-text companion only matters when the combo says "其他" and
        # the card is in natural-person mode.
        def refresh_ethnicity_other_visibility():
            self._update_ethnicity_other_visibility(widget)

        ethnicity_combo.currentTextChanged.connect(lambda _text: refresh_ethnicity_other_visibility())
        ethnicity_combo.currentTextChanged.connect(lambda _text: self._refresh_validation_message())
        gender_combo.currentTextChanged.connect(lambda _text: self._refresh_validation_message())

        name_fields = [
            (name_label, name_edit),
            (id_label, id_edit),
            (gender_label, gender_combo),
            (birth_label, birth_edit),
            (ethnicity_label, ethnicity_combo),
            (ethnicity_other_label, ethnicity_other_edit),
            (occupation_label, occupation_edit),
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
            "gender": gender_combo,
            "birth": birth_edit,
            "ethnicity": ethnicity_combo,
            "ethnicity_other": ethnicity_other_edit,
            "occupation": occupation_edit,
            "id_label": id_label,
            "credit_code_label": credit_code_label,
            "legal_rep_label": legal_rep_label,
            "ethnicity_other_label": ethnicity_other_label,
            "delete_btn": delete_btn,
            "name_fields": name_fields,
            "addr_hint": addr_hint,
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
            personal_fields,
            card=widget,
        )
        self._apply_field_names(name_fields, f"{kind}{number}")

        # Keep the live guidance and the wizard "Next" button state in sync, and
        # mark the page as touched when the user leaves a field.
        for w in (name_edit, phone_edit, credit_code_edit, legal_rep_edit,
                  birth_edit, ethnicity_other_edit, occupation_edit):
            w.textChanged.connect(lambda _text: self._refresh_validation_message())
            w.editingFinished.connect(self._on_field_edited)

        self._refresh_validation_message()
        self._rebuild_party_tab_order()

    @staticmethod
    def _update_ethnicity_other_visibility(widget):
        """Show the free-text ethnicity companion only for "其他" natural persons."""
        show = (
            widget["ethnicity"].currentText() == ETHNICITY_OTHER
            and not widget["is_company"].isChecked()
        )
        widget["ethnicity_other"].setVisible(show)
        widget["ethnicity_other_label"].setVisible(show)

    def _toggle_company_fields(
        self,
        checked,
        id_edit,
        credit_code_edit,
        legal_rep_edit,
        id_label,
        credit_code_label,
        legal_rep_label,
        personal_fields=(),
        card=None,
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
        for field_widget in personal_fields:
            field_widget.setVisible(not checked)
        if card is not None:
            self._update_ethnicity_other_visibility(card)
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
                for key in ("name", "id", "addr", "phone", "gender", "birth",
                            "ethnicity", "ethnicity_other", "occupation",
                            "credit_code", "legal_rep", "is_company", "delete_btn")
            )
        sequence.append(self.add_p_btn)
        for card in self.defendant_widgets:
            sequence.extend(
                card[key]
                for key in ("name", "id", "addr", "phone", "gender", "birth",
                            "ethnicity", "ethnicity_other", "occupation",
                            "credit_code", "legal_rep", "is_company", "delete_btn")
            )
        sequence.append(self.add_d_btn)
        for key in ("name", "type", "org", "phone"):
            sequence.append(self._agent_widgets[key])
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
                continue

            birth = self._widget_text(w["birth"]).strip()
            if birth and parse_full_date(birth).status in (
                DateStatus.INVALID_FORMAT,
                DateStatus.INVALID_CALENDAR_DATE,
                DateStatus.OUT_OF_SUPPORTED_RANGE,
            ):
                issues.append(f"{kind}{idx}“{name}”的出生日期格式可能不正确，建议按 YYYY-MM-DD 填写（仅提示，不阻止生成）。")

            if w["ethnicity"].currentText() == ETHNICITY_OTHER and not self._widget_text(w["ethnicity_other"]).strip():
                issues.append(f"{kind}{idx}“{name}”选择了“其他”民族但未填写具体名称（仅提示，不阻止生成）。")

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
        defensively so that an absent widget can never raise. ``ethnicity``
        keeps the raw combo selection (which may literally be "其他"); the
        presenter resolves it against ``ethnicity_other`` so the draft can
        restore the combo state verbatim.
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
                    "gender": w["gender"].currentText().strip(),
                    "birth_date": self._widget_text(w["birth"]).strip(),
                    "ethnicity": w["ethnicity"].currentText().strip(),
                    "ethnicity_other": self._widget_text(w["ethnicity_other"]).strip(),
                    "occupation": self._widget_text(w["occupation"]).strip(),
                })
            return result

        return {
            "plaintiffs": build(self.plaintiff_widgets),
            "defendants": build(self.defendant_widgets),
        }
