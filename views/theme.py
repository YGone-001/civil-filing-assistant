# File: views/theme.py
# Purpose: Centralized visual theme (colors, spacing, typography, QSS)
# Encoding: UTF-8
"""Single source of truth for the application's look and feel.

Pages must not sprinkle inline colours or font sizes. Instead they set a
semantic ``objectName`` on their widgets (e.g. ``WARNING_LABEL``) and this
module's global stylesheet provides the visual treatment. This keeps the palette
cohesive, restrained and accessible across every wizard page.

Design language ("静谧法务"): a single deep teal-blue accent over cool slate
neutrals, a consistent Chinese UI font stack, generous spacing and soft radii.
The look stays calm and trustworthy for an offline legal-document tool rather
than flashy.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# --------------------------------------------------------------------------- #
# Semantic color tokens (low-saturation, single accent)
# --------------------------------------------------------------------------- #

COLOR_PRIMARY = "#12677A"          # main buttons, active step, links
COLOR_PRIMARY_HOVER = "#0E5262"
COLOR_PRIMARY_HOVER_SOFT = "#15708C"  # gentle hover lift for solid buttons
COLOR_PRIMARY_SOFT = "#E8F1F5"     # primary-tinted surface
COLOR_SECONDARY_BG = "#F1F4F7"     # secondary buttons / muted surfaces
COLOR_SECONDARY_BORDER = "#C7D2DB"

COLOR_DANGER = "#B42318"           # destructive actions, errors
COLOR_DANGER_HOVER = "#8E1C13"
COLOR_WARNING = "#A86405"          # reminders / cautions
COLOR_WARNING_BG = "#FBF3E4"
COLOR_REMINDER = "#5F4B8B"         # non-blocking action reminders
COLOR_REMINDER_BG = "#F1EDF8"
COLOR_ERROR = "#B42318"
COLOR_ERROR_BG = "#FBEEEC"
COLOR_SUCCESS = "#2F7D4F"
COLOR_SUCCESS_BG = "#EAF4EE"
COLOR_INFO = "#12677A"
COLOR_INFO_BG = "#E8F1F5"

COLOR_TEXT = "#1B2530"             # primary text
COLOR_TEXT_MUTED = "#5B6B7A"       # secondary text / captions
COLOR_BORDER = "#D7DFE7"
COLOR_DIVIDER = "#E8EDF2"
COLOR_BACKGROUND = "#F7F9FB"
COLOR_SUGGESTED_ROW_BG = "#F5F8FC"
COLOR_WHITE = "#FFFFFF"

# --------------------------------------------------------------------------- #
# Typography / spacing / radius tokens
# --------------------------------------------------------------------------- #

FONT_FAMILY = (
    '"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", '
    '"Noto Sans CJK SC", "Source Han Sans SC", sans-serif'
)

FONT_SIZE_TITLE = 18
FONT_SIZE_SUBTITLE = 16
FONT_SIZE_BODY = 14
FONT_SIZE_CAPTION = 12

SPACING_XS = 2
SPACING_SM = 4
SPACING_MD = 8
SPACING_LG = 16
SPACING_XL = 24

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

# Layout: every page's content lives in a single centered column capped at this
# width. Wide windows keep readable line lengths instead of stretching each
# input field edge-to-edge across the whole wizard.
CONTENT_MAX_WIDTH = 960

# --------------------------------------------------------------------------- #
# Semantic objectName identifiers (used by APP_STYLESHEET)
# --------------------------------------------------------------------------- #

PRIMARY_BUTTON = "primaryButton"
SECONDARY_BUTTON = "secondaryButton"
DANGER_BUTTON = "dangerButton"

INFO_LABEL = "infoLabel"
REMINDER_LABEL = "reminderLabel"
WARNING_LABEL = "warningLabel"
ERROR_LABEL = "errorLabel"
SUCCESS_LABEL = "successLabel"

DEMO_BADGE = "demoBadge"
STEP_INDICATOR = "stepIndicator"
STEP_CHIP = "stepChip"
STEP_CONNECTOR = "stepConnector"
CASE_CONTEXT_LABEL = "caseContextLabel"
DOC_CARD = "docCard"
DOC_CARD_ICON = "docCardIcon"
DOC_CARD_TITLE = "docCardTitle"
DOC_CARD_DESC = "docCardDesc"
CASE_CARD = "caseCard"
CASE_CARD_SELECTED = "caseCardSelected"
CASE_CARD_BADGE = "caseCardBadge"
CASE_CARD_TITLE = "caseCardTitle"
CASE_CARD_DESC = "caseCardDesc"
PAGE_LEAD = "pageLead"
SECTION_LABEL = "sectionLabel"
SECTION_BOX = "sectionBox"
PAGE_CONTENT_COLUMN = "pageContentColumn"
PAGE_TITLE_LABEL = "pageTitleLabel"

# --------------------------------------------------------------------------- #
# Global stylesheet
# --------------------------------------------------------------------------- #

APP_STYLESHEET = f"""
QWidget {{
    color: {COLOR_TEXT};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_BODY}px;
}}

