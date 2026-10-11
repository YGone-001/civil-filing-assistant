# File: views/widgets.py
# Purpose: Small reusable view components shared across wizard pages
# Encoding: UTF-8

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from views.theme import CASE_CONTEXT_LABEL, STEP_CHIP, STEP_CONNECTOR, STEP_INDICATOR

# The five fixed wizard steps (1-based, shown to the user in Chinese).
STEP_NAMES = ["选择案由", "当事人", "案情与请求", "证据", "核对与导出"]

# Case-type labels used for the persistent case context hint. Kept here so the
# wizard and its pages share a single source instead of duplicating the mapping.
CASE_TYPE_LABELS = {
    "loan": "民间借贷纠纷",
    "contract": "买卖合同纠纷",
    "property": "物业服务合同纠纷",
    "labor": "劳动报酬/工资追索",
    "divorce": "离婚纠纷",
}


def _repolish(widget):
    """Force a widget to re-apply its stylesheet after a dynamic property change."""
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)


class StepIndicator(QWidget):
    """A persistent five-step progress strip with a case-context hint.

    The current step is highlighted via the ``stepState`` dynamic property
    (``current`` / ``done`` / ``todo``) matched by the global stylesheet, so no
    colour values appear in the view code itself.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(STEP_INDICATOR)

        chips_layout = QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(4)

        self._chips = []
        self._connectors = []
        for index, name in enumerate(STEP_NAMES, start=1):
            if index > 1:
                connector = QLabel("→")
                connector.setObjectName(STEP_CONNECTOR)
                connector.setProperty("stepState", "todo")
                chips_layout.addWidget(connector)
                self._connectors.append(connector)

            chip = QLabel(f"{index} {name}")
            chip.setObjectName(STEP_CHIP)
            chip.setProperty("stepState", "todo")
            chip.setWordWrap(False)
            chips_layout.addWidget(chip)
            self._chips.append(chip)

        self.case_label = QLabel("")
        self.case_label.setObjectName(CASE_CONTEXT_LABEL)
        self.case_label.setWordWrap(True)
        self.case_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)
        layout.addLayout(chips_layout)
        layout.addWidget(self.case_label)

        self._current = 0

    def set_current(self, index):
        """Highlight step ``index`` (1..5); ``0`` means "not started"."""
        self._current = index
        for position, chip in enumerate(self._chips, start=1):
            if position < index:
                state = "done"
            elif position == index:
                state = "current"
            else:
                state = "todo"
            if chip.property("stepState") != state:
                chip.setProperty("stepState", state)
                _repolish(chip)

        # Connector between step N and N+1 is "done" once step N is completed.
        for position, connector in enumerate(self._connectors, start=1):
            state = "done" if position < index else "todo"
            if connector.property("stepState") != state:
                connector.setProperty("stepState", state)
                _repolish(connector)

        # Connector between step N and N+1 is "done" once step N is completed.
        for position, connector in enumerate(self._connectors, start=1):
            state = "done" if position < index else "todo"
            if connector.property("stepState") != state:
                connector.setProperty("stepState", state)
                _repolish(connector)

    def set_case_label(self, text):
        """Show the current case type, or hide it when empty."""
        self.case_label.setText(text or "")
        self.case_label.setVisible(bool(text))

    def current(self):
        return self._current