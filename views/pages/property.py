# File: views/pages/property.py
# Purpose: Property-service claim page (shared fee estimate, demo controls).
# Encoding: UTF-8
"""Property-service claim page: the shared property-fee estimate feeds both
the on-screen label and the model; insufficient input shows a neutral
message instead of a fabricated zero."""

from decimal import Decimal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout
from models.calculations import CalculationError, calculate_property_fee, parse_decimal
from views.theme import DEMO_BADGE, INFO_LABEL, PRIMARY_BUTTON, REMINDER_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)

class PropertyClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（物业服务合同）")

        root = QVBoxLayout()

        # Demo-mode badge, hidden in production.
        self.demo_badge = QLabel("演示模式")
        self.demo_badge.setObjectName(DEMO_BADGE)
        self.demo_badge.setVisible(False)
        root.addWidget(self.demo_badge)

        # Test-data entry point, only shown in demo mode (see set_demo_mode).
        self.fill_btn = QPushButton("一键填写测试数据")
        self.fill_btn.setObjectName(PRIMARY_BUTTON)
        self.fill_btn.setVisible(False)
        root.addWidget(self.fill_btn)

        # --- 一、物业与计费情况 ---------------------------------------------
        basic = _section(root, "一、物业与计费情况")

        self.property_addr = QLineEdit()
        self.property_addr.setPlaceholderText("如: 幸福里小区 3 栋 1201 室")

        self.house_area = QLineEdit()
        _decimal_validator(self.house_area)
        self.house_area.setPlaceholderText("如: 115.5")

        self.fee_rate = QLineEdit()
        _decimal_validator(self.fee_rate)
        self.fee_rate.setPlaceholderText("如: 2.8")

        self.period_start = QLineEdit()
        self.period_start.setPlaceholderText("格式 YYYY-MM-DD 或 YYYY年M月D日，如 2024-01-01")

        self.period_end = QLineEdit()
        self.period_end.setPlaceholderText("格式 YYYY-MM-DD 或 YYYY年M月D日，如 2025-12-31")

        basic.addRow("物业地址/房号:", self.property_addr)
        basic.addRow("房屋面积(m²):", self.house_area)
        basic.addRow("计费标准(元/m²/月):", self.fee_rate)
        basic.addRow("欠费起始日期:", self.period_start)
        basic.addRow("欠费截止日期:", self.period_end)

        # --- 二、违约金与催缴 -----------------------------------------------
        demand = _section(root, "二、违约金与催缴")

        self.late_fee_logic = QLineEdit()
        self.late_fee_logic.setPlaceholderText("如: 按合同约定计算 / 暂计 500 元")

        self.demand_record = QTextEdit()
        self.demand_record.setMaximumHeight(80)
        self.demand_record.setPlaceholderText("如: 2025年6月多次张贴催缴通知并发送短信。")

        demand.addRow("违约金/滞纳金计算:", self.late_fee_logic)
        demand.addRow("催缴方式:", self.demand_record)

        # --- 三、金额核对（系统计算） ---------------------------------------
        amount = _section(root, "三、金额核对（系统计算）")

        self.total_input = QLineEdit()
        _decimal_validator(self.total_input)
        self.total_input.setPlaceholderText("可选：用户自填总金额，用于与系统计算比对")

        self.calc_label = QLabel("")
        self.calc_label.setObjectName(INFO_LABEL)
        self.calc_label.setWordWrap(True)
        self.warn_label = QLabel("")
        self.warn_label.setObjectName(REMINDER_LABEL)
        self.warn_label.setWordWrap(True)
        self.warn_label.setVisible(False)

        amount.addRow("自填总金额(元):", self.total_input)
        amount.addRow("系统计算:", self.calc_label)
        amount.addRow("", self.warn_label)

        # --- 四、建议管辖法院 -----------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 上海市徐汇区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        for w in [self.house_area, self.fee_rate, self.period_start, self.period_end, self.total_input]:
            w.textChanged.connect(self.update_calc)

        self.registerField("p_property_addr*", self.property_addr)
        self.registerField("p_house_area*", self.house_area)
        self.registerField("p_fee_rate*", self.fee_rate)
        self.registerField("p_period_start*", self.period_start)
        self.registerField("p_period_end*", self.period_end)
        self.registerField("p_late_fee_logic", self.late_fee_logic)
        self.registerField("p_demand_record", self.demand_record, "plainText")
        self.registerField("p_total_input", self.total_input)
        self.registerField("p_court_name*", self.court_name)

    def initializePage(self):
        super().initializePage()
        self.update_calc()

    def update_calc(self):
        """Refresh the on-screen estimate via the shared property-fee calculation.

        The exact same pure function feeds ``PropertyCaseModel``, so the label,
        the preview and the exported document can never disagree. Insufficient
        or invalid input shows a neutral message instead of a fabricated
        valid-looking zero total.
        """
        estimate = calculate_property_fee(
            self.house_area.text(),
            self.fee_rate.text(),
            self.period_start.text(),
            self.period_end.text(),
        )
        if estimate.total is None:
            self.calc_label.setText("尚无法计算，请检查面积、计费标准及起止日期。")
            _set_status(self.warn_label, "")
            return

        self.calc_label.setText(f"月数={estimate.months}，总本金={estimate.total} 元")

        user_total_text = (self.total_input.text() or "").strip()
        if not user_total_text:
            _set_status(self.warn_label, "")
            return
        try:
            user_total = parse_decimal(user_total_text, "自填总金额")
        except CalculationError:
            # The optional comparison amount is malformed (programmatic setText
            # bypasses the input validator): the valid system estimate stays on
            # screen and the label asks for a correctable value. Never zero.
            _set_status(self.warn_label, "自填总金额格式有误，请修正后再比对。")
            return
        if user_total is None or user_total == 0:
            _set_status(self.warn_label, "")
            return
        deviation = abs(user_total - estimate.total) / user_total
        if deviation > Decimal("0.01"):
            _set_status(self.warn_label, "提示：自填总金额与系统计算误差超过 1%，建议核对。")
        else:
            _set_status(self.warn_label, "")

    def fill_test_data(self, notify=True):
        """Populate the property form with fictional data for demo mode."""
        self.property_addr.setText("幸福里小区 3 栋 1201 室")
        self.house_area.setText("115.5")
        self.fee_rate.setText("2.8")
        self.period_start.setText("2024-01-01")
        self.period_end.setText("2025-12-31")
        self.late_fee_logic.setText("按合同约定计算")
        self.demand_record.setPlainText("2025年6月多次张贴催缴通知、发送短信。")
        self.total_input.setText("")
        self.court_name.setText("上海市徐汇区人民法院")
        self.update_calc()
        if notify:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "物业纠纷测试数据已填入。")

    def set_demo_mode(self, enabled):
        """Show or hide the demo-mode badge and test-data button."""
        self.fill_btn.setVisible(enabled)
        self.demo_badge.setVisible(enabled)