QWidget#wizardBody {{
    background-color: {COLOR_BACKGROUND};
}}

/* ---- Wizard header (title / subtitle) ---- */
QWizard {{
    background-color: {COLOR_BACKGROUND};
}}

QWizard QLabel#qt_wizard_title {{
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}

QWizard QLabel#qt_wizard_subtitle {{
    font-size: {FONT_SIZE_CAPTION}px;
    color: {COLOR_TEXT_MUTED};
}}

/* ---- In-column page heading ----------------------------------------------
   Qt's ModernStyle draws the page title in a full-width banner that cannot be
   inset to match the centered content column, so the banner is suppressed and
   the heading is rendered as this label inside the column instead. The type
   scale matches the banner it replaces. */
QLabel#pageTitleLabel {{
    font-size: {FONT_SIZE_TITLE}px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}

/* ---- Base input controls ---- */
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QTableWidget {{
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px {SPACING_MD}px;
    background-color: {COLOR_WHITE};
    selection-background-color: {COLOR_PRIMARY};
    selection-color: {COLOR_WHITE};
    color: {COLOR_TEXT};
}}

QLineEdit:hover, QComboBox:hover, QTextEdit:hover, QPlainTextEdit:hover,
QTableWidget:hover {{
    border-color: {COLOR_SECONDARY_BORDER};
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
QTableWidget:focus {{
    border: 1px solid {COLOR_PRIMARY};
    background-color: {COLOR_WHITE};
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    background-color: {COLOR_PRIMARY_SOFT};
}}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    color: {COLOR_TEXT_MUTED};
    background-color: {COLOR_SECONDARY_BG};
}}

/* Combo box drop-down (keep the default arrow, just clean the chrome). */
QComboBox::drop-down {{
    border: none;
    width: {SPACING_XL}px;
}}

QComboBox QAbstractItemView {{
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    background-color: {COLOR_WHITE};
    selection-background-color: {COLOR_PRIMARY_SOFT};
    selection-color: {COLOR_TEXT};
    outline: none;
}}

/* ---- Checkboxes / radio buttons ---- */
QCheckBox, QRadioButton {{
    spacing: {SPACING_MD}px;
    color: {COLOR_TEXT};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_SECONDARY_BORDER};
    border-radius: 4px;
    background-color: {COLOR_WHITE};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_PRIMARY};
}}

QCheckBox::indicator:checked {{
    border-color: {COLOR_PRIMARY};
    background-color: {COLOR_PRIMARY};
}}

QCheckBox::indicator:disabled {{
    border-color: {COLOR_BORDER};
    background-color: {COLOR_SECONDARY_BG};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_SECONDARY_BORDER};
    border-radius: 8px;
    background-color: {COLOR_WHITE};
}}

QRadioButton::indicator:hover {{
    border-color: {COLOR_PRIMARY};
}}

QRadioButton::indicator:checked {{
    border: 5px solid {COLOR_PRIMARY};
    background-color: {COLOR_WHITE};
}}

QRadioButton::indicator:disabled {{
    border-color: {COLOR_BORDER};
    background-color: {COLOR_SECONDARY_BG};
}}

/* ---- Group boxes ---- */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_MD}px;
    margin-top: {SPACING_LG}px;
    padding-top: {SPACING_LG}px;
    background-color: {COLOR_WHITE};
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {SPACING_LG}px;
    padding: 0 {SPACING_SM}px;
    color: {COLOR_TEXT};
}}

/* Numbered form sections keep a subtle primary accent on their headings. */
QGroupBox#{SECTION_BOX}::title {{
    color: {COLOR_PRIMARY};
    font-weight: 700;
}}

