# File: tests/conftest.py
# Purpose: pytest fixtures for GUI, isolation and dialog suppression.
# Encoding: UTF-8

import os

# Must be set before any Qt module is imported.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """A single offscreen QApplication shared by all GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def dialog_recorder(monkeypatch, qapp):
    """Suppress and record modal dialogs so GUI tests never block.

    Tests can request this fixture by name to inspect the recorded calls.
    """
    recorded = []

    def _make(kind):
        def _fake(*args, **kwargs):
            recorded.append({"kind": kind, "args": args, "kwargs": kwargs})
            return QMessageBox.Ok

        return _fake

    for kind in ("information", "warning", "critical", "question"):
        monkeypatch.setattr(QMessageBox, kind, _make(kind))
    return recorded


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    """Redirect the user home directory so exports never touch the real desktop."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HOMEDRIVE", "")
    monkeypatch.setenv("HOMEPATH", "")
    return home
