# File: tests/test_page_module_imports.py
# Purpose: Fresh-process import integrity for the modularized page package.
# Encoding: UTF-8
"""P3A-10: every new page module imports in a fresh Python process, without a
QApplication and without an initialized wizard, alongside the compatibility
facade and the composition root."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MODULES = (
    "views.main_window",
    "views.wizard_pages",
    "views.pages",
    "views.pages.common",
    "views.pages.base",
    "views.pages.welcome",
    "views.pages.case_selection",
    "views.pages.party",
    "views.pages.loan",
    "views.pages.contract",
    "views.pages.property",
    "views.pages.labor",
    "views.pages.divorce",
    "views.pages.evidence",
    "views.pages.export",
)


def test_all_page_modules_import_in_a_fresh_process():
    script = "import importlib\n"
    script += "".join(f"importlib.import_module({name!r})\n" for name in MODULES)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
