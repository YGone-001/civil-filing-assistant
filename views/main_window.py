# File: views/main_window.py
# Purpose: Main application window integrating the Wizard
# Encoding: UTF-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFormLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizard,
)

from presenters.model_builder import is_supported_case_type
from views.theme import PAGE_CONTENT_COLUMN, PRIMARY_BUTTON, SECONDARY_BUTTON
from views.widgets import CASE_TYPE_LABELS, DraftActionBar, StepIndicator, page_title
from views.wizard_pages import (
    WelcomePage,
    CaseSelectionPage,
    PartyPage,
    LoanClaimPage,
    ContractClaimPage,
    PropertyClaimPage,
    LaborClaimPage,
    DivorceClaimPage,
    EvidencePage,
    ExportPage,
)


class LawsuitWizard(QWizard):
    #: Emitted when the user clicks 保存草稿 on any page's action bar.
    save_draft_requested = Signal()
    #: Emitted when the user clicks 打开草稿 on any page's action bar.
    open_draft_requested = Signal()

    def __init__(self, demo_mode=False):
        super().__init__()
        self.setObjectName("wizardBody")
        self.setWindowTitle("民事立案文书助手（离线版）")
        # A ~5:4 form-oriented ratio: wide enough for two-column form pages and
        # the case-selection list, tall enough to keep claim/fact pages readable
        # with minimal scrolling.
        # Responsive default geometry: fit comfortably on 1366x768 laptops
        # (taskbar and title bar leave roughly 1366x700 usable) and grow on
        # larger displays instead of opening taller than the screen. Pages
        # scroll vertically, so a smaller window stays fully usable.
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        default_width, default_height = 1180, 800
        if available is not None and available.isValid():
            default_width = min(default_width, int(available.width() * 0.92))
            default_height = min(default_height, int(available.height() * 0.9))
        self.resize(default_width, default_height)
        self.setMinimumSize(960, 620)
        self.setWizardStyle(QWizard.ModernStyle)

        # Replace the stock English navigation labels with Chinese text. The
        # Export page's primary action is phrased around the three Word drafts.
        # QWizard's built-in navigation buttons ignore application QSS on
        # Windows, so each built-in role is replaced with an ordinary styled
        # QPushButton (theme objectNames); setButton() re-wires the built-in
        # behaviour for these roles (Back/Next/Finish/Cancel).
        for role, text, object_name in (
            (QWizard.BackButton, "上一步", SECONDARY_BUTTON),
            (QWizard.NextButton, "下一步", PRIMARY_BUTTON),
            (QWizard.FinishButton, "生成三份 Word 初稿", PRIMARY_BUTTON),
            (QWizard.CancelButton, "退出", SECONDARY_BUTTON),
        ):
            button = QPushButton(text)
            button.setObjectName(object_name)
            self.setButton(role, button)

        # Qt's QWizard creates an internal, unnamed 32x32 QAbstractButton at the
        # top-left of the header area. On Windows it renders as a stray "back"
        # arrow overlapping the page title, and it has no function here because
        # navigation is provided by the standard Back/Next/Cancel bar. Hide it
        # (and keep it hidden across page changes) without touching the real
        # navigation buttons, which are not direct children of the wizard.
        for child in self.children():
            if isinstance(child, QAbstractButton) and not child.text() and not child.objectName():
                child.hide()
        self.currentIdChanged.connect(self._hide_internal_wizard_buttons)

        # Define Page IDs
        self.PAGE_WELCOME = 0
        self.PAGE_CASE_SELECTION = 1
        self.PAGE_PARTY = 2
        self.PAGE_LOAN_CLAIM = 3
        self.PAGE_CONTRACT_CLAIM = 4
        self.PAGE_PROPERTY_CLAIM = 5
        self.PAGE_LABOR_CLAIM = 6
        self.PAGE_DIVORCE_CLAIM = 7
        self.PAGE_EVIDENCE = 8
        self.PAGE_EXPORT = 9

        # Add pages
        self.welcome_page = WelcomePage()
        self.case_selection_page = CaseSelectionPage()
        self.party_page = PartyPage()
        self.loan_claim_page = LoanClaimPage()
        self.contract_claim_page = ContractClaimPage()
        self.property_claim_page = PropertyClaimPage()
        self.labor_claim_page = LaborClaimPage()
        self.divorce_claim_page = DivorceClaimPage()
        self.evidence_page = EvidencePage()
        self.export_page = ExportPage()

        self.setPage(self.PAGE_WELCOME, self.welcome_page)
        self.setPage(self.PAGE_CASE_SELECTION, self.case_selection_page)
        self.setPage(self.PAGE_PARTY, self.party_page)
        self.setPage(self.PAGE_LOAN_CLAIM, self.loan_claim_page)
        self.setPage(self.PAGE_CONTRACT_CLAIM, self.contract_claim_page)
        self.setPage(self.PAGE_PROPERTY_CLAIM, self.property_claim_page)
        self.setPage(self.PAGE_LABOR_CLAIM, self.labor_claim_page)
        self.setPage(self.PAGE_DIVORCE_CLAIM, self.divorce_claim_page)
        self.setPage(self.PAGE_EVIDENCE, self.evidence_page)
        self.setPage(self.PAGE_EXPORT, self.export_page)

        # The five-step indicator maps every wizard page to its step. The
        # welcome page is a landing page and therefore shows no indicator.
        self.STEP_OF_PAGE = {
            self.PAGE_CASE_SELECTION: 1,
            self.PAGE_PARTY: 2,
            self.PAGE_LOAN_CLAIM: 3,
            self.PAGE_CONTRACT_CLAIM: 3,
            self.PAGE_PROPERTY_CLAIM: 3,
            self.PAGE_LABOR_CLAIM: 3,
            self.PAGE_DIVORCE_CLAIM: 3,
            self.PAGE_EVIDENCE: 4,
            self.PAGE_EXPORT: 5,
        }
        self._step_indicators = []
        for page_id, page in (
            (self.PAGE_CASE_SELECTION, self.case_selection_page),
            (self.PAGE_PARTY, self.party_page),
            (self.PAGE_LOAN_CLAIM, self.loan_claim_page),
            (self.PAGE_CONTRACT_CLAIM, self.contract_claim_page),
            (self.PAGE_PROPERTY_CLAIM, self.property_claim_page),
            (self.PAGE_LABOR_CLAIM, self.labor_claim_page),
            (self.PAGE_DIVORCE_CLAIM, self.divorce_claim_page),
            (self.PAGE_EVIDENCE, self.evidence_page),
            (self.PAGE_EXPORT, self.export_page),
        ):
            self._attach_step_indicator(page, self.STEP_OF_PAGE[page_id])

        # Render each page's heading inside its centered content column so it
        # shares the form's left edge, replacing the full-width ModernStyle
        # banner that could not be inset. Done after the step strip so the
        # heading lands above it in the column. The draft action bar is
        # appended to the same column, under the page content.
        self._draft_bars = []
        for page in (
            self.welcome_page,
            self.case_selection_page,
            self.party_page,
            self.loan_claim_page,
            self.contract_claim_page,
            self.property_claim_page,
            self.labor_claim_page,
            self.divorce_claim_page,
            self.evidence_page,
            self.export_page,
        ):
            self._attach_page_title(page)
            self._attach_draft_bar(page)

        self.currentIdChanged.connect(self._update_step_indicators)
        self.case_selection_page.case_combo.currentIndexChanged.connect(
            self._update_step_indicators
        )

        # Set start page
        self.setStartId(self.PAGE_WELCOME)

        # The presenter registers a Finish handler that performs the export
        # before the wizard commits to its accepted (closed) state.
        self.finish_handler = None

        # Demo-mode plumbing: test-data entry points are hidden in production
        # and only exposed by an explicit --demo launch argument.
        self.demo_mode = bool(demo_mode)
        self.welcome_page.set_demo_mode(self.demo_mode)
        self.property_claim_page.set_demo_mode(self.demo_mode)

        # Connect the (demo-only) welcome-page fill button to the guarded path.
        self.welcome_page.fill_btn.clicked.connect(self._demo_fill)
        self.property_claim_page.fill_btn.clicked.connect(self._demo_fill)
        self._update_step_indicators()

    # ------------------------------------------------------------------ #
    # Step indicator
    # ------------------------------------------------------------------ #

    def _attach_step_indicator(self, page, step):
        indicator = StepIndicator()
        # Prefer the page's centered content column so the step strip shares the
        # same left edge as the form; fall back to the raw page layout.
        holder = page.findChild(QWidget, PAGE_CONTENT_COLUMN)
        layout = holder.layout() if holder is not None else page.layout()
        if isinstance(layout, QFormLayout):
            layout.insertRow(0, indicator)
        elif isinstance(layout, QVBoxLayout):
            layout.insertWidget(0, indicator)
        else:
            return None
        self._step_indicators.append(indicator)
        return indicator

    def _attach_page_title(self, page):
        """Insert the page heading at the top of its centered content column.

        Mirrors :meth:`_attach_step_indicator`'s column lookup so the visible
        heading and the step strip share one left edge.
        """
        holder = page.findChild(QWidget, PAGE_CONTENT_COLUMN)
        layout = holder.layout() if holder is not None else page.layout()
        heading = page_title(page.title())
        if isinstance(layout, QFormLayout):
            layout.insertRow(0, heading)
        elif isinstance(layout, QVBoxLayout):
            layout.insertWidget(0, heading)

    def _attach_draft_bar(self, page):
        """Append the 保存草稿 / 打开草稿 actions to *page*'s content column.

        One bar per page (rather than one global button in QWizard's button
        box) keeps the actions visible on every step while leaving their
        ownership to the ordinary layout rules used everywhere else in the
        application.
        """
        holder = page.findChild(QWidget, PAGE_CONTENT_COLUMN)
        layout = holder.layout() if holder is not None else page.layout()
        if not isinstance(layout, (QVBoxLayout, QFormLayout)):
            return None
        bar = DraftActionBar()
        bar.save_button.clicked.connect(self.save_draft_requested.emit)
        bar.open_button.clicked.connect(self.open_draft_requested.emit)
        if isinstance(layout, QFormLayout):
            layout.addRow(bar)
        else:
            layout.addWidget(bar)
        self._draft_bars.append((page, bar))
        return bar

    def _current_draft_bar(self):
        """Return the draft action bar of the page currently shown."""
        current = self.currentPage()
        for page, bar in self._draft_bars:
            if page is current:
                return bar
        return self._draft_bars[0][1] if self._draft_bars else None

    @property
    def save_draft_button(self):
        """The 保存草稿 button on the current page."""
        bar = self._current_draft_bar()
        return bar.save_button if bar is not None else None

    @property
    def open_draft_button(self):
        """The 打开草稿 button on the current page."""
        bar = self._current_draft_bar()
        return bar.open_button if bar is not None else None

    def _update_step_indicators(self, *_):
        current = self.currentId()
        step = self.STEP_OF_PAGE.get(current, 0)
        case_type = self.field("case_type")
        # Guard against non-string/unhashable field values: this slot runs on
        # every currentIdChanged and must never raise inside the Qt callback.
        case_label = CASE_TYPE_LABELS.get(case_type, "") if is_supported_case_type(case_type) else ""
        for indicator in self._step_indicators:
            indicator.set_current(step)
            indicator.set_case_label(case_label)

    # ------------------------------------------------------------------ #
    # Qt wizard plumbing
    # ------------------------------------------------------------------ #

    def _hide_internal_wizard_buttons(self, *_):
        """Keep Qt's internal header button hidden across page changes."""
        for child in self.children():
            if isinstance(child, QAbstractButton) and not child.text() and not child.objectName():
                child.hide()

    def nextId(self):
        current = self.currentId()
        if current == self.PAGE_WELCOME:
            return self.PAGE_CASE_SELECTION

        elif current == self.PAGE_CASE_SELECTION:
            return self.PAGE_PARTY

        elif current == self.PAGE_PARTY:
            case_type = self.field("case_type")
            if not is_supported_case_type(case_type):
                # Fail closed: an unknown (or unhashable) identifier must never
                # fall through to the loan claim page; send the user back to
                # the case selection page so they can pick a supported
                # category again.
                return self.PAGE_CASE_SELECTION
            if case_type == "contract":
                return self.PAGE_CONTRACT_CLAIM
            elif case_type == "property":
                return self.PAGE_PROPERTY_CLAIM
            elif case_type == "labor":
                return self.PAGE_LABOR_CLAIM
            elif case_type == "divorce":
                return self.PAGE_DIVORCE_CLAIM
            else:
                return self.PAGE_LOAN_CLAIM

        elif current == self.PAGE_LOAN_CLAIM or current == self.PAGE_CONTRACT_CLAIM or current == self.PAGE_PROPERTY_CLAIM or current == self.PAGE_LABOR_CLAIM or current == self.PAGE_DIVORCE_CLAIM:
            return self.PAGE_EVIDENCE

        elif current == self.PAGE_EVIDENCE:
            return self.PAGE_EXPORT

        elif current == self.PAGE_EXPORT:
            return -1

        return super().nextId()

    def set_finish_handler(self, handler):
        """Register the pre-accept export step supplied by the presenter."""
        self.finish_handler = handler

    def accept(self):
        """Run the export before accepting, so a failure keeps the wizard open.

        The real QWizard "Finish" button routes through this method. Only a
        successful export advances to Qt's normal accepted (closed) state.
        """
        handler = getattr(self, "finish_handler", None)
        if callable(handler) and not handler():
            return  # keep the wizard open so the user can correct and retry
        super().accept()

    # ------------------------------------------------------------------ #
    # Demo / test-data filling
    # ------------------------------------------------------------------ #

    def _has_entered_data(self):
        if (
            self.party_page._has_named_party(self.party_page.plaintiff_widgets)
            or self.party_page._has_named_party(self.party_page.defendant_widgets)
        ):
            return True

        # The property-page demo action is available after users may have
        # entered case facts. Inspect the active branch too, without treating
        # fixed defaults such as the contract LPR reference value as user data.
        fields_by_case = {
            "loan": (
                self.loan_claim_page,
                ("loan_date", "loan_reason", "principal", "payment_method", "rate",
                 "start_date", "demand_date", "demand_method", "court_name"),
            ),
            "contract": (
                self.contract_claim_page,
                ("contract_date", "contract_name", "product_name", "total_amount",
                 "delivery_date", "unpaid_amount", "penalty_amount", "overdue_start",
                 "overdue_end", "court_name"),
            ),
            "property": (
                self.property_claim_page,
                ("property_addr", "house_area", "fee_rate", "period_start", "period_end",
                 "late_fee_logic", "demand_record", "total_input", "court_name"),
            ),
            "labor": (
                self.labor_claim_page,
                ("emp_join_date", "job_title", "monthly_salary", "unpaid_months",
                 "emp_term_date", "overtime_hours", "overtime_pay", "social_sec_info",
                 "court_name"),
            ),
            "divorce": (
                self.divorce_claim_page,
                ("marriage_date", "child_name", "child_birthday", "custody_preference",
                 "support_monthly", "divorce_reason", "separation_start_date",
                 "asset_description", "court_name"),
            ),
        }
        page_and_fields = fields_by_case.get(self.field("case_type"))
        if not page_and_fields:
            return False
        page, field_names = page_and_fields
        for name in field_names:
            widget = getattr(page, name)
            value = (
                widget.toPlainText()
                if hasattr(widget, "toPlainText")
                else widget.text()
            )
            if value.strip():
                return True
        return False

    def _demo_fill(self):
        """Guard the test-data entry behind a confirmation before overwriting."""
        if self._has_entered_data():
            answer = QMessageBox.question(
                self,
                "覆盖确认",
                "检测到已填写的案件信息。是否用演示数据覆盖当前内容？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        # Ensure a case type is selected so the fill covers a complete branch.
        if not self.field("case_type"):
            self.case_selection_page.case_combo.setCurrentIndex(0)
        self.fill_template_data()

    def fill_template_data(self):
        """Auto-fill data for testing purposes"""
        # Get current case type
        case_type = self.field("case_type")

        # Page 1: Party Info
        if self.party_page.plaintiff_widgets:
            self.party_page.plaintiff_widgets[0]["name"].setText("张三")
            self.party_page.plaintiff_widgets[0]["id"].setText("示例证件号-原告")
            self.party_page.plaintiff_widgets[0]["addr"].setText("北京市朝阳区某某路1号")
            self.party_page.plaintiff_widgets[0]["phone"].setText("示例电话-原告")

        if self.party_page.defendant_widgets:
            self.party_page.defendant_widgets[0]["name"].setText("李四")
            self.party_page.defendant_widgets[0]["id"].setText("示例证件号-被告")
            self.party_page.defendant_widgets[0]["addr"].setText("上海市徐汇区某某街2号")
            self.party_page.defendant_widgets[0]["phone"].setText("示例电话-被告")

        # Page 2: Claim Info - Fill based on case type
        if case_type == "loan":
            self.loan_claim_page.loan_date.setText("2023年1月1日")
            self.loan_claim_page.loan_reason.setText("资金周转")
            self.loan_claim_page.principal.setText("50000")
            self.loan_claim_page.payment_method.setText("银行转账")
            self.loan_claim_page.rate.setText("14.6")
            self.loan_claim_page.start_date.setText("2023-05-01")
            self.loan_claim_page.iou_yes.setChecked(True)
            self.loan_claim_page.demand_date.setText("2023年10月至12月")
            self.loan_claim_page.demand_method.setText("微信及电话")
            self.loan_claim_page.court_name.setText("上海市徐汇区人民法院")

        elif case_type == "contract":
            self.contract_claim_page.contract_date.setText("2023年1月1日")
            self.contract_claim_page.contract_name.setText("产品购销合同")
            self.contract_claim_page.product_name.setText("10台联想电脑")
            self.contract_claim_page.total_amount.setText("50000")
            self.contract_claim_page.delivery_date.setText("2023年2月1日")
            self.contract_claim_page.del_yes.setChecked(True)
            self.contract_claim_page.sign_yes.setChecked(True)
            self.contract_claim_page.unpaid_amount.setText("30000")
            self.contract_claim_page.penalty_amount.setText("5000")
            self.contract_claim_page.overdue_start.setText("2023-03-01")
            self.contract_claim_page.overdue_end.setText("")
            self.contract_claim_page.court_name.setText("上海市徐汇区人民法院")

        elif case_type == "property":
            # The property page owns its own demo setter; reuse it so the two
            # entry points cannot drift apart. Confirmation already happened in
            # _demo_fill(), so fill silently here.
            self.property_claim_page.fill_test_data(notify=False)

        elif case_type == "labor":
            self.labor_claim_page.emp_join_date.setText("2023-01-15")
            self.labor_claim_page.job_title.setText("软件工程师")
            self.labor_claim_page.monthly_salary.setText("8000")
            self.labor_claim_page.unpaid_months.setText("2023年12月至2024年2月")
            self.labor_claim_page.emp_term_date.setText("2024-03-20")
            self.labor_claim_page.overtime_hours.setText("40")
            self.labor_claim_page.overtime_pay.setText("3500")
            self.labor_claim_page.no_contract_no.setChecked(True)
            self.labor_claim_page.social_sec_info.setText("未按实际工资基数缴纳")
            self.labor_claim_page.court_name.setText("北京市朝阳区人民法院")

        elif case_type == "divorce":
            self.divorce_claim_page.marriage_date.setText("2018-05-20")
            self.divorce_claim_page.child_name.setText("张三")
            self.divorce_claim_page.child_birthday.setText("2020-01-01")
            self.divorce_claim_page.custody_preference.setText("由原告抚养")
            self.divorce_claim_page.support_monthly.setText("3000")
            self.divorce_claim_page.divorce_reason.setText("感情不和")
            self.divorce_claim_page.asset_description.setText("房产归原告，车辆归被告")
            self.divorce_claim_page.court_name.setText("北京市朝阳区人民法院")

        # Page 3: Evidence (cleared through the page's own state tracking so a
        # demo fill counts as an explicit clear, not a "reload suggestions" cue).
        self.evidence_page.clear_all_rows()

        QMessageBox.information(self, "提示", "测试数据已自动填入！您可以直接点击下一步查看并生成文档。")
