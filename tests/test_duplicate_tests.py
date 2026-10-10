# File: tests/test_duplicate_tests.py
# Purpose: Guard against duplicate test declarations and prove scenario
#          discoverability (C2-T01..C2-T08).
# Encoding: UTF-8

import ast
from pathlib import Path

import pytest

from tools import check_duplicate_tests as cdt

TESTS_DIR = Path(__file__).resolve().parent


def test_no_duplicate_test_declarations_in_suite():
    """C2-T01/T02/T03/T08: no duplicate test declarations anywhere in tests/."""
    files = sorted(TESTS_DIR.rglob("test_*.py"))
    assert files, "no test modules found"
    problems = []
    for path in files:
        for name, lines in cdt.find_duplicates(path):
            problems.append(f"{path.name}: {name} at {lines}")
    assert not problems, problems


def test_checker_detects_duplicate_functions(tmp_path):
    module = tmp_path / "test_dup.py"
    module.write_text("def test_a():\n    pass\n\n\ndef test_a():\n    pass\n", encoding="utf-8")
    dupes = cdt.find_duplicates(module)
    assert [name for name, _ in dupes] == ["test_a"]
    assert cdt.main([str(tmp_path)]) == 1


def test_checker_detects_duplicate_class_methods(tmp_path):
    module = tmp_path / "test_dup_class.py"
    module.write_text(
        "class TestX:\n"
        "    def test_a(self):\n        pass\n\n"
        "    def test_a(self):\n        pass\n",
        encoding="utf-8",
    )
    dupes = cdt.find_duplicates(module)
    assert [name for name, _ in dupes] == ["TestX.test_a"]


def test_checker_accepts_unique_functions(tmp_path):
    module = tmp_path / "test_ok.py"
    module.write_text("def test_a():\n    pass\n\n\ndef test_b():\n    pass\n", encoding="utf-8")
    assert cdt.find_duplicates(module) == []
    assert cdt.main([str(tmp_path)]) == 0


def _module_test_names(module_filename):
    tree = ast.parse((TESTS_DIR / module_filename).read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    ]


def _module_assign_names(module_filename):
    tree = ast.parse((TESTS_DIR / module_filename).read_text(encoding="utf-8"))
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
    return names


@pytest.mark.parametrize(
    "name",
    [
        "test_finish_button_success_exports_and_accepts",
        "test_finish_button_failure_keeps_wizard_open",
        "test_finish_button_retry_after_failure",
        "test_finish_button_blocks_on_incomplete_parties",
        "test_reentrant_finish_does_not_duplicate_export",
    ],
)
def test_finish_scenarios_discoverable(name):
    """C2-T04: every real Finish-button scenario remains discoverable exactly once."""
    names = _module_test_names("test_gui_flow.py")
    assert names.count(name) == 1, f"{name} appears {names.count(name)} times"


@pytest.mark.parametrize(
    "name",
    [
        "test_range_validation_checks_new_commits",
        "test_range_validation_includes_merge_commit",
        "test_range_unresolvable_returns_failure",
    ],
)
def test_commit_governance_scenarios_discoverable(name):
    """C2-T05: commit-message governance scenarios remain discoverable once."""
    names = _module_test_names("test_commit_message.py")
    assert names.count(name) == 1, f"{name} appears {names.count(name)} times"


def test_factual_integrity_scenario_discoverable():
    """C2-T06: the five-category factual-integrity test is declared once."""
    names = _module_test_names("test_e2e_documents.py")
    assert names.count("test_no_fabricated_case_facts") == 1


def test_shared_mappings_defined_once():
    """C2-T07: shared test-data mappings must be declared exactly once per module."""
    e2e_assigns = _module_assign_names("test_e2e_documents.py")
    for mapping in ("FORBIDDEN_FABRICATIONS", "CORRECTED_PHRASES"):
        assert e2e_assigns.count(mapping) == 1, f"{mapping} declared {e2e_assigns.count(mapping)} times"

    commit_assigns = _module_assign_names("test_commit_message.py")
    for mapping in ("INVALID_ELONGATIONS", "ORDINARY_WORDS"):
        assert commit_assigns.count(mapping) == 1, f"{mapping} declared {commit_assigns.count(mapping)} times"
