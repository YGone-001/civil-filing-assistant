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
prove that a source is authentic or that content is legally correct, and it
cannot prove that a human legal review actually took place.

Approval integrity
------------------
Populating approval text fields is **not** sufficient for approval. A mapping
may only be ``APPROVED`` when it binds one explicitly selected source
(``approved_source_id``) that is itself an eligible official template that has
reached ``APPROVED_FOR_ADAPTATION`` with a verified hash, a completed
legal/content review and distinct review evidence for each review stage.

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

# Legal / copyright review vocabulary. Only ``REVIEWED`` counts as completed.
LEGAL_REVIEW_STATUSES = frozenset({
    "NOT_REVIEWED",
    "NOT_APPLICABLE",
    "IN_PROGRESS",
    "PENDING",
    "REVIEWED",
    "REJECTED",
})
COMPLETED_LEGAL_REVIEW_STATUSES = frozenset({"REVIEWED"})

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

# --- Approval-integrity contract -------------------------------------------

# Only an actual template document may back an approval. A notice, an
# explanation, guidance, secondary material or the project's own output may
# never do so.
ELIGIBLE_APPROVAL_SOURCE_TYPES = frozenset({
    "OFFICIAL_TEMPLATE",
    "REPRODUCED_OFFICIAL_SOURCE",
})

# Level A (issuing authority) or a verified official reproduction (level B).
ELIGIBLE_APPROVAL_SOURCE_LEVELS = frozenset({"A", "B"})

# A mapping may not be approved before the source has been authorised for
# adaptation.
REQUIRED_SOURCE_APPROVAL_STATE = "APPROVED_FOR_ADAPTATION"

# Distinct evidence is required for each review stage; one generic string may
# not stand in for all of them.
SOURCE_APPROVAL_EVIDENCE_FIELDS = (
    "content_review_evidence",
    "mapping_review_evidence",
    "legal_content_review_evidence",
    "approval_evidence",
)

APPROVED_SOURCE_FIELD = "approved_source_id"

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

# Mapping fields only required once an approval is claimed.
APPROVAL_METADATA_FIELDS = (
    "approved_by_or_review_role",
    "approval_date",
    "approval_evidence",
)

_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_MAPPING_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# --- small helpers ----------------------------------------------------------


def _nonempty_str(value: Any) -> bool:
    """True only for a string that contains non-whitespace characters."""
    return isinstance(value, str) and bool(value.strip())


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
    except OSError as exc:
        issues.append(f"{path}: could not be read ({exc})")
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


# --- source records ---------------------------------------------------------


def source_approval_prerequisites(source: Dict[str, Any]) -> List[str]:
    """Return the reasons *source* may not back an approved mapping.

    An empty list means the source is eligible: it is an official template of
    level A/B that has reached ``APPROVED_FOR_ADAPTATION`` with a verified hash,
    a completed legal/content review and distinct evidence for every review
    stage.
    """
    reasons: List[str] = []

    source_type = source.get("source_type")
    if source_type not in ELIGIBLE_APPROVAL_SOURCE_TYPES:
        reasons.append(
            f"source_type {source_type!r} is not an official template source"
        )

    level = source.get("source_level")
    if level not in ELIGIBLE_APPROVAL_SOURCE_LEVELS:
        reasons.append(f"source_level {level!r} is not an official level A/B source")

    status = source.get("verification_status")
    if status != REQUIRED_SOURCE_APPROVAL_STATE:
        reasons.append(
            f"verification_status {status!r} has not reached {REQUIRED_SOURCE_APPROVAL_STATE!r}"
        )

    if not _nonempty_str(source.get("content_hash_if_verified")):
        reasons.append("no verified content hash")

    if source.get("legal_or_copyright_review_status") not in COMPLETED_LEGAL_REVIEW_STATUSES:
        reasons.append("legal/content review is not completed")

    for field in SOURCE_APPROVAL_EVIDENCE_FIELDS:
        if not _nonempty_str(source.get(field)):
            reasons.append(f"missing {field}")

    evidence = [
        source.get(field).strip()
        for field in SOURCE_APPROVAL_EVIDENCE_FIELDS
        if _nonempty_str(source.get(field))
    ]
    if len(evidence) == len(SOURCE_APPROVAL_EVIDENCE_FIELDS) and len(set(evidence)) != len(evidence):
        reasons.append("review evidence is not distinct across review stages")

    return reasons


