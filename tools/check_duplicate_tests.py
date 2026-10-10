#!/usr/bin/env python
# File: tools/check_duplicate_tests.py
# Purpose: Detect duplicate top-level test declarations with the AST.
# Encoding: UTF-8
"""Duplicate test-declaration checker.

Python silently lets a later definition of the same function name shadow an
earlier one, which can hide a test entirely. This checker parses each test
module and reports:

* repeated top-level ``test_*`` function names within the same module;
* repeated ``test_*`` method names within the same class.

Names only need to be unique *within* a module (and within a class), so two
different modules may each define ``test_something``.

Usage::

    python tools/check_duplicate_tests.py            # scans tests/ by default
    python tools/check_duplicate_tests.py path [path ...]

Exit code is non-zero when a duplicate is found.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_TARGETS = ["tests"]


def _test_functions(nodes) -> Dict[str, List[int]]:
    found: Dict[str, List[int]] = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            found.setdefault(node.name, []).append(node.lineno)
    return found


def find_duplicates(path: Path) -> List[Tuple[str, List[int]]]:
    """Return ``[(qualified_name, [linenos])]`` for duplicate test definitions."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    duplicates: List[Tuple[str, List[int]]] = []

    for name, lines in _test_functions(tree.body).items():
        if len(lines) > 1:
            duplicates.append((name, lines))

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for name, lines in _test_functions(node.body).items():
                if len(lines) > 1:
                    duplicates.append((f"{node.name}.{name}", lines))

    return sorted(duplicates)


def _iter_python_files(targets: List[str]):
    for target in targets:
        path = Path(target)
        if path.is_dir():
            yield from sorted(path.rglob("test_*.py"))
        elif path.suffix == ".py":
            yield path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect duplicate test declarations.")
    parser.add_argument("paths", nargs="*", default=None, help="files or directories to scan")
    args = parser.parse_args(argv)

    targets = args.paths or DEFAULT_TARGETS
    violations = 0
    scanned = 0

    for path in _iter_python_files(targets):
        scanned += 1
        for name, lines in find_duplicates(path):
            violations += 1
            joined = ", ".join(f"line {n}" for n in lines)
            print(f"DUPLICATE {path}: {name} defined {len(lines)} times ({joined})")

    if violations:
        print(f"FAIL duplicate test declarations: {violations}")
        return 1

    print(f"OK   no duplicate test declarations ({scanned} file(s) scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
