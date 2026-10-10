#!/usr/bin/env python
# File: tools/check_template_governance.py
# Purpose: Deterministic, offline validation of the legal-template governance metadata.
# Encoding: UTF-8
"""Validate the legal-template governance registries.

Checks the machine-readable governance metadata defined by
``docs/legal-template-governance/governance.md``:

* ``docs/legal-template-governance/source-registry.json``
* ``docs/legal-template-governance/case-template-mapping.json``

The validator is standard-library only, runs offline, reads repository metadata
only, has no side effects, and returns a nonzero exit code when the records are
invalid.

It proves the records are *well-formed and internally consistent*. It cannot
prove that a source is authentic or that content is legally correct.

Usage::

    python tools/check_template_governance.py
    python tools/check_template_governance.py --source-registry a.json --mapping-registry b.json
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
DEFAULT_SOURCE_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"
DEFAULT_MAPPING_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "case-template-mapping.json"

# --- Policy enums (authoritative) ------------------------------------------

SOURCE_TYPES = frozenset({
    "OFFICIAL_NOTICE",
    "OFFICIAL_TEMPLATE",
    "OFFICIAL_GUIDANCE",
    "OFFICIAL_EXPLANATION",
    "REPRODUCED_OFFICIAL_SOURCE",
    "SECONDARY_REFERENCE",
    "CURRENT_APPLICATION_OUTPUT",
})

VERIFICATION_STATES = frozenset({
    "DISCOVERED",
    "ANNOUNCEMENT_VERIFIED",
    "SOURCE_FILE_VERIFIED",
    "CONTENT_REVIEWED",
    "MAPPING_REVIEWED",
    "APPROVED_FOR_ADAPTATION",
    "REJECTED",
    "UNAVAILABLE",
})

# States that require a retrieved file (and therefore a recorded content hash).
FILE_VERIFIED_STATES = frozenset({
    "SOURCE_FILE_VERIFIED",
    "CONTENT_REVIEWED",
    "MAPPING_REVIEWED",
    "APPROVED_FOR_ADAPTATION",
})

SOURCE_LEVELS = frozenset({"A", "B", "C"})

CASE_TYPES = frozenset({"loan", "contract", "property", "labor", "divorce"})
DOCUMENT_TYPES = frozenset({
    "civil_complaint",
    "evidence_list",
    "service_address_confirmation",
})

MAPPING_STATUSES = frozenset({
    "UNVERIFIED",
    "CANDIDATE_SOURCE_IDENTIFIED",
    "MAPPING_REVIEWED",
    "APPROVED",
    "REJECTED",
    "NO_OFFICIAL_SOURCE_IDENTIFIED",
})

APPROVAL_STATUSES = frozenset({"NOT_REQUESTED", "PENDING", "APPROVED", "REJECTED"})

SOURCE_REQUIRED_FIELDS = (
    "source_id",
    "title",
    "issuing_authority",
    "source_type",
    "official_url",
    "publication_date",
    "document_date",
    "retrieval_or_review_date",
    "source_level",
    "verification_status",
    "verification_evidence",
    "local_artifact_status",
    "content_hash_if_verified",
    "legal_or_copyright_review_status",
    "notes",
)

MAPPING_REQUIRED_FIELDS = (
    "mapping_id",
    "case_type",
    "document_type",
    "current_generator",
    "current_output_status",
    "candidate_source_ids",
    "mapping_status",
    "mapping_confidence_or_evidence",
    "jurisdictional_scope",
    "applicability_notes",
    "unverified_assumptions",
    "required_manual_review",
    "approval_status",
    "notes",
)

# Fields only required once an approval is claimed.
APPROVAL_METADATA_FIELDS = ("approved_by_or_review_role", "approval_date", "approval_evidence")

_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_MAPPING_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_json(path: Path, issues: List[str]) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        issues.append(f"{path}: file not found")
        return None
    except json.JSONDecodeError as exc:
        issues.append(f"{path}: invalid JSON ({exc})")
        return None
    if not isinstance(data, dict):
        issues.append(f"{path}: top-level value must be a JSON object")
        return None
    return data


def _check_date(label: str, value: Any, issues: List[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not _DATE_RE.match(value):
        issues.append(f"{label}: date must be null or 'YYYY-MM-DD', got {value!r}")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        issues.append(f"{label}: date is not a real calendar date: {value!r}")


def _check_hash(label: str, value: Any, issues: List[str]) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not _HASH_RE.match(value):
        issues.append(f"{label}: content hash must be null or 'sha256:<64 lowercase hex>', got {value!r}")


def _check_sources(sources: Any, issues: List[str]) -> List[Dict[str, Any]]:
    if not isinstance(sources, list):
        issues.append("source-registry: 'sources' must be a list")
        return []
    seen: Dict[str, int] = {}
    for index, source in enumerate(sources):
        label = f"source[{index}]"
        if not isinstance(source, dict):
            issues.append(f"{label}: record must be a JSON object")
            continue

        for field in SOURCE_REQUIRED_FIELDS:
            if field not in source:
                issues.append(f"{label}: missing required field {field!r}")

        sid = source.get("source_id")
        if isinstance(sid, str):
            label = f"source {sid!r}"
            if not _SOURCE_ID_RE.match(sid):
                issues.append(f"{label}: source_id must match {_SOURCE_ID_RE.pattern}")
            if sid in seen:
                issues.append(f"{label}: duplicate source_id (also at index {seen[sid]})")
            else:
                seen[sid] = index
        elif sid is not None:
            issues.append(f"{label}: source_id must be a string")

        source_type = source.get("source_type")
        if source_type is not None and source_type not in SOURCE_TYPES:
            issues.append(f"{label}: unknown source_type {source_type!r}")

        status = source.get("verification_status")
        if status is not None and status not in VERIFICATION_STATES:
            issues.append(f"{label}: invalid verification_status {status!r}")

        level = source.get("source_level")
        if level is not None and level not in SOURCE_LEVELS:
            issues.append(f"{label}: source_level must be null or one of {sorted(SOURCE_LEVELS)}")

        for field in ("publication_date", "document_date", "retrieval_or_review_date"):
            _check_date(f"{label}: {field}", source.get(field), issues)

        _check_hash(f"{label}: content_hash_if_verified", source.get("content_hash_if_verified"), issues)

        evidence = source.get("verification_evidence")
        if status != "DISCOVERED" and (not isinstance(evidence, str) or not evidence.strip()):
            issues.append(
                f"{label}: verification_evidence is required for status {status!r}"
            )

        # Inconsistent verification claims.
        has_hash = source.get("content_hash_if_verified") is not None
        if status in FILE_VERIFIED_STATES and not has_hash:
            issues.append(
                f"{label}: status {status!r} requires a recorded content hash"
            )
        if status == "DISCOVERED" and has_hash:
            issues.append(
                f"{label}: a DISCOVERED source must not carry a content hash"
            )
        if status == "APPROVED_FOR_ADAPTATION":
            if source.get("legal_or_copyright_review_status") in (None, "NOT_REVIEWED"):
                issues.append(
                    f"{label}: APPROVED_FOR_ADAPTATION requires a completed legal/copyright review"
                )
            if not source.get("approval_evidence"):
                issues.append(
                    f"{label}: APPROVED_FOR_ADAPTATION requires documented approval evidence"
                )

    return [s for s in sources if isinstance(s, dict)]


def _check_mappings(mappings: Any, source_ids: set, issues: List[str]) -> None:
    if not isinstance(mappings, list):
        issues.append("case-template-mapping: 'mappings' must be a list")
        return

    seen_ids: Dict[str, int] = {}
    seen_combos: Dict[tuple, str] = {}

    for index, mapping in enumerate(mappings):
        label = f"mapping[{index}]"
        if not isinstance(mapping, dict):
            issues.append(f"{label}: record must be a JSON object")
            continue

        for field in MAPPING_REQUIRED_FIELDS:
            if field not in mapping:
                issues.append(f"{label}: missing required field {field!r}")

        mid = mapping.get("mapping_id")
        if isinstance(mid, str):
            label = f"mapping {mid!r}"
            if not _MAPPING_ID_RE.match(mid):
                issues.append(f"{label}: mapping_id must match {_MAPPING_ID_RE.pattern}")
            if mid in seen_ids:
                issues.append(f"{label}: duplicate mapping_id (also at index {seen_ids[mid]})")
            else:
                seen_ids[mid] = index
        elif mid is not None:
            issues.append(f"{label}: mapping_id must be a string")

        case_type = mapping.get("case_type")
        if case_type is not None and case_type not in CASE_TYPES:
            issues.append(f"{label}: unknown case_type {case_type!r}")

        document_type = mapping.get("document_type")
        if document_type is not None and document_type not in DOCUMENT_TYPES:
            issues.append(f"{label}: unknown document_type {document_type!r}")

        if case_type in CASE_TYPES and document_type in DOCUMENT_TYPES:
            combo = (case_type, document_type)
            if combo in seen_combos:
                issues.append(
                    f"{label}: duplicate case-document combination {combo} "
                    f"(also at {seen_combos[combo]})"
                )
            else:
                seen_combos[combo] = label

        refs = mapping.get("candidate_source_ids")
        if not isinstance(refs, list):
            issues.append(f"{label}: candidate_source_ids must be a list")
        else:
            for ref in refs:
                if ref not in source_ids:
                    issues.append(f"{label}: references unknown source_id {ref!r}")

        status = mapping.get("mapping_status")
        if status is not None and status not in MAPPING_STATUSES:
            issues.append(f"{label}: invalid mapping_status {status!r}")

        approval = mapping.get("approval_status")
        if approval is not None and approval not in APPROVAL_STATUSES:
            issues.append(f"{label}: invalid approval_status {approval!r}")

        if status == "APPROVED" and approval != "APPROVED":
            issues.append(f"{label}: mapping_status APPROVED requires approval_status APPROVED")

        if approval == "APPROVED":
            for field in APPROVAL_METADATA_FIELDS:
                if not mapping.get(field):
                    issues.append(
                        f"{label}: approval claimed without documented {field!r}"
                    )
            _check_date(f"{label}: approval_date", mapping.get("approval_date"), issues)

        if not isinstance(mapping.get("required_manual_review"), bool):
            issues.append(f"{label}: required_manual_review must be a boolean")

        if not isinstance(mapping.get("unverified_assumptions"), list):
            issues.append(f"{label}: unverified_assumptions must be a list")

    expected = {(c, d) for c in CASE_TYPES for d in DOCUMENT_TYPES}
    missing = sorted(expected - set(seen_combos))
    if missing:
        issues.append(f"case-template-mapping: missing case-document combinations: {missing}")


def validate_registries(source_path: Path, mapping_path: Path) -> List[str]:
    """Return a list of human-readable issues (empty list == valid)."""
    issues: List[str] = []

    source_data = _load_json(Path(source_path), issues)
    mapping_data = _load_json(Path(mapping_path), issues)

    source_ids: set = set()
    if source_data is not None:
        sources = _check_sources(source_data.get("sources"), issues)
        source_ids = {s.get("source_id") for s in sources if isinstance(s.get("source_id"), str)}

    if mapping_data is not None:
        _check_mappings(mapping_data.get("mappings"), source_ids, issues)

    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate legal-template governance metadata."
    )
    parser.add_argument("--source-registry", default=str(DEFAULT_SOURCE_REGISTRY))
    parser.add_argument("--mapping-registry", default=str(DEFAULT_MAPPING_REGISTRY))
    args = parser.parse_args(argv)

    issues = validate_registries(Path(args.source_registry), Path(args.mapping_registry))

    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        print(f"FAIL template governance metadata: {len(issues)} issue(s)")
        return 1

    print("OK   template governance metadata is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