def _check_sources(sources: Any, issues: List[str]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(sources, list):
        issues.append("source-registry: 'sources' must be a list")
        return {}

    by_id: Dict[str, Dict[str, Any]] = {}

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
            if sid in by_id:
                issues.append(f"{label}: duplicate source_id (first record wins)")
            else:
                by_id[sid] = source
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

        legal_review = source.get("legal_or_copyright_review_status")
        if legal_review is not None and legal_review not in LEGAL_REVIEW_STATUSES:
            issues.append(f"{label}: invalid legal_or_copyright_review_status {legal_review!r}")

        for field in ("publication_date", "document_date", "retrieval_or_review_date"):
            _check_date(f"{label}: {field}", source.get(field), issues)

        _check_hash(f"{label}: content_hash_if_verified", source.get("content_hash_if_verified"), issues)

        evidence = source.get("verification_evidence")
        if status != "DISCOVERED" and not _nonempty_str(evidence):
            issues.append(f"{label}: verification_evidence is required for status {status!r}")

        # Inconsistent verification claims.
        has_hash = _nonempty_str(source.get("content_hash_if_verified"))
        if status in FILE_VERIFIED_STATES and not has_hash:
            issues.append(f"{label}: status {status!r} requires a recorded content hash")
        if status == "DISCOVERED" and source.get("content_hash_if_verified") is not None:
            issues.append(f"{label}: a DISCOVERED source must not carry a content hash")

        # An approval-claimed source must satisfy every approval prerequisite.
        if status == REQUIRED_SOURCE_APPROVAL_STATE:
            for reason in source_approval_prerequisites(source):
                issues.append(f"{label}: {REQUIRED_SOURCE_APPROVAL_STATE} is not supported: {reason}")

    return by_id


# --- mapping records --------------------------------------------------------


def _check_mapping_approval(
    mapping: Dict[str, Any],
    label: str,
    sources_by_id: Dict[str, Dict[str, Any]],
    issues: List[str],
) -> None:
    """Enforce approval integrity for a single mapping record."""
    status = mapping.get("mapping_status")
    approval = mapping.get("approval_status")

    mapping_approved = status == "APPROVED"
    approval_claimed = approval == "APPROVED"

    # Bidirectional invariant: the two fields must agree.
    if mapping_approved != approval_claimed:
        issues.append(
            f"{label}: mapping_status {status!r} and approval_status {approval!r} are "
            f"inconsistent (both must be APPROVED together, or neither)"
        )

    reference = mapping.get(APPROVED_SOURCE_FIELD)

    if not approval_claimed:
        # Not claiming approval: the field must be absent/null, or at least point
        # at a real source so the registry cannot accumulate dangling references.
        if reference is not None and reference not in sources_by_id:
            issues.append(
                f"{label}: {APPROVED_SOURCE_FIELD} {reference!r} does not exist in the source registry"
            )
        return

    # --- approval claimed: require complete, consistent documentary evidence ---

    if not _nonempty_str(mapping.get("approved_by_or_review_role")):
        issues.append(f"{label}: approval claimed without documented 'approved_by_or_review_role'")

    if "approval_date" not in mapping or mapping.get("approval_date") is None:
        issues.append(f"{label}: approval claimed without documented 'approval_date'")
    else:
        _check_date(f"{label}: approval_date", mapping.get("approval_date"), issues)

    if not _nonempty_str(mapping.get("approval_evidence")):
        issues.append(f"{label}: approval claimed without documented 'approval_evidence'")

    if not _nonempty_str(reference):
        issues.append(f"{label}: approval claimed without documented {APPROVED_SOURCE_FIELD!r}")
        return

    if reference not in sources_by_id:
        issues.append(
            f"{label}: {APPROVED_SOURCE_FIELD} {reference!r} does not exist in the source registry"
        )
        return

    candidates = mapping.get("candidate_source_ids")
    if isinstance(candidates, list) and reference not in candidates:
        issues.append(
            f"{label}: {APPROVED_SOURCE_FIELD} {reference!r} is not among candidate_source_ids"
        )

    source = sources_by_id.get(reference)
    if isinstance(source, dict):
        for reason in source_approval_prerequisites(source):
            issues.append(
                f"{label}: approved source {reference!r} is not eligible for approval: {reason}"
            )


def _check_mappings(mappings: Any, sources_by_id: Dict[str, Dict[str, Any]], issues: List[str]) -> None:
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
                if ref not in sources_by_id:
                    issues.append(f"{label}: references unknown source_id {ref!r}")

        status = mapping.get("mapping_status")
        if status is not None and status not in MAPPING_STATUSES:
            issues.append(f"{label}: invalid mapping_status {status!r}")

        approval = mapping.get("approval_status")
        if approval is not None and approval not in APPROVAL_STATUSES:
            issues.append(f"{label}: invalid approval_status {approval!r}")

        if not isinstance(mapping.get("required_manual_review"), bool):
            issues.append(f"{label}: required_manual_review must be a boolean")

        if not isinstance(mapping.get("unverified_assumptions"), list):
            issues.append(f"{label}: unverified_assumptions must be a list")

        _check_mapping_approval(mapping, label, sources_by_id, issues)

    expected = {(c, d) for c in CASE_TYPES for d in DOCUMENT_TYPES}
    missing = sorted(expected - set(seen_combos))
    if missing:
        issues.append(f"case-template-mapping: missing case-document combinations: {missing}")


def validate_registries(source_path: Path, mapping_path: Path) -> List[str]:
    """Return a list of human-readable issues (empty list == valid)."""
    issues: List[str] = []

    source_data = _load_json(Path(source_path), issues)
    mapping_data = _load_json(Path(mapping_path), issues)

    sources_by_id: Dict[str, Dict[str, Any]] = {}
    if source_data is not None:
        sources_by_id = _check_sources(source_data.get("sources"), issues)

    if mapping_data is not None:
        _check_mappings(mapping_data.get("mappings"), sources_by_id, issues)

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
