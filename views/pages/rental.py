# File: views/pages/rental.py
# Purpose: Rental-contract claim page (arrears, termination, return of premises).
# Encoding: UTF-8
"""Rental-contract page: lease basics, arrears and demand history, the
contract-status classification and the conditional termination date."""

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from models.case_model import RENTAL_LEASE_LABELS, RENTAL_LEASE_STATUSES
from models.validation import DateStatus, parse_full_date
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
    add_facts_examples_button,
    add_supplement_section,
)
from views.theme import INFO_LABEL, WARNING_LABEL
from views.widgets import DateLineEdit


def _tri_state_group(owner, yes_text, no_text):
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


class RentalClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（租赁合同）")

        root = QVBoxLayout()

        # --- 一、租赁基本事实 ------------------------------------------------
        basics = _section(root, "一、租赁基本事实")

        self.property_address = QLineEdit()
        self.property_address.setPlaceholderText("如: 上海市示例区示例路1号1栋101室")

        self.contract_date = DateLineEdit(restrict_future=True)
        self.contract_date.setPlaceholderText("格式 YYYY-MM-DD，如 2023-01-01")

        self.lease_start = DateLineEdit(restrict_future=True)
        self.lease_start.setPlaceholderText("格式 YYYY-MM-DD")

        self.lease_end = DateLineEdit(restrict_future=True)
        self.lease_end.setPlaceholderText("格式 YYYY-MM-DD")

        self.monthly_rent = QLineEdit()
        _decimal_validator(self.monthly_rent)
        self.monthly_rent.setPlaceholderText("单位：元/月，如 3000")

        self.payment_cycle = QLineEdit()
        self.payment_cycle.setPlaceholderText("如: 按月支付 / 按季支付")

        basics.addRow("房屋地址:", self.property_address)
        basics.addRow("合同签订日期:", self.contract_date)
        basics.addRow("租赁起始日期:", self.lease_start)
        basics.addRow("租赁到期日期:", self.lease_end)
        basics.addRow("月租金(元/月):", self.monthly_rent)
        basics.addRow("租金支付方式:", self.payment_cycle)

        # --- 二、欠租与催缴 --------------------------------------------------
        arrears = _section(root, "二、欠租与催缴")

        self.arrears_start = DateLineEdit(restrict_future=True)
        self.arrears_start.setPlaceholderText("格式 YYYY-MM-DD")

        self.arrears_end = DateLineEdit(restrict_future=True)
        self.arrears_end.setPlaceholderText("格式 YYYY-MM-DD")

        self.arrears_amount = QLineEdit()
        _decimal_validator(self.arrears_amount)
        self.arrears_amount.setPlaceholderText("单位：元，如 9000")

        self.late_fee = QLineEdit()
        _decimal_validator(self.late_fee)
        self.late_fee.setPlaceholderText("单位：元（留空表示不主张）")

        self.demand_record = QPlainTextEdit()
        self.demand_record.setMaximumHeight(80)
        self.demand_record.setPlaceholderText(
            "如: 2024年6月通过微信、短信催缴，承租人仍未支付。"
        )

        arrears.addRow("欠租起始日期:", self.arrears_start)
        arrears.addRow("欠租截止日期:", self.arrears_end)
        arrears.addRow("欠租金额(元):", self.arrears_amount)
        arrears.addRow("违约金/滞纳金(元):", self.late_fee)
        arrears.addRow("催缴情况:", self.demand_record)
        add_facts_examples_button(self, arrears)

        # --- 三、合同状态与房屋返还 ------------------------------------------
        status = _section(root, "三、合同状态与房屋返还")

        self.lease_status_combo = QComboBox()
        self.lease_status_combo.setAccessibleName("租赁合同状态")
        self.lease_status_combo.setAccessibleDescription(
            "选择租赁合同当前是继续履行、已经解除，还是请求法院解除"
        )
        self.lease_status_combo.addItem("— 请选择合同状态 —", None)
        for value in RENTAL_LEASE_STATUSES:
            self.lease_status_combo.addItem(RENTAL_LEASE_LABELS[value], value)

        self.status_description = QLabel("")
        self.status_description.setObjectName(INFO_LABEL)
        self.status_description.setWordWrap(True)

        self.termination_date = DateLineEdit(restrict_future=True)
        self.termination_date.setPlaceholderText("格式 YYYY-MM-DD")
        self._termination_label = QLabel("解除日期:")

        (
            self.returned_group,
            self.returned_yes,
            self.returned_no,
            self.returned_unknown,
            returned_layout,
        ) = _tri_state_group(self, "已腾退", "未腾退")
        self._returned_label = QLabel("房屋是否已返还:")
        returned_row = QWidget()
        returned_row_layout = QHBoxLayout(returned_row)
        returned_row_layout.setContentsMargins(0, 0, 0, 0)
        returned_row_layout.addWidget(self._returned_label)
        returned_row_layout.addLayout(returned_layout)
        returned_row_layout.addStretch(1)

        status.addRow("合同状态:", self.lease_status_combo)
        status.addRow("", self.status_description)
        status.addRow(self._termination_label, self.termination_date)
        status.addRow(returned_row)

        self.cond_hint = QLabel("")
        self.cond_hint.setObjectName(WARNING_LABEL)
        self.cond_hint.setWordWrap(True)
        self.cond_hint.setVisible(False)
        status.addRow("", self.cond_hint)

        add_supplement_section(self, root, "r")

        # --- 四、建议管辖法院 ------------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 上海市徐汇区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        self.registerField("r_property_address*", self.property_address)
        self.registerField("r_contract_date*", self.contract_date)
        self.registerField("r_lease_start*", self.lease_start)
        self.registerField("r_lease_end*", self.lease_end)
        self.registerField("r_monthly_rent*", self.monthly_rent)
        self.registerField("r_payment_cycle*", self.payment_cycle)
        self.registerField("r_arrears_start*", self.arrears_start)
        self.registerField("r_arrears_end*", self.arrears_end)
        self.registerField("r_arrears_amount*", self.arrears_amount)
        self.registerField("r_late_fee", self.late_fee)
        self.registerField("r_demand_record", self.demand_record, "plainText")
        self.registerField("r_termination_date", self.termination_date)
        self.registerField("r_court_name*", self.court_name)

        self.lease_status_combo.currentIndexChanged.connect(self._refresh_conditional)
        for widget in (
            self.contract_date, self.lease_start, self.lease_end,
            self.arrears_start, self.arrears_end, self.termination_date,
        ):
            widget.textChanged.connect(lambda *_: self._refresh_conditional())
        self._refresh_conditional()

    def _update_status_rows(self):
        status = self.get_lease_status()
        descriptions = {
            "active": "合同继续履行：起诉主要针对欠租；如还要求解除合同或腾退房屋，请选择相应状态。",
            "terminated": "合同已解除：请填写解除日期；如房屋尚未返还，可选择“未腾退”，文书将请求返还房屋。",
            "request_termination": "请求解除：文书将增加解除合同的诉讼请求；如房屋未返还，可请求腾退。",
        }
        self.status_description.setText(
            descriptions.get(status, "请选择合同状态，以便生成相应的诉讼请求和事实表述。")
        )
        show_termination = status == "terminated"
        self._termination_label.setVisible(show_termination)
        self.termination_date.setVisible(show_termination)

    @staticmethod
    def _date_issue(field, label):
        text = field.text().strip()
        if not text:
            return ""
        validation = parse_full_date(text)
        if validation.status in (
            DateStatus.INVALID_FORMAT,
            DateStatus.INVALID_CALENDAR_DATE,
            DateStatus.OUT_OF_SUPPORTED_RANGE,
        ):
            return f"{label}格式无法识别，请按 YYYY-MM-DD 填写或使用日历选择。"
        return ""

    def _conditional_issue(self):
        """Return ``(message, focus_widget)`` for the first blocking issue.

        The required-status check lives in :meth:`isComplete` so that the
        wizard's Next button is disabled for an unclassified contract, while a
        programmatic ``wizard.next()`` keeps the same behavior as the other
        claim pages (their required-text checks are also button-level).
        """
        status = self.get_lease_status()
        if status == "terminated" and not self.termination_date.text().strip():
            return "选择“已解除”时，请填写解除日期。", self.termination_date

        date_fields = [
            (self.contract_date, "合同签订日期"),
            (self.lease_start, "租赁起始日期"),
            (self.lease_end, "租赁到期日期"),
            (self.arrears_start, "欠租起始日期"),
            (self.arrears_end, "欠租截止日期"),
        ]
        if status == "terminated":
            date_fields.append((self.termination_date, "解除日期"))
        for field, label in date_fields:
            issue = self._date_issue(field, label)
            if issue:
                return issue, field

        lease_start = parse_full_date(self.lease_start.text())
        lease_end = parse_full_date(self.lease_end.text())
        if (
            lease_start.status == DateStatus.VALID
            and lease_end.status == DateStatus.VALID
            and lease_end.value < lease_start.value
        ):
            return "租赁到期日期早于起始日期，请核对。", self.lease_end

        arrears_start = parse_full_date(self.arrears_start.text())
        arrears_end = parse_full_date(self.arrears_end.text())
        if (
            arrears_start.status == DateStatus.VALID
            and arrears_end.status == DateStatus.VALID
            and arrears_end.value < arrears_start.value
        ):
            return "欠租截止日期早于起始日期，请核对。", self.arrears_end

        return "", None

    def _refresh_conditional(self):
        self._update_status_rows()
        message, _widget = self._conditional_issue()
        _set_status(self.cond_hint, message)
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        if self.get_lease_status() is None:
            return False
        return not self._conditional_issue()[0]

    def validatePage(self):
        message, widget = self._conditional_issue()
        _set_status(self.cond_hint, message)
        if message:
            widget.setFocus()
            return False
        return True

    # ------------------------------------------------------------------ #
    # State accessors (draft adapter and model builder)
    # ------------------------------------------------------------------ #

    def get_lease_status(self):
        return self.lease_status_combo.currentData()

    def get_property_returned(self):
        checked = self.returned_group.checkedId()
        if checked == 1:
            return True
        if checked == 0:
            return False
        return None
