# File: views/pages/labor.py
# Purpose: Labour-compensation claim page (procedural classification, facts).
# Encoding: UTF-8
"""Labour-compensation claim page with the procedural-state selector.

The page replaces the former binary/tri-state arbitration posture with a
finite procedural classification (see :mod:`utils.labor_security`). One pure
evaluator drives three consumers that must never disagree:

* this page's immediate hint and Next-button enablement,
* the presenter's fail-closed export gate,
* the arbitration sentence of the generated complaint.

Conditional rows are shown per selected state; hidden rows keep their values,
so changing a selection never destroys user input. Guidance is immediate and
non-destructive: blocked states explain why in Chinese and keep every field
editable (and savable as a draft).
"""

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from views.theme import REMINDER_LABEL, WARNING_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
    add_facts_examples_button,
)
from utils.labor_security import (
    LABOR_PROCEDURES,
    LABOR_REFUSAL_GROUNDS,
    LABOR_ROLES,
    PROCEDURE_ACCEPTANCE_OVERDUE,
    PROCEDURE_AWARD_OVERDUE,
    PROCEDURE_DESCRIPTIONS,
    PROCEDURE_FINAL_AWARD,
    PROCEDURE_LABELS,
    PROCEDURE_NON_FINAL_AWARD,
    PROCEDURE_NOT_ACCEPTED,
    REFUSAL_GROUND_LABELS,
    ROLE_LABELS,
    LaborProcedureGuard,
    evaluate_labor_eligibility,
)


def _tri_state_group(owner, yes_text, no_text):
    """Return ``(group, yes, no, unknown, layout)`` with "未确认" preselected."""
    group = QButtonGroup(owner)
    yes = QRadioButton(yes_text)
    no = QRadioButton(no_text)
    unknown = QRadioButton("未确认")
    group.addButton(yes, 1)
    group.addButton(no, 0)
    group.addButton(unknown, 2)
    unknown.setChecked(True)
    layout = QHBoxLayout()
    for button in (yes, no, unknown):
        layout.addWidget(button)
    return group, yes, no, unknown, layout


def _tri_state_value(group):
    checked = group.checkedId()
    if checked == 1:
        return True
    if checked == 0:
        return False
    return None


def _choice_group(owner, values, labels):
    """Return ``(group, layout, widgets)`` for a value radio list, none selected.

    Radios stack in a single column: the labels are legal phrasing and must
    never force horizontal scrolling at the minimum window width.
    """
    group = QButtonGroup(owner)
    widgets = {}
    layout = QGridLayout()
    for index, value in enumerate(values):
        button = QRadioButton(labels[value])
        group.addButton(button, index)
        widgets[value] = button
        layout.addWidget(button, index, 0)
    return group, layout, widgets


def _full_width_row(layout):
    """Wrap *layout* in a marginless container so whole rows hide cleanly."""
    row = QWidget()
    box = QVBoxLayout(row)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(2)
    box.addLayout(layout)
    return row


def _checked_choice(group, widgets):
    checked = group.checkedId()
    if checked < 0:
        return None
    for value, button in widgets.items():
        if button is group.checkedButton():
            return value
    return None


class LaborClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（劳动报酬／工资追索）")

        root = QVBoxLayout()

        # Persistent arbitration-precondition notice with an explicit basis
        # time, so the page never reads as a universally current conclusion.
        self._guard = LaborProcedureGuard()
        self.arbitration_notice = QLabel(self._guard.get_persistent_notice())
        self.arbitration_notice.setObjectName(REMINDER_LABEL)
        self.arbitration_notice.setWordWrap(True)
        root.addWidget(self.arbitration_notice)

        # --- 一、仲裁程序状态 -------------------------------------------------
        arbitration = _section(root, "一、仲裁程序状态")

        self.procedure_combo = QComboBox()
        self.procedure_combo.setAccessibleName("劳动仲裁程序状态")
        self.procedure_combo.setAccessibleDescription(
            "选择当前劳动争议所处的仲裁程序阶段；不同阶段可进行的诉讼途径不同"
        )
        self.procedure_combo.addItem("— 请选择程序状态 —", None)
        for state in LABOR_PROCEDURES:
            self.procedure_combo.addItem(PROCEDURE_LABELS[state], state)
        self.procedure_description = QLabel("")
        self.procedure_description.setObjectName(REMINDER_LABEL)
        self.procedure_description.setWordWrap(True)

        arbitration.addRow("程序状态:", self.procedure_combo)
        arbitration.addRow("", self.procedure_description)

        # Conditional inputs, revealed per state. Every row owns its QLabel so
        # visibility (and, for the shared receipt date, the wording) can follow
        # the selected state without rebuilding the form.
        self.arb_commission = QLineEdit()
        self.arb_commission.setPlaceholderText("如: 北京市朝阳区劳动人事争议仲裁委员会")

        self.arb_case_no = QLineEdit()
        self.arb_case_no.setPlaceholderText("如: 京朝劳人仲字〔2024〕第1号（选填）")

        self._commission_label = QLabel("仲裁机构:")
        self._case_no_label = QLabel("仲裁案号:")

        self.arb_receipt_date = QLineEdit()
        self.arb_receipt_date.setPlaceholderText("格式 YYYY-MM-DD")
        self._receipt_label = QLabel("收到裁决书日期:")

        self.arb_application_date = QLineEdit()
        self.arb_application_date.setPlaceholderText("格式 YYYY-MM-DD")
        self._application_label = QLabel("申请仲裁日期:")

        self.arb_acceptance_date = QLineEdit()
        self.arb_acceptance_date.setPlaceholderText("见受理通知书，格式 YYYY-MM-DD")
        self._acceptance_label = QLabel("仲裁受理日期:")

        (self.refusal_group, refusal_layout, self._refusal_buttons) = _choice_group(
            self, LABOR_REFUSAL_GROUNDS, REFUSAL_GROUND_LABELS
        )
        self._refusal_label = QLabel("不予受理理由:")
        self._refusal_row = _full_width_row(refusal_layout)
        refusal_layout.setColumnStretch(0, 1)
        refusal_layout.setColumnStretch(1, 1)

        (self.delay_group, self.delay_yes, self.delay_no, self.delay_unknown,
         delay_layout) = _tri_state_group(self, "是", "否")
        self._delay_label = QLabel("迟延是否因下列情形造成:")
        self._delay_help = QLabel(
            "移送管辖、送达延误、等待另案诉讼结果或评残结论、等待开庭、"
            "启动鉴定程序或委托其他部门调查取证"
        )
        self._delay_help.setWordWrap(True)
        delay_box = QVBoxLayout()
        delay_box.setContentsMargins(0, 0, 0, 0)
        delay_box.setSpacing(2)
        delay_box.addLayout(delay_layout)
        delay_box.addWidget(self._delay_help)
        self._delay_row = _full_width_row(delay_box)

        (self.role_group, role_layout, self._role_buttons) = _choice_group(
            self, LABOR_ROLES, ROLE_LABELS
        )
        self._role_label = QLabel("您在本案中的身份:")
        self._role_row = _full_width_row(role_layout)

        arbitration.addRow(self._commission_label, self.arb_commission)
        arbitration.addRow(self._case_no_label, self.arb_case_no)
        arbitration.addRow(self._receipt_label, self.arb_receipt_date)
        arbitration.addRow(self._application_label, self.arb_application_date)
        arbitration.addRow(self._acceptance_label, self.arb_acceptance_date)
        arbitration.addRow(self._refusal_label, self._refusal_row)
        arbitration.addRow(self._delay_label, self._delay_row)
        arbitration.addRow(self._role_label, self._role_row)

        self.arbitration_hint = QLabel("")
        self.arbitration_hint.setObjectName(WARNING_LABEL)
        self.arbitration_hint.setWordWrap(True)
        self.arbitration_hint.setVisible(False)

        self.procedure_warning = QLabel("")
        self.procedure_warning.setObjectName(REMINDER_LABEL)
        self.procedure_warning.setWordWrap(True)
        self.procedure_warning.setVisible(False)

        arbitration.addRow("", self.arbitration_hint)
        arbitration.addRow("", self.procedure_warning)

        # --- 二、劳动关系基本事实 -------------------------------------------
        basic = _section(root, "二、劳动关系基本事实")

        self.emp_join_date = QLineEdit()
        self.emp_join_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-15")

        self.job_title = QLineEdit()
        self.job_title.setPlaceholderText("如: 软件工程师")

        self.monthly_salary = QLineEdit()
        _decimal_validator(self.monthly_salary)
        self.monthly_salary.setPlaceholderText("如: 8000")

        self.emp_term_date = QLineEdit()
        self.emp_term_date.setPlaceholderText("格式 YYYY-MM-DD（仍在职可不填）")

        basic.addRow("入职日期:", self.emp_join_date)
        basic.addRow("岗位:", self.job_title)
        basic.addRow("月工资标准(元):", self.monthly_salary)
        basic.addRow("离职/截止日期:", self.emp_term_date)
        add_facts_examples_button(self, basic)

        # --- 三、欠薪与加班 -------------------------------------------------
        unpaid = _section(root, "三、欠薪与加班")

        self.unpaid_months = QLineEdit()
        self.unpaid_months.setPlaceholderText("如: 2023年12月至2024年2月（整月区间）")

        self.overtime_hours = QLineEdit()
        _decimal_validator(self.overtime_hours)
        self.overtime_hours.setPlaceholderText("如: 40（选填）")

        self.overtime_pay = QLineEdit()
        _decimal_validator(self.overtime_pay)
        self.overtime_pay.setPlaceholderText("如: 3500（选填）")

        unpaid.addRow("欠薪月份/区间:", self.unpaid_months)
        unpaid.addRow("加班工时(小时，选填):", self.overtime_hours)
        unpaid.addRow("加班费(元，选填):", self.overtime_pay)

        # --- 四、合同与社保 -------------------------------------------------
        contract = _section(root, "四、合同与社保")

        # Tri-state like every other factual confirmation: an untouched control
        # is "未确认" and never asserts that a written contract was missing.
        (self.is_no_contract_group, self.no_contract_yes, self.no_contract_no,
         self.no_contract_unknown, no_contract_layout) = _tri_state_group(self, "是", "否")

        self.social_sec_info = QLineEdit()
        self.social_sec_info.setPlaceholderText("如: 未按实际工资基数缴纳（选填）")

        contract.addRow("是否未签劳动合同:", no_contract_layout)
        contract.addRow("社保缴纳情况:", self.social_sec_info)

        # --- 五、建议管辖法院 -----------------------------------------------
        court = _section(root, "五、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        self.registerField("l_emp_join_date*", self.emp_join_date)
        self.registerField("l_job_title*", self.job_title)
        self.registerField("l_monthly_salary*", self.monthly_salary)
        self.registerField("l_unpaid_months*", self.unpaid_months)
        self.registerField("l_emp_term_date", self.emp_term_date)
        self.registerField("l_overtime_hours", self.overtime_hours)
        self.registerField("l_overtime_pay", self.overtime_pay)
        self.registerField("l_social_sec_info", self.social_sec_info)
        self.registerField("l_court_name*", self.court_name)
        # Conditional procedure inputs; requiredness is enforced per state by
        # the shared evaluator, not by the asterisk mechanism.
        self.registerField("l_arb_commission", self.arb_commission)
        self.registerField("l_arb_case_no", self.arb_case_no)
        self.registerField("l_arb_receipt_date", self.arb_receipt_date)
        self.registerField("l_arb_application_date", self.arb_application_date)
        self.registerField("l_arb_acceptance_date", self.arb_acceptance_date)

        self.procedure_combo.currentIndexChanged.connect(self._refresh_conditional)
        self.refusal_group.buttonToggled.connect(lambda *_: self._refresh_conditional())
        self.role_group.buttonToggled.connect(lambda *_: self._refresh_conditional())
        self.delay_group.buttonToggled.connect(lambda *_: self._refresh_conditional())
        for widget in (self.arb_commission, self.arb_case_no, self.arb_receipt_date,
                       self.arb_application_date, self.arb_acceptance_date):
            widget.textChanged.connect(lambda *_: self._refresh_conditional())
        self._refresh_conditional()

    # ------------------------------------------------------------------ #
    # Conditional procedure rows
    # ------------------------------------------------------------------ #

    _COMMISSION_STATES = frozenset({
        PROCEDURE_ACCEPTANCE_OVERDUE,
        PROCEDURE_NOT_ACCEPTED,
        PROCEDURE_AWARD_OVERDUE,
        PROCEDURE_NON_FINAL_AWARD,
        PROCEDURE_FINAL_AWARD,
    })
    _RECEIPT_STATES = frozenset({
        PROCEDURE_NOT_ACCEPTED,
        PROCEDURE_NON_FINAL_AWARD,
        PROCEDURE_FINAL_AWARD,
    })
    #: States that can reach the employee wage-recovery complaint and must
    #: therefore confirm the plaintiff role (mirrors the evaluator contract).
    _ROLE_REQUIRED_STATES = frozenset({
        PROCEDURE_ACCEPTANCE_OVERDUE,
        PROCEDURE_NOT_ACCEPTED,
        PROCEDURE_AWARD_OVERDUE,
        PROCEDURE_NON_FINAL_AWARD,
        PROCEDURE_FINAL_AWARD,
    })

    def _update_conditional_rows(self):
        """Reveal the rows the selected state needs; hidden rows keep values."""
        state = self.get_labor_procedure()
        show_commission = state in self._COMMISSION_STATES
        show_receipt = state in self._RECEIPT_STATES
        self._commission_label.setVisible(show_commission)
        self.arb_commission.setVisible(show_commission)
        self._case_no_label.setVisible(show_commission)
        self.arb_case_no.setVisible(show_commission)

        self._receipt_label.setVisible(show_receipt)
        self.arb_receipt_date.setVisible(show_receipt)
        if show_receipt:
            label = "收到不予受理通知书日期:" if state == PROCEDURE_NOT_ACCEPTED else "收到裁决书日期:"
            self._receipt_label.setText(label)
            self.arb_receipt_date.setAccessibleName(label.rstrip(":"))
            self.arb_receipt_date.setAccessibleDescription(
                "填写书面裁决或通知上载明的日期，用于起诉状中如实陈述程序经过"
            )

        show_application = state == PROCEDURE_ACCEPTANCE_OVERDUE
        self._application_label.setVisible(show_application)
        self.arb_application_date.setVisible(show_application)

        show_acceptance = state == PROCEDURE_AWARD_OVERDUE
        self._acceptance_label.setVisible(show_acceptance)
        self.arb_acceptance_date.setVisible(show_acceptance)

        show_refusal = state == PROCEDURE_NOT_ACCEPTED
        self._refusal_label.setVisible(show_refusal)
        self._refusal_row.setVisible(show_refusal)

        show_delay = state in (PROCEDURE_ACCEPTANCE_OVERDUE, PROCEDURE_AWARD_OVERDUE)
        self._delay_label.setVisible(show_delay)
        self._delay_row.setVisible(show_delay)

        show_role = state in self._ROLE_REQUIRED_STATES
        self._role_label.setVisible(show_role)
        self._role_row.setVisible(show_role)

    # ------------------------------------------------------------------ #
    # Shared evaluation (one source of truth with the export gate)
    # ------------------------------------------------------------------ #

    def evaluate_current(self):
        """Run the shared eligibility evaluator on the page's current input.

        The plaintiff's company/natural-person form is read from the party
        cards so the employee-only wage template cannot be produced for a
        company-form plaintiff (the role itself is never inferred from the
        cards — the user must select it).
        """
        wizard = self.wizard()
        plaintiff_is_company = False
        if wizard is not None:
            plaintiff_is_company = any(
                card["is_company"].isChecked()
                for card in wizard.party_page.plaintiff_widgets
            )
        return evaluate_labor_eligibility(
            self.get_labor_procedure(),
            refusal_ground=self.get_refusal_ground(),
            role=self.get_labor_role(),
            delay_exception=self.get_delay_exception(),
            plaintiff_is_company=plaintiff_is_company,
            commission=self.arb_commission.text(),
            application_date=self.arb_application_date.text(),
            acceptance_date=self.arb_acceptance_date.text(),
            receipt_date=self.arb_receipt_date.text(),
        )

    def initializePage(self):
        """Subscribe to party-form changes once the page can see the wizard.

        The plaintiff's company/natural-person form lives on the party page and
        changes without touching any widget on this page; without this wiring
        the guidance hint and the Next button would go stale when the user
        marks a plaintiff as a company. The wiring is idempotent.
        """
        wizard = self.wizard()
        if wizard is not None and not getattr(self, "_party_form_wired", False):
            self._party_form_wired = True
            wizard.party_page.completeChanged.connect(self._refresh_conditional)
        self._refresh_conditional()

    def _conditional_issue(self):
        """The blocking explanation for the current selection, or ``""``."""
        eligibility = self.evaluate_current()
        if eligibility.eligible:
            return ""
        return eligibility.reason

    def _refresh_conditional(self):
        state = self.get_labor_procedure()
        self.procedure_description.setText(
            PROCEDURE_DESCRIPTIONS.get(state, "") if state else "请先选择当前所处的仲裁程序阶段。"
        )
        self._update_conditional_rows()
        eligibility = self.evaluate_current()
        if eligibility.eligible:
            _set_status(self.arbitration_hint, "")
            self.procedure_warning.setText(eligibility.warning)
            self.procedure_warning.setVisible(bool(eligibility.warning))
        else:
            _set_status(self.arbitration_hint, eligibility.reason)
            self.procedure_warning.setVisible(False)
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return self.evaluate_current().eligible

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.arbitration_hint, issue)
            self.procedure_combo.setFocus()
            return False
        return True

    # ------------------------------------------------------------------ #
    # State accessors (used by the draft adapter and the model builder)
    # ------------------------------------------------------------------ #

    def get_labor_procedure(self):
        """Return the selected procedural state, or ``None`` when unselected."""
        return self.procedure_combo.currentData()

    def get_refusal_ground(self):
        """Return the selected non-acceptance ground, or ``None``."""
        return _checked_choice(self.refusal_group, self._refusal_buttons)

    def get_labor_role(self):
        """Return the selected party role, or ``None``."""
        return _checked_choice(self.role_group, self._role_buttons)

    def get_delay_exception(self):
        """Return ``True`` / ``False`` / ``None`` (unconfirmed) delay cause."""
        return _tri_state_value(self.delay_group)

    def get_has_no_contract(self):
        """Return ``True`` / ``False`` / ``None`` (unconfirmed) no-contract status."""
        return _tri_state_value(self.is_no_contract_group)