/* ---- Buttons: default (secondary) / primary / danger ---- */
QPushButton {{
    border: 1px solid {COLOR_SECONDARY_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px {SPACING_LG}px;
    min-height: 20px;
    background-color: {COLOR_WHITE};
    color: {COLOR_TEXT};
}}

QPushButton:hover {{
    border-color: {COLOR_PRIMARY};
    background-color: {COLOR_PRIMARY_SOFT};
}}

QPushButton:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {COLOR_SECONDARY_BG};
}}

QPushButton:disabled {{
    color: {COLOR_TEXT_MUTED};
    background-color: {COLOR_SECONDARY_BG};
    border-color: {COLOR_BORDER};
}}

QPushButton#{PRIMARY_BUTTON} {{
    background-color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
    color: {COLOR_WHITE};
    font-weight: 600;
    padding: {SPACING_MD}px {SPACING_XL}px;
}}

QPushButton#{PRIMARY_BUTTON}:hover {{
    background-color: {COLOR_PRIMARY_HOVER_SOFT};
    border-color: {COLOR_PRIMARY_HOVER_SOFT};
}}

QPushButton#{PRIMARY_BUTTON}:pressed {{
    background-color: {COLOR_PRIMARY_HOVER};
    border-color: {COLOR_PRIMARY_HOVER};
}}

QPushButton#{PRIMARY_BUTTON}:disabled {{
    background-color: {COLOR_SECONDARY_BG};
    border-color: {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
}}

QPushButton#{DANGER_BUTTON} {{
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_DANGER};
    color: {COLOR_DANGER};
}}

QPushButton#{DANGER_BUTTON}:hover {{
    background-color: {COLOR_ERROR_BG};
    border-color: {COLOR_DANGER};
}}

QPushButton#{DANGER_BUTTON}:pressed {{
    background-color: {COLOR_DANGER};
    color: {COLOR_WHITE};
}}

/* ---- Status labels ---- */
QLabel#{INFO_LABEL}, QLabel#{REMINDER_LABEL}, QLabel#{WARNING_LABEL},
QLabel#{ERROR_LABEL}, QLabel#{SUCCESS_LABEL} {{
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px {SPACING_LG}px;
}}

QLabel#{INFO_LABEL} {{
    color: {COLOR_INFO};
    background-color: {COLOR_INFO_BG};
    border: 1px solid {COLOR_BORDER};
    border-left: 3px solid {COLOR_INFO};
}}

QLabel#{REMINDER_LABEL} {{
    color: {COLOR_REMINDER};
    background-color: {COLOR_REMINDER_BG};
    border: 1px solid {COLOR_BORDER};
    border-left: 3px solid {COLOR_REMINDER};
}}

QLabel#{WARNING_LABEL} {{
    color: {COLOR_WARNING};
    background-color: {COLOR_WARNING_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-left: 3px solid {COLOR_WARNING};
}}

QLabel#{ERROR_LABEL} {{
    color: {COLOR_ERROR};
    background-color: {COLOR_ERROR_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-left: 3px solid {COLOR_ERROR};
}}

QLabel#{SUCCESS_LABEL} {{
    color: {COLOR_SUCCESS};
    background-color: {COLOR_SUCCESS_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-left: 3px solid {COLOR_SUCCESS};
}}

/* ---- Demo-mode badge ---- */
QLabel#{DEMO_BADGE} {{
    color: {COLOR_WARNING};
    background-color: {COLOR_WARNING_BG};
    border: 1px solid {COLOR_WARNING};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_SM}px {SPACING_MD}px;
    font-weight: 600;
    font-size: {FONT_SIZE_CAPTION}px;
}}

/* ---- Step indicator ---- */
QWidget#{STEP_INDICATOR} {{
    background: transparent;
}}

QLabel#{STEP_CHIP} {{
    color: {COLOR_TEXT_MUTED};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_LG}px;
    padding: {SPACING_XS}px {SPACING_LG}px;
    background-color: {COLOR_WHITE};
}}

QLabel#{STEP_CHIP}[stepState="current"] {{
    color: {COLOR_WHITE};
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
    font-weight: 600;
}}

