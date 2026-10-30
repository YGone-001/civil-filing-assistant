# File: views/pages/divorce.py
# Purpose: Divorce/custody claim page (child-related conditional requirements).
# Encoding: UTF-8
"""Divorce, custody and property-division claim page; child-related details
require an identified child (conditional validation with focus recovery)."""

from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout
from views.theme import INFO_LABEL, WARNING_LABEL
from views.pages.base import _TitledPage
from views.pages.common import (
    _decimal_validator,
    _section,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)

class DivorceClaimPage(_TitledPage):
    def __init__(self):
        super().__init__()
        self.set_page_title("填写案情与请求（离婚析产／抚养费纠纷）")

        root = QVBoxLayout()

        # --- 一、婚姻与离婚原因 ---------------------------------------------
        marriage = _section(root, "一、婚姻与离婚原因")

        self.marriage_date = QLineEdit()
        self.marriage_date.setPlaceholderText("格式 YYYY-MM-DD，如 2018-05-20")

        self.divorce_reason = QLineEdit()
        self.divorce_reason.setPlaceholderText("如: 感情不和/长期分居")

        self.separation_start_date = QLineEdit()
        self.separation_start_date.setPlaceholderText("格式 YYYY-MM-DD，如 2022-01-01")

        marriage.addRow("登记结婚日期:", self.marriage_date)
        marriage.addRow("离婚原因:", self.divorce_reason)
        marriage.addRow("分居起始日期:", self.separation_start_date)

        # --- 二、子女与抚养（无子女可留空） ---------------------------------
        child = _section(root, "二、子女与抚养（无子女可留空）")

        self.child_name = QLineEdit()
        self.child_name.setPlaceholderText("如: 张三")

        self.child_birthday = QLineEdit()
        self.child_birthday.setPlaceholderText("格式 YYYY-MM-DD，如 2020-01-01")

        self.custody_preference = QLineEdit()
        self.custody_preference.setPlaceholderText("如: 由原告抚养")

        self.support_monthly = QLineEdit()
        _decimal_validator(self.support_monthly)
        self.support_monthly.setPlaceholderText("如: 3000")

        # Persistent guidance clarifying the conditional relationship: a
        # childless divorce may leave every child-related field blank, but any
        # one of them requires the child's name to identify the child.
        self.child_help = QLabel(
            "无子女的离婚可不填本组任何字段；若填写出生日期、抚养权或抚养费，"
            "需同时填写子女姓名。"
        )
        self.child_help.setObjectName(INFO_LABEL)
        self.child_help.setWordWrap(True)

        # On-page explanation for the conditional child-information requirement.
        self.cond_hint = QLabel("")
        self.cond_hint.setObjectName(WARNING_LABEL)
        self.cond_hint.setWordWrap(True)
        self.cond_hint.setVisible(False)

        child.addRow("子女姓名:", self.child_name)
        child.addRow("子女出生日期:", self.child_birthday)
        child.addRow("抚养权诉求:", self.custody_preference)
        child.addRow("月抚养费金额(元):", self.support_monthly)
        child.addRow("", self.child_help)
        child.addRow("", self.cond_hint)

        # --- 三、财产分割 ---------------------------------------------------
        asset = _section(root, "三、财产分割")

        self.asset_description = QLineEdit()
        self.asset_description.setPlaceholderText("如: 房产归原告，车辆归被告")

        asset.addRow("财产分割方案:", self.asset_description)

        # --- 四、建议管辖法院 -----------------------------------------------
        court = _section(root, "四、建议管辖法院")

        self.court_name = QLineEdit()
        self.court_name.setPlaceholderText("如: 北京市朝阳区人民法院")

        court.addRow("建议管辖法院:", self.court_name)

        self.setLayout(_wrap_in_scroll(root))
        _set_page_form_accessibility(self)

        self.registerField("d_marriage_date*", self.marriage_date)
        # Child information is optional: a childless divorce must be reachable.
        # Child-related fields are only consistent together, which is enforced
        # by isComplete() below, so they are registered without "*".
        self.registerField("d_child_name", self.child_name)
        self.registerField("d_child_birthday", self.child_birthday)
        self.registerField("d_custody_preference", self.custody_preference)
        self.registerField("d_support_monthly", self.support_monthly)
        self.registerField("d_divorce_reason", self.divorce_reason)
        self.registerField("d_separation_start_date", self.separation_start_date)
        self.registerField("d_asset_description", self.asset_description)
        self.registerField("d_court_name*", self.court_name)

        # Keep the Next-button state in sync with the conditional requirement.
        for widget in (self.child_name, self.child_birthday, self.custody_preference,
                       self.support_monthly):
            widget.textChanged.connect(lambda *_: self._refresh_conditional())

    def _conditional_issue(self):
        """Child-related details require an identified child."""
        if self.child_name.text().strip():
            return ""
        orphans = []
        if self.child_birthday.text().strip():
            orphans.append("子女出生日期")
        if self.custody_preference.text().strip():
            orphans.append("抚养权诉求")
        if self.support_monthly.text().strip():
            orphans.append("月抚养费金额")
        if orphans:
            return ("已填写" + "、".join(orphans)
                    + "，请同时填写“子女姓名”，或清空上述子女相关字段"
                      "（无子女的离婚可以不填）。")
        return ""

    def _refresh_conditional(self):
        _set_status(self.cond_hint, self._conditional_issue())
        self.completeChanged.emit()

    def isComplete(self):
        if not super().isComplete():
            return False
        return not self._conditional_issue()

    def validatePage(self):
        issue = self._conditional_issue()
        if issue:
            _set_status(self.cond_hint, issue)
            self.child_name.setFocus()
            return False
        return True
