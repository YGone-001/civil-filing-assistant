# File: views/pages/base.py
# Purpose: Shared titled wizard-page base class.
# Encoding: UTF-8
"""The common base class for every wizard page.

``_TitledPage`` keeps the in-column heading contract (the Qt ``title``
property stays empty so no banner is drawn) and the deliberate
``cleanupPage()`` no-op that preserves entered user data across Back
navigation - a critical data-loss prevention fix that must survive any
future refactor.
"""

from PySide6.QtWidgets import QWizardPage

class _TitledPage(QWizardPage):
    """A wizard page whose heading renders inside the centered content column.

    Qt's ModernStyle draws the page ``title`` in a full-width banner pinned to
    the window edge, which cannot be inset to align with the capped content
    column. The Qt property is therefore left empty (no banner is drawn) and the
    text is remembered here, so ``title()`` and the visible in-column heading
    keep a single source of truth instead of drifting apart.
    """

    def set_page_title(self, text):
        self._page_title = text

    def title(self):
        # QWizard reads the (empty) Qt property through the meta-object, so no
        # banner appears; Python callers still get the real heading text here.
        return getattr(self, "_page_title", "")

    def cleanupPage(self):
        """Keep entered values when the user navigates back.

        ``QWizardPage``'s default ``cleanupPage()`` resets every field
        registered with ``registerField()`` to its initial value, which
        silently erased entered case facts whenever the user pressed 上一步
        and moved forward again. All wizard state lives in the page widgets
        themselves, so leaving it untouched is safe; case-type switches are
        re-handled by ``PartyPage.initializePage()`` and the per-category
        evidence state in ``EvidencePage``.
        """
        return None
