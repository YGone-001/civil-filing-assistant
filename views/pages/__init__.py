# File: views/pages/__init__.py
# Purpose: Cohesive PySide6 wizard page package (one module per page).
# Encoding: UTF-8
"""Modularized wizard pages.

``common`` holds the shared form/status/accessibility/layout helpers,
``base`` the titled wizard-page base class, and each remaining module one
page (``export`` owns the export page and its preview dialog).
``views/wizard_pages.py`` stays as the compatibility facade for existing
imports; new code should import from the owning module directly.
"""
