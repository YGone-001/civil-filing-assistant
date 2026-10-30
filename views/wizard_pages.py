# File: views/wizard_pages.py
# Purpose: Compatibility facade for the modularized wizard page package.
# Encoding: UTF-8
"""Compatibility facade over :mod:`views.pages`.

The wizard page classes and their shared helpers were extracted into the
``views/pages/`` package (one cohesive module per page plus the shared
``common``/``base`` modules). This module remains the stable import path for
existing consumers — it re-exports the real classes and helpers and contains
no UI implementation of its own. New code should import from the owning
``views.pages`` module directly.
"""

from views.pages.base import _TitledPage  # noqa: F401  (compatibility re-export)
from views.pages.case_selection import CaseSelectionPage  # noqa: F401
from views.pages.common import (  # noqa: F401  (compatibility re-exports)
    _DECIMAL_INPUT_PATTERN,
    _PHONE_INPUT_PATTERN,
    _TwoColumnForm,
    _decimal_validator,
    _dedup_messages,
    _section,
    _set_form_accessibility,
    _set_label_field_accessibility,
    _set_page_form_accessibility,
    _set_status,
    _wrap_in_scroll,
)
from views.pages.contract import ContractClaimPage  # noqa: F401
from views.pages.divorce import DivorceClaimPage  # noqa: F401
from views.pages.evidence import EvidencePage  # noqa: F401
from views.pages.export import ExportPage, _PreviewDialog  # noqa: F401
from views.pages.labor import LaborClaimPage  # noqa: F401
from views.pages.loan import LoanClaimPage  # noqa: F401
from views.pages.party import PartyPage  # noqa: F401
from views.pages.property import PropertyClaimPage  # noqa: F401
from views.pages.welcome import WelcomePage  # noqa: F401
