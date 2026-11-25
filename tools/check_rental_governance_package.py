#!/usr/bin/env python
# File: tools/check_rental_governance_package.py
# Purpose: Offline validation for the post-baseline rental governance work package.
# Encoding: UTF-8
"""Validate ``rental-contract-work-package.json``.

The validator proves only that the work package is well-formed and still at a
pre-review stage. It cannot establish that a source exists, that legal review
occurred, or that a mapping is applicable.

Two documentary gates may be recorded as ``COMPLETE``:

* ``SOURCE_DISCOVERY``
* ``SOURCE_VERIFICATION``

The current stage may be ``TEXT_AND_STRUCTURE_COMPARISON``; every later gate
must remain incomplete and unauthorized. A candidate source may be recorded,
but no source selection, mapping, legal review, rights decision, engineering
authorization or release approval is accepted.

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
DEFAULT_SOURCE_REGISTRY = (
    REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"
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
# Only the documentary evidence stages may advance in this package.
PACKAGE_STAGES = TASK_STAGES[:3]
TASK_STATUSES = frozenset({
    "NOT_STARTED",
    "BLOCKED",
    "NOT_AUTHORIZED",
    "NOT_ASSESSED",
})
FORBIDDEN_TASK_STATUSES = frozenset({"COMPLETE", "PASS", "APPROVED", "AUTHORIZED"})
DISCOVERY_STATUSES = frozenset({"NOT_STARTED", "CANDIDATE_IDENTIFIED"})
OFFICIAL_COUNTERPARTS = frozenset({"UNKNOWN", "CANDIDATE_OFFICIAL_COMPLAINT"})
COUNTERPART_CLASSIFICATIONS = {
    "civil_complaint": frozenset({
        "CANDIDATE_OFFICIAL_COMPLAINT",
        "NO_COUNTERPART_IDENTIFIED_IN_INSPECTED_SOURCE",
    }),
    "evidence_list": frozenset({
        "OFFICIAL_SECTION_ONLY",
        "NO_COUNTERPART_IDENTIFIED_IN_INSPECTED_SOURCE",
    }),
    "service_address_confirmation": frozenset({
        "NO_COUNTERPART_IDENTIFIED_IN_INSPECTED_SOURCE",
    }),
}

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
    "source_verification",
    "counterpart_assessment",
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
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _date_is_iso(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


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


def _check_page_range(
    entry: Dict[str, Any], key: str, label: str, issues: List[str]
) -> None:
    value = entry.get(key)
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_is_positive_int(page) for page in value)
        or value[0] > value[1]
    ):
        issues.append(f"{label}.{key} must be an ascending two-element page range")


def _check_source_discovery(
    data: Dict[str, Any], issues: List[str]
) -> List[str]:
    """Validate the discovery record and return discovered candidate ids."""
    discovery = data.get("source_discovery")
    if not isinstance(discovery, dict):
        issues.append("source_discovery must be an object")
        return []

    status = discovery.get("status")
    if status not in DISCOVERY_STATUSES:
        issues.append("source_discovery.status must be 'NOT_STARTED' or 'CANDIDATE_IDENTIFIED'")

    candidate_ids = discovery.get("candidate_source_ids")
    if not isinstance(candidate_ids, list) or not all(
        isinstance(item, str) and item.strip() for item in candidate_ids
    ):
        issues.append("source_discovery.candidate_source_ids must be a list of source ids")
        candidate_ids = []
    elif len(set(candidate_ids)) != len(candidate_ids):
        issues.append("source_discovery.candidate_source_ids must not contain duplicates")

    if discovery.get("selected_source_id") is not None:
        issues.append("source_discovery.selected_source_id must remain null")

    counterpart = discovery.get("official_counterpart")
    if counterpart not in OFFICIAL_COUNTERPARTS:
        issues.append(
            "source_discovery.official_counterpart must be 'UNKNOWN' or "
            "'CANDIDATE_OFFICIAL_COMPLAINT'"
        )

    if status == "NOT_STARTED":
        if candidate_ids:
            issues.append(
                "source_discovery.candidate_source_ids must be empty while status is "
                "'NOT_STARTED'"
            )
        if counterpart != "UNKNOWN":
            issues.append(
                "source_discovery.official_counterpart must remain 'UNKNOWN' while status "
                "is 'NOT_STARTED'"
            )
    elif status == "CANDIDATE_IDENTIFIED":
        if not candidate_ids:
            issues.append(
                "source_discovery.candidate_source_ids must record a candidate while status "
                "is 'CANDIDATE_IDENTIFIED'"
            )
        if counterpart != "CANDIDATE_OFFICIAL_COMPLAINT":
            issues.append(
                "source_discovery.official_counterpart must be 'CANDIDATE_OFFICIAL_COMPLAINT' "
                "while status is 'CANDIDATE_IDENTIFIED'"
            )

    _require_string(discovery, "next_action", issues)
    return candidate_ids


def _check_source_verification(
    data: Dict[str, Any], candidate_ids: List[str], issues: List[str]
) -> None:
    verification = data.get("source_verification")
    if not isinstance(verification, dict):
        issues.append("source_verification must be an object")
        return

    source_id = verification.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        issues.append("source_verification.source_id must be a non-empty string")
    elif source_id not in candidate_ids:
        issues.append(
            "source_verification.source_id must appear in "
            "source_discovery.candidate_source_ids"
        )

    if verification.get("status") != "SOURCE_FILE_VERIFIED":
        issues.append("source_verification.status must be 'SOURCE_FILE_VERIFIED'")

    if not _date_is_iso(verification.get("retrieved_date")):
        issues.append("source_verification.retrieved_date must be an ISO calendar date")

    if not _is_positive_int(verification.get("file_size_bytes")):
        issues.append("source_verification.file_size_bytes must be a positive integer")

    if not _is_positive_int(verification.get("page_count")):
        issues.append("source_verification.page_count must be a positive integer")

    sha256 = verification.get("sha256")
    if not isinstance(sha256, str) or not _HEX64_RE.match(sha256):
        issues.append("source_verification.sha256 must be 64 lowercase hex characters")

    if verification.get("local_artifact_status") != "NOT_STORED_IN_REPOSITORY":
        issues.append(
            "source_verification.local_artifact_status must remain "
            "'NOT_STORED_IN_REPOSITORY'"
        )

    _require_string(verification, "evidence", issues)


def _check_counterpart_assessment(
    data: Dict[str, Any], candidate_ids: List[str], issues: List[str]
) -> None:
    assessment = data.get("counterpart_assessment")
    if not isinstance(assessment, dict):
        issues.append("counterpart_assessment must be an object")
        return

    for document_type in DOCUMENT_TYPES:
        entry = assessment.get(document_type)
        label = f"counterpart_assessment.{document_type}"
        if not isinstance(entry, dict):
            issues.append(f"{label} must be an object")
            continue

        classification = entry.get("classification")
        if classification not in COUNTERPART_CLASSIFICATIONS[document_type]:
            issues.append(
                f"{label}.classification must be one of: "
                + ", ".join(sorted(COUNTERPART_CLASSIFICATIONS[document_type]))
            )

        source_id = entry.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            issues.append(f"{label}.source_id must be a non-empty string")
        elif source_id not in candidate_ids:
            issues.append(
                f"{label}.source_id must appear in "
                "source_discovery.candidate_source_ids"
            )

        _require_string(entry, "notes", issues)

        if document_type == "civil_complaint" and classification == (
            "CANDIDATE_OFFICIAL_COMPLAINT"
        ):
            for key in (
                "blank_form_pdf_pages",
                "blank_form_printed_pages",
                "instance_pdf_pages",
                "instance_printed_pages",
            ):
                _check_page_range(entry, key, label, issues)

        if document_type == "evidence_list" and classification == "OFFICIAL_SECTION_ONLY":
            pages = entry.get("pdf_pages")
            if (
                not isinstance(pages, list)
                or not pages
                or not all(_is_positive_int(page) for page in pages)
            ):
                issues.append(f"{label}.pdf_pages must be a non-empty list of page numbers")


def _check_task_progression(
    data: Dict[str, Any], tasks: List[Any], issues: List[str]
) -> None:
    current_stage = data.get("current_stage")
    if current_stage not in PACKAGE_STAGES:
        return
    current_index = PACKAGE_STAGES.index(current_stage)

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        status = task.get("status")
        if index < current_index:
            if status != "COMPLETE":
                issues.append(
                    f"tasks[{index}].status must be 'COMPLETE' for a stage that is already past"
                )
        elif index == current_index:
            if status != "NOT_STARTED":
                issues.append(
                    f"tasks[{index}].status must be 'NOT_STARTED' for the current stage"
                )
        elif status in FORBIDDEN_TASK_STATUSES:
            issues.append(
                f"tasks[{index}] must not claim completion or authorization"
            )
        elif status not in TASK_STATUSES:
            issues.append(f"tasks[{index}].status is not an allowed pre-review state")


def _check_registry_consistency(
    data: Dict[str, Any],
    candidate_ids: List[str],
    source_registry: Optional[Dict[str, Any]],
    issues: List[str],
) -> None:
    if source_registry is None:
        return
    if not isinstance(source_registry, dict):
        issues.append("source registry must be a JSON object")
        return

    records: Dict[str, Dict[str, Any]] = {}
    sources = source_registry.get("sources")
    if not isinstance(sources, list):
        issues.append("source registry must contain a 'sources' list")
        return
    for source in sources:
        if isinstance(source, dict) and isinstance(source.get("source_id"), str):
            records[source["source_id"]] = source

    for source_id in candidate_ids:
        if source_id not in records:
            issues.append(
                f"source_discovery.candidate_source_ids references unknown source_id "
                f"{source_id!r}"
            )

    verification = data.get("source_verification")
    if not isinstance(verification, dict):
        return
    source_id = verification.get("source_id")
    record = records.get(source_id) if isinstance(source_id, str) else None
    if record is None:
        if isinstance(source_id, str) and source_id.strip():
            issues.append(
                f"source_verification.source_id {source_id!r} is not present in the "
                "source registry"
            )
        return

    sha256 = verification.get("sha256")
    if isinstance(sha256, str) and _HEX64_RE.match(sha256):
        recorded = record.get("content_hash_if_verified")
        if recorded != f"sha256:{sha256}":
            issues.append(
                f"source_verification.sha256 does not match the registry hash for "
                f"{source_id!r}"
            )


def validate_package(
    data: Any, source_registry: Optional[Dict[str, Any]] = None
) -> List[str]:
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
    if data.get("current_stage") not in PACKAGE_STAGES:
        issues.append(
            "current_stage must be one of: " + ", ".join(PACKAGE_STAGES)
        )
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

    candidate_ids = _check_source_discovery(data, issues)
    _check_source_verification(data, candidate_ids, issues)
    _check_counterpart_assessment(data, candidate_ids, issues)
    _check_registry_consistency(data, candidate_ids, source_registry, issues)

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
        _check_task_progression(data, tasks, issues)

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
    parser.add_argument(
        "--source-registry", type=Path, default=DEFAULT_SOURCE_REGISTRY
    )
    args = parser.parse_args(argv)

    issues: List[str] = []
    data = _load(args.package, issues)
    registry = _load(args.source_registry, issues)
    if data is not None:
        issues.extend(validate_package(data, registry))

    if issues:
        print("FAIL rental governance work package is invalid:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(
        "OK   rental governance work package is valid "
        "(pre-review, candidate source only, NO-GO)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
