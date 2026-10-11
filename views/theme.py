# File: views/theme.py
# Purpose: Centralized visual theme (colors, spacing, typography, QSS)
# Encoding: UTF-8
"""Single source of truth for the application's look and feel.

Pages must not sprinkle inline colours or font sizes anymore. Instead they set
a semantic ``objectName`` on their widgets (e.g. ``WARNING_LABEL``) and this
module's global stylesheet provides the visual treatment. This keeps the palette
cohesive, restrained and accessible across every wizard page.
"""

from PySide6.QtWidgets import QApplication

# --------------------------------------------------------------------------- #
# Semantic color tokens (kept intentionally muted / low-saturation)
# --------------------------------------------------------------------------- #

COLOR_PRIMARY = "#1F5E8C"          # main buttons, active step, links
COLOR_PRIMARY_HOVER = "#1A4F76"
COLOR_SECONDARY_BG = "#F2F5F8"     # secondary buttons
COLOR_SECONDARY_BORDER = "#C6D2DC"

COLOR_DANGER = "#B00020"           # destructive actions, errors
COLOR_DANGER_HOVER = "#8F001A"
COLOR_WARNING = "#B26A00"          # reminders / cautions
COLOR_WARNING_BG = "#FBF3E4"
COLOR_REMINDER = "#6A4C93"         # non-blocking action reminders
COLOR_REMINDER_BG = "#F1ECF7"
COLOR_ERROR = "#B00020"
COLOR_ERROR_BG = "#FBEAEC"
COLOR_SUCCESS = "#2E7D32"
COLOR_SUCCESS_BG = "#E8F5E9"
COLOR_INFO = "#1F5E8C"
COLOR_INFO_BG = "#EAF1F7"

COLOR_TEXT = "#1B2733"             # primary text
COLOR_TEXT_MUTED = "#5A6B7B"       # secondary text / captions
COLOR_BORDER = "#D5DDE5"
COLOR_DIVIDER = "#E5EBF0"
COLOR_BACKGROUND = "#FAFBFD"
COLOR_WHITE = "#FFFFFF"

# --------------------------------------------------------------------------- #
# Typography / spacing / radius tokens
# --------------------------------------------------------------------------- #

FONT_SIZE_TITLE = 16
FONT_SIZE_BODY = 14
FONT_SIZE_CAPTION = 12

SPACING_SM = 4
SPACING_MD = 8
SPACING_LG = 16

RADIUS_SM = 3
RADIUS_MD = 5

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

# --------------------------------------------------------------------------- #
# Global stylesheet
# --------------------------------------------------------------------------- #

APP_STYLESHEET = f"""
QWidget {{
    color: {COLOR_TEXT};
    font-size: {FONT_SIZE_BODY}px;
}}

QWidget#wizardBody {{
    background-color: {COLOR_BACKGROUND};
}}

/* ---- Base input controls ---- */
QLineEdit, QComboBox, QTextEdit, QTableWidget {{
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px {SPACING_MD}px;
    background-color: {COLOR_WHITE};
    selection-background-color: {COLOR_PRIMARY};
    color: {COLOR_TEXT};
}}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QTableWidget:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QRadioButton:focus {{
    border: 1px solid {COLOR_PRIMARY};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_SM}px;
}}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled {{
    color: {COLOR_TEXT_MUTED};
    background-color: {COLOR_SECONDARY_BG};
}}

/* ---- Group boxes ---- */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_MD}px;
    margin-top: {SPACING_LG}px;
    padding-top: {SPACING_LG}px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: {SPACING_LG}px;
    padding: 0 {SPACING_SM}px;
    color: {COLOR_TEXT};
}}

/* ---- Buttons: primary / secondary / danger ---- */
QPushButton {{
    border: 1px solid {COLOR_SECONDARY_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px {SPACING_LG}px;
    background-color: {COLOR_SECONDARY_BG};
    color: {COLOR_TEXT};
}}

QPushButton:hover {{
    border-color: {COLOR_PRIMARY};
    background-color: {COLOR_INFO_BG};
}}

QPushButton:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {COLOR_DIVIDER};
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
}}

QPushButton#{PRIMARY_BUTTON}:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
    border-color: {COLOR_PRIMARY_HOVER};
}}

QPushButton#{PRIMARY_BUTTON}:disabled {{
    background-color: {COLOR_SECONDARY_BG};
    border-color: {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
}}

QPushButton#{DANGER_BUTTON} {{
    background-color: {COLOR_DANGER};
    border: 1px solid {COLOR_DANGER};
    color: {COLOR_WHITE};
}}

QPushButton#{DANGER_BUTTON}:hover {{
    background-color: {COLOR_DANGER_HOVER};
    border-color: {COLOR_DANGER_HOVER};
}}

/* ---- Status labels ---- */
QLabel#{INFO_LABEL} {{
    color: {COLOR_INFO};
    background-color: {COLOR_INFO_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px;
}}

QLabel#{REMINDER_LABEL} {{
    color: {COLOR_REMINDER};
    background-color: {COLOR_REMINDER_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px;
}}

QLabel#{WARNING_LABEL} {{
    color: {COLOR_WARNING};
    background-color: {COLOR_WARNING_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px;
}}

QLabel#{ERROR_LABEL} {{
    color: {COLOR_ERROR};
    background-color: {COLOR_ERROR_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px;
}}

QLabel#{SUCCESS_LABEL} {{
    color: {COLOR_SUCCESS};
    background-color: {COLOR_SUCCESS_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_MD}px;
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
    border-radius: {RADIUS_MD}px;
    padding: {SPACING_SM}px {SPACING_MD}px;
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
    background-color: {COLOR_INFO_BG};
}}

QLabel#{STEP_CONNECTOR} {{
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
    padding: 0 {SPACING_SM}px;
}}

QLabel#{STEP_CONNECTOR}[stepState="done"] {{
    color: {COLOR_INFO};
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
    border-radius: {RADIUS_MD}px;
    padding: {SPACING_MD}px;
}}

QLabel#{DOC_CARD_ICON} {{
    font-size: 24px;
    color: {COLOR_PRIMARY};
}}

QLabel#{DOC_CARD_TITLE} {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}

QLabel#{DOC_CARD_DESC} {{
    color: {COLOR_TEXT_MUTED};
    font-size: {FONT_SIZE_CAPTION}px;
}}

/* ---- Case selection cards ---- */
QPushButton#{CASE_CARD} {{
    text-align: left;
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    border-radius: {RADIUS_MD}px;
    padding: {SPACING_MD}px {SPACING_LG}px;
    color: {COLOR_TEXT};
    font-weight: 600;
}}

QPushButton#{CASE_CARD}:hover {{
    border-color: {COLOR_PRIMARY};
    background-color: {COLOR_INFO_BG};
}}

QPushButton#{CASE_CARD}[caseCardSelected="true"] {{
    border: 2px solid {COLOR_PRIMARY};
    background-color: {COLOR_INFO_BG};
    color: {COLOR_PRIMARY};
}}

/* ---- Tables ---- */
QTableWidget {{
    gridline-color: {COLOR_DIVIDER};
}}

QHeaderView::section {{
    background-color: {COLOR_SECONDARY_BG};
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: {SPACING_SM}px {SPACING_MD}px;
    color: {COLOR_TEXT};
    font-weight: 600;
}}
"""


def apply_theme(app):
    """Apply the global stylesheet to the running ``QApplication``."""
    if not isinstance(app, QApplication):
        raise TypeError("apply_theme expects a QApplication instance")
    app.setStyleSheet(APP_STYLESHEET)
