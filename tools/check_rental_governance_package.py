#!/usr/bin/env python
# File: tools/check_rental_governance_package.py
# Purpose: Offline validation for the post-baseline rental governance work package.
# Encoding: UTF-8
"""Validate ``rental-contract-work-package.json``.

The validator proves only that the work package is well-formed and still in the
correct pre-review state. It cannot establish that a source exists, that legal
review occurred, or that a mapping is applicable.

Usage::

    python tools/check_rental_governance_package.py
    python tools/check_rental_governance_package.py --package path.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = (
    REPO_ROOT
    / "docs"
    / "legal-template-governance"
    / "official-adaptation-planning"
    / "rental-contract-work-package.json"
)

CASE_TYPE = "rental"
DOCUMENT_TYPES = (
    "civil_complaint",
    "evidence_list",
    "service_address_confirmation",
)
TASK_STAGES = (
    "SOURCE_DISCOVERY",
    "SOURCE_VERIFICATION",
    "TEXT_AND_STRUCTURE_COMPARISON",
    "CASE_MAPPING_REVIEW",
    "LEGAL_CONTENT_REVIEW",
    "RIGHTS_AND_REDISTRIBUTION_REVIEW",
    "ENGINEERING_IMPLEMENTATION",
    "DOCX_REGRESSION_VALIDATION",
    "RELEASE_APPROVAL",
)
TASK_STATUSES = frozenset({
    "NOT_STARTED",
    "BLOCKED",
    "NOT_AUTHORIZED",
    "NOT_ASSESSED",
})
FORBIDDEN_TASK_STATUSES = frozenset({"COMPLETE", "PASS", "APPROVED", "AUTHORIZED"})

_REQUIRED_TOP_LEVEL = (
    "work_package_id",
    "title",
    "status",
    "current_stage",
    "created_date",
    "baseline_commit",
    "case_type",
    "document_types",
    "runtime_status",
    "runtime_characterization",
    "central_mapping_registry_updated",
    "frozen_planning_records_modified",
    "source_discovery",
    "legal_review_status",
    "rights_review_status",
    "implementation_authorization",
    "release_gate",
    "reviewer_roles_required",
    "assigned_reviewers",
    "scope_note",
    "current_application",
    "known_legal_questions",
    "tasks",
    "gate_sequence",
    "exit_criteria",
    "non_claims",
)

_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")


def _date_is_iso(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _require_string(data: Dict[str, Any], key: str, issues: List[str]) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} must be a non-empty string")


def _require_string_list(data: Dict[str, Any], key: str, issues: List[str]) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        issues.append(f"{key} must be a list of non-empty strings")


def validate_package(data: Any) -> List[str]:
    """Return validation issues; an empty list means the package is valid."""
    issues: List[str] = []
    if not isinstance(data, dict):
        return ["work package must be a JSON object"]

    for key in _REQUIRED_TOP_LEVEL:
        if key not in data:
            issues.append(f"missing required field {key!r}")

    for key in (
        "work_package_id", "title", "status", "current_stage", "baseline_commit",
        "case_type", "runtime_status", "runtime_characterization",
        "legal_review_status", "rights_review_status",
        "implementation_authorization", "release_gate", "scope_note",
    ):
        _require_string(data, key, issues)

    if data.get("work_package_id") != "wp-rental-source-discovery":
        issues.append("work_package_id must be 'wp-rental-source-discovery'")
    if data.get("case_type") != CASE_TYPE:
        issues.append("case_type must be 'rental'")
    if data.get("status") != "OPEN":
        issues.append("status must remain 'OPEN'")
    if data.get("current_stage") != "SOURCE_DISCOVERY":
        issues.append("current_stage must remain 'SOURCE_DISCOVERY'")
    if data.get("runtime_status") != "IMPLEMENTED_AND_TESTED":
        issues.append("runtime_status must record the tested baseline")
    if data.get("runtime_characterization") != "PROJECT_AUTHORED_STRUCTURED_TEMPLATE":
        issues.append("runtime_characterization must remain project-authored")
    if data.get("central_mapping_registry_updated") is not False:
        issues.append("central_mapping_registry_updated must be false")
    if data.get("frozen_planning_records_modified") is not False:
        issues.append("frozen_planning_records_modified must be false")
    if data.get("legal_review_status") != "NOT_REQUESTED":
        issues.append("legal_review_status must remain 'NOT_REQUESTED'")
    if data.get("rights_review_status") != "NOT_REVIEWED":
        issues.append("rights_review_status must remain 'NOT_REVIEWED'")
    if data.get("implementation_authorization") != "NOT_AUTHORIZED":
        issues.append("implementation_authorization must remain 'NOT_AUTHORIZED'")
    if data.get("release_gate") != "NO-GO":
        issues.append("release_gate must remain 'NO-GO'")

    created = data.get("created_date")
    if not _date_is_iso(created):
        issues.append("created_date must be an ISO calendar date")
    baseline = data.get("baseline_commit")
    if isinstance(baseline, str) and not _HEX40_RE.match(baseline):
        issues.append("baseline_commit must be a 40-character lowercase hex SHA")

    docs = data.get("document_types")
    if not isinstance(docs, list) or tuple(docs) != DOCUMENT_TYPES:
        issues.append(
            "document_types must be exactly: " + ", ".join(DOCUMENT_TYPES)
        )

    discovery = data.get("source_discovery")
    if not isinstance(discovery, dict):
        issues.append("source_discovery must be an object")
    else:
        if discovery.get("status") != "NOT_STARTED":
            issues.append("source_discovery.status must remain 'NOT_STARTED'")
        if discovery.get("candidate_source_ids") != []:
            issues.append("source_discovery.candidate_source_ids must remain empty")
        if discovery.get("selected_source_id") is not None:
            issues.append("source_discovery.selected_source_id must remain null")
        if discovery.get("official_counterpart") != "UNKNOWN":
            issues.append("source_discovery.official_counterpart must remain 'UNKNOWN'")
        _require_string(discovery, "next_action", issues)

    _require_string_list(data, "reviewer_roles_required", issues)
    if data.get("assigned_reviewers") != []:
        issues.append("assigned_reviewers must remain empty; do not invent reviewers")
    _require_string_list(data, "known_legal_questions", issues)
    _require_string_list(data, "gate_sequence", issues)
    _require_string_list(data, "exit_criteria", issues)
    _require_string_list(data, "non_claims", issues)

    expected_gates = [
        "SOURCE_AUTHENTICITY",
        "SOURCE_CONTENT_REVIEW",
        "MAPPING_APPLICABILITY_REVIEW",
        "LEGAL_CONTENT_REVIEW",
        "RIGHTS_AND_REDISTRIBUTION_REVIEW",
        "SCOPED_ENGINEERING_AUTHORIZATION",
        "IMPLEMENTATION",
        "DOCX_REGRESSION_ACCEPTANCE",
        "RELEASE_APPROVAL",
    ]
    if data.get("gate_sequence") != expected_gates:
        issues.append("gate_sequence must match the governance approval-gate order")

    app = data.get("current_application")
    if not isinstance(app, dict):
        issues.append("current_application must be an object")
    else:
        if app.get("case_type_name") != "租赁合同纠纷":
            issues.append("current_application.case_type_name must be '租赁合同纠纷'")
        for key in ("user_fields", "claims", "documents", "runtime_files", "runtime_tests"):
            _require_string_list(app, key, issues)

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        issues.append("tasks must be a list")
    else:
        if len(tasks) != len(TASK_STAGES):
            issues.append(f"tasks must contain exactly {len(TASK_STAGES)} stages")
        for index, expected_stage in enumerate(TASK_STAGES):
            if index >= len(tasks):
                break
            task = tasks[index]
            if not isinstance(task, dict):
                issues.append(f"tasks[{index}] must be an object")
                continue
            if task.get("stage") != expected_stage:
                issues.append(f"tasks[{index}].stage must be {expected_stage!r}")
            _require_string(task, "task_id", issues)
            _require_string(task, "owner_role", issues)
            _require_string(task, "objective", issues)
            _require_string_list(task, "exit_criteria", issues)
            status = task.get("status")
            if status in FORBIDDEN_TASK_STATUSES:
                issues.append(f"tasks[{index}] must not claim completion or authorization")
            elif status not in TASK_STATUSES:
                issues.append(f"tasks[{index}].status is not an allowed pre-review state")
        if tasks and isinstance(tasks[0], dict):
            if tasks[0].get("status") != "NOT_STARTED":
                issues.append("the source-discovery task must remain 'NOT_STARTED'")

    return issues


def _load(path: Path, issues: List[str]) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        issues.append(f"cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        issues.append(f"invalid JSON in {path}: {exc}")
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the rental-contract governance work package."
    )
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    args = parser.parse_args(argv)

    issues: List[str] = []
    data = _load(args.package, issues)
    if data is not None:
        issues.extend(validate_package(data))

    if issues:
        print("FAIL rental governance work package is invalid:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("OK   rental governance work package is valid (pre-review, NO-GO)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