QLabel#{STEP_CHIP}[stepState="done"] {{
    color: {COLOR_INFO};
    border-color: {COLOR_BORDER};
    background-color: {COLOR_PRIMARY_SOFT};
}}

QLabel#{STEP_CONNECTOR} {{
    background-color: {COLOR_BORDER};
    border: none;
    border-radius: 1px;
}}

QLabel#{STEP_CONNECTOR}[stepState="done"] {{
    background-color: {COLOR_PRIMARY};
}}

QLabel#{CASE_CONTEXT_LABEL} {{
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
    padding: 0 {SPACING_SM}px;
}}

/* ---- Document cards ---- */
QWidget#{DOC_CARD} {{
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    border-left: 3px solid {COLOR_PRIMARY};
    border-radius: {RADIUS_MD}px;
    padding: {SPACING_MD}px;
}}

QLabel#{DOC_CARD_ICON} {{
    font-size: {FONT_SIZE_SUBTITLE}px;
    font-weight: 700;
    color: {COLOR_PRIMARY};
    background-color: {COLOR_PRIMARY_SOFT};
    border-radius: {RADIUS_SM}px;
}}

QLabel#{DOC_CARD_TITLE} {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}

QLabel#{DOC_CARD_DESC} {{
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
}}

/* ---- Page lead (intro subtitle) ---- */
QLabel#{PAGE_LEAD} {{
    font-size: {FONT_SIZE_BODY}px;
    color: {COLOR_TEXT_MUTED};
}}

/* ---- Section heading (party/group labels) ---- */
QLabel#{SECTION_LABEL} {{
    font-size: {FONT_SIZE_BODY}px;
    font-weight: 700;
    color: {COLOR_PRIMARY};
}}

/* ---- Case selection cards ---- */
QPushButton#{CASE_CARD} {{
    text-align: left;
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    border-left: 3px solid {COLOR_BORDER};
    border-radius: {RADIUS_MD}px;
    padding: {SPACING_MD}px {SPACING_LG}px;
    min-height: 44px;
    color: {COLOR_TEXT};
}}

QPushButton#{CASE_CARD}:hover {{
    border-color: {COLOR_PRIMARY};
    border-left: 4px solid {COLOR_PRIMARY};
    background-color: {COLOR_PRIMARY_SOFT};
}}

QPushButton#{CASE_CARD}[caseCardSelected="true"] {{
    border: 1px solid {COLOR_PRIMARY};
    border-left: 4px solid {COLOR_PRIMARY};
    background-color: {COLOR_PRIMARY_SOFT};
}}

QLabel#{CASE_CARD_BADGE} {{
    background-color: {COLOR_SECONDARY_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_SUBTITLE}px;
    font-weight: 700;
}}

QPushButton#{CASE_CARD}[caseCardSelected="true"] QLabel#{CASE_CARD_BADGE} {{
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
    color: {COLOR_WHITE};
}}

QLabel#{CASE_CARD_TITLE} {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}

QLabel#{CASE_CARD_DESC} {{
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
}}

/* ---- Tables ---- */
QTableWidget {{
    gridline-color: {COLOR_DIVIDER};
    alternate-background-color: {COLOR_BACKGROUND};
}}

QHeaderView::section {{
    background-color: {COLOR_SECONDARY_BG};
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: {SPACING_SM}px {SPACING_MD}px;
    color: {COLOR_TEXT};
    font-weight: 600;
}}

QTableWidget::item:selected {{
    background-color: {COLOR_PRIMARY_SOFT};
    color: {COLOR_TEXT};
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: {SPACING_XS}px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_SECONDARY_BORDER};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_MUTED};
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: {SPACING_XS}px;
}}

QScrollBar::handle:horizontal {{
    background: {COLOR_SECONDARY_BORDER};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_TEXT_MUTED};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---- Tooltips ---- */
QToolTip {{
    background-color: {COLOR_TEXT};
    color: {COLOR_WHITE};
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_SM}px {SPACING_MD}px;
}}
"""


def apply_theme(app):
    """Apply the global stylesheet and font stack to the running ``QApplication``."""
    if not isinstance(app, QApplication):
        raise TypeError("apply_theme expects a QApplication instance")

    font = QFont()
    font.setFamilies(
        ["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
         "Noto Sans CJK SC", "Source Han Sans SC"]
    )
    app.setFont(font)
    app.setStyleSheet(APP_STYLESHEET)