#!/usr/bin/env python
# File: tools/check_rental_governance_package.py
# Purpose: Offline validation for the post-baseline rental governance work package.
# Encoding: UTF-8
"""Validate ``rental-contract-work-package.json``.

The validator proves only that the work package is well-formed and still at a
pre-review stage. It cannot establish that a source exists, that legal review
occurred, or that a mapping is applicable.

Four documentary gates may be recorded as ``COMPLETE``:

* ``SOURCE_DISCOVERY``
* ``SOURCE_VERIFICATION``
* ``TEXT_AND_STRUCTURE_COMPARISON``
* ``CASE_MAPPING_REVIEW``

The current stage may be ``LEGAL_CONTENT_REVIEW``; every later gate must remain
incomplete and unauthorized. A candidate source and three unapproved rental
mapping entries may be recorded, but no source selection, legal review, rights
decision, engineering authorization or release approval is accepted.

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
DEFAULT_MAPPING_REGISTRY = (
    REPO_ROOT / "docs" / "legal-template-governance" / "case-template-mapping.json"
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
# The documentary stages and the mapping review may advance here.
PACKAGE_STAGES = TASK_STAGES[:5]
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
RENTAL_MAPPING_IDS = {
    "civil_complaint": "map-rental-complaint",
    "evidence_list": "map-rental-evidence",
    "service_address_confirmation": "map-rental-address",
}
EXPECTED_RENTAL_MAPPING_STATUSES = {
    "civil_complaint": "CANDIDATE_SOURCE_IDENTIFIED",
    "evidence_list": "UNVERIFIED",
    "service_address_confirmation": "NO_OFFICIAL_SOURCE_IDENTIFIED",
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
    "text_and_structure_comparison",
    "case_mapping_review",
    "legal_content_review",
    "scoped_engineering_authorization",
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
_GAP_ID_RE = re.compile(r"^RCS-\d{2}$")
_LRQ_ID_RE = re.compile(r"^LRQ-\d{2}$")
_PF_ID_RE = re.compile(r"^PF-\d{2}$")


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


def _check_text_and_structure_comparison(
    data: Dict[str, Any], candidate_ids: List[str], issues: List[str]
) -> None:
    comparison = data.get("text_and_structure_comparison")
    if not isinstance(comparison, dict):
        issues.append("text_and_structure_comparison must be an object")
        return

    if comparison.get("status") != "COMPLETE":
        issues.append("text_and_structure_comparison.status must be 'COMPLETE'")
    if not _date_is_iso(comparison.get("completed_date")):
        issues.append(
            "text_and_structure_comparison.completed_date must be an ISO calendar date"
        )
    if comparison.get("document") != "rental-text-and-structure-comparison.md":
        issues.append(
            "text_and_structure_comparison.document must be "
            "'rental-text-and-structure-comparison.md'"
        )

    source_id = comparison.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        issues.append(
            "text_and_structure_comparison.source_id must be a non-empty string"
        )
    elif source_id not in candidate_ids:
        issues.append(
            "text_and_structure_comparison.source_id must appear in "
            "source_discovery.candidate_source_ids"
        )

    _require_string(comparison, "current_output_basis", issues)
    _require_string(comparison, "method", issues)
    _require_string(comparison, "summary", issues)

    for key in ("blank_form_pdf_pages", "instance_pdf_pages"):
        _check_page_range(comparison, key, "text_and_structure_comparison", issues)

    assessment = data.get("counterpart_assessment")
    if isinstance(assessment, dict):
        complaint = assessment.get("civil_complaint")
        if isinstance(complaint, dict):
            for key in ("blank_form_pdf_pages", "instance_pdf_pages"):
                if comparison.get(key) != complaint.get(key):
                    issues.append(
                        f"text_and_structure_comparison.{key} must match "
                        f"counterpart_assessment.civil_complaint.{key}"
                    )

    gap_ids = comparison.get("gap_register_ids")
    if not isinstance(gap_ids, list) or not gap_ids:
        issues.append(
            "text_and_structure_comparison.gap_register_ids must be a non-empty list"
        )
        gap_ids = []
    else:
        normalized = []
        for gap_id in gap_ids:
            if not isinstance(gap_id, str) or not _GAP_ID_RE.match(gap_id):
                issues.append(
                    "text_and_structure_comparison.gap_register_ids must use RCS-NN "
                    "identifiers"
                )
                continue
            normalized.append(gap_id)
        if len(set(normalized)) != len(normalized):
            issues.append(
                "text_and_structure_comparison.gap_register_ids must not contain duplicates"
            )

    gap_count = comparison.get("gap_count")
    if not _is_positive_int(gap_count):
        issues.append(
            "text_and_structure_comparison.gap_count must be a positive integer"
        )
    elif gap_count != len(gap_ids):
        issues.append(
            "text_and_structure_comparison.gap_count must equal the number of gap ids"
        )

    questions = comparison.get("highest_priority_open_questions")
    if not isinstance(questions, list) or not questions or not all(
        isinstance(item, str) and item.strip() for item in questions
    ):
        issues.append(
            "text_and_structure_comparison.highest_priority_open_questions must be a "
            "non-empty list of strings"
        )


def _check_case_mapping_review(data: Dict[str, Any], issues: List[str]) -> None:
    review = data.get("case_mapping_review")
    if not isinstance(review, dict):
        issues.append("case_mapping_review must be an object")
        return

    if review.get("status") != "COMPLETE":
        issues.append("case_mapping_review.status must be 'COMPLETE'")
    if not _date_is_iso(review.get("completed_date")):
        issues.append("case_mapping_review.completed_date must be an ISO calendar date")
    if review.get("document") != "case-template-mapping.json":
        issues.append(
            "case_mapping_review.document must be 'case-template-mapping.json'"
        )

    expected_ids = [RENTAL_MAPPING_IDS[doc_type] for doc_type in DOCUMENT_TYPES]
    if review.get("mapping_ids") != expected_ids:
        issues.append(
            "case_mapping_review.mapping_ids must be exactly: "
            + ", ".join(expected_ids)
        )

    decisions = review.get("decisions")
    if not isinstance(decisions, dict):
        issues.append("case_mapping_review.decisions must be an object")
    else:
        for document_type in DOCUMENT_TYPES:
            label = f"case_mapping_review.decisions.{document_type}"
            entry = decisions.get(document_type)
            if not isinstance(entry, dict):
                issues.append(f"{label} must be an object")
                continue
            expected_status = EXPECTED_RENTAL_MAPPING_STATUSES[document_type]
            if entry.get("mapping_status") != expected_status:
                issues.append(
                    f"{label}.mapping_status must be {expected_status!r}"
                )
            for key in ("decision", "basis"):
                value = entry.get(key)
                if not isinstance(value, str) or not value.strip():
                    issues.append(f"{label}.{key} must be a non-empty string")

    if review.get("approval_status") != "NOT_REQUESTED":
        issues.append("case_mapping_review.approval_status must remain 'NOT_REQUESTED'")
    if review.get("legal_review_status") != "NOT_STARTED":
        issues.append("case_mapping_review.legal_review_status must remain 'NOT_STARTED'")
    _require_string(review, "notes", issues)


def _check_legal_content_review(data: Dict[str, Any], issues: List[str]) -> None:
    review = data.get("legal_content_review")
    if not isinstance(review, dict):
        issues.append("legal_content_review must be an object")
        return

    if review.get("status") != "PACKET_PREPARED":
        issues.append("legal_content_review.status must be 'PACKET_PREPARED'")
    if not _date_is_iso(review.get("prepared_date")):
        issues.append("legal_content_review.prepared_date must be an ISO calendar date")
    if review.get("packet_document") != "rental-legal-content-review-packet.md":
        issues.append(
            "legal_content_review.packet_document must be "
            "'rental-legal-content-review-packet.md'"
        )
    if review.get("agenda_document") != "rental-legal-review-agenda.md":
        issues.append(
            "legal_content_review.agenda_document must be "
            "'rental-legal-review-agenda.md'"
        )
    if review.get("review_performed") is not False:
        issues.append("legal_content_review.review_performed must remain false")
    _require_string(review, "reviewer_required", issues)
    candidate = review.get("reviewer_candidate")
    if candidate is not None:
        if not isinstance(candidate, dict):
            issues.append("legal_content_review.reviewer_candidate must be an object")
        else:
            name = candidate.get("name")
            if not isinstance(name, str) or not name.strip():
                issues.append(
                    "legal_content_review.reviewer_candidate.name must be a "
                    "non-empty string"
                )
            if candidate.get("status") != (
                "PENDING_QUALIFICATION_AND_INDEPENDENCE"
            ):
                issues.append(
                    "legal_content_review.reviewer_candidate.status must remain "
                    "'PENDING_QUALIFICATION_AND_INDEPENDENCE'"
                )
            for key in (
                "qualification",
                "independent_of_project",
                "consent_confirmed",
            ):
                if candidate.get(key) is not None:
                    issues.append(
                        f"legal_content_review.reviewer_candidate.{key} must "
                        "remain null until confirmed"
                    )
            notes = candidate.get("notes")
            if not isinstance(notes, str) or not notes.strip():
                issues.append(
                    "legal_content_review.reviewer_candidate.notes must be a "
                    "non-empty string"
                )
    if review.get("reviewer_assigned") is not False:
        issues.append("legal_content_review.reviewer_assigned must remain false")
    if review.get("review_date") is not None:
        issues.append("legal_content_review.review_date must remain null")
    _require_string(review, "blocking_reason", issues)

    question_ids = review.get("question_ids")
    if not isinstance(question_ids, list) or not question_ids:
        issues.append("legal_content_review.question_ids must be a non-empty list")
        question_ids = []
    else:
        normalized = []
        for question_id in question_ids:
            if not isinstance(question_id, str) or not _LRQ_ID_RE.match(question_id):
                issues.append(
                    "legal_content_review.question_ids must use LRQ-NN identifiers"
                )
                continue
            normalized.append(question_id)
        if len(set(normalized)) != len(normalized):
            issues.append(
                "legal_content_review.question_ids must not contain duplicates"
            )

    question_count = review.get("question_count")
    if not _is_positive_int(question_count):
        issues.append(
            "legal_content_review.question_count must be a positive integer"
        )
    elif question_count != len(question_ids):
        issues.append(
            "legal_content_review.question_count must equal the number of question ids"
        )

    non_claims = review.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims or not all(
        isinstance(item, str) and item.strip() for item in non_claims
    ):
        issues.append(
            "legal_content_review.non_claims must be a non-empty list of strings"
        )

    _check_preflight(review, issues)


def _check_preflight(review: Dict[str, Any], issues: List[str]) -> None:
    preflight = review.get("preflight")
    if not isinstance(preflight, dict):
        issues.append("legal_content_review.preflight must be an object")
        return

    if preflight.get("status") != "PREFLIGHT_COMPLETE":
        issues.append(
            "legal_content_review.preflight.status must be 'PREFLIGHT_COMPLETE'"
        )
    if preflight.get("document") != "rental-legal-content-preflight.md":
        issues.append(
            "legal_content_review.preflight.document must be "
            "'rental-legal-content-preflight.md'"
        )
    if not _date_is_iso(preflight.get("completed_date")):
        issues.append(
            "legal_content_review.preflight.completed_date must be an ISO calendar date"
        )
    _require_string(preflight, "prepared_by", issues)

    if preflight.get("coverage") != "ALL_21_QUESTIONS":
        issues.append(
            "legal_content_review.preflight.coverage must be 'ALL_21_QUESTIONS'"
        )
    if preflight.get("overall_recommendation") != "MODIFY_AND_RECHECK":
        issues.append(
            "legal_content_review.preflight.overall_recommendation must be "
            "'MODIFY_AND_RECHECK'"
        )
    if preflight.get("court_specific_applicability") != (
        "UNDETERMINED_TARGET_COURT_AND_CHANNEL_NOT_SPECIFIED"
    ):
        issues.append(
            "legal_content_review.preflight.court_specific_applicability must "
            "remain 'UNDETERMINED_TARGET_COURT_AND_CHANNEL_NOT_SPECIFIED'"
        )
    if preflight.get("formal_review_status") != "NOT_PERFORMED":
        issues.append(
            "legal_content_review.preflight.formal_review_status must be "
            "'NOT_PERFORMED'"
        )
    if preflight.get("reviewer_signed") is not False:
        issues.append(
            "legal_content_review.preflight.reviewer_signed must remain false"
        )

    samples_path = preflight.get("samples_path")
    if not isinstance(samples_path, str) or not samples_path.startswith(
        "test_samples/"
    ):
        issues.append(
            "legal_content_review.preflight.samples_path must be under test_samples/"
        )
    if preflight.get("samples_git_status") != "IGNORED":
        issues.append(
            "legal_content_review.preflight.samples_git_status must be 'IGNORED'"
        )

    verification = preflight.get("verification")
    if not isinstance(verification, dict):
        issues.append("legal_content_review.preflight.verification must be an object")
    else:
        for key, expected in (
            ("wps_page_check", "COMPLETE"),
            ("microsoft_word_check", "NOT_PERFORMED"),
            ("court_platform_check", "NOT_PERFORMED"),
        ):
            if verification.get(key) != expected:
                issues.append(
                    f"legal_content_review.preflight.verification.{key} must be "
                    f"{expected!r}"
                )

    findings = preflight.get("findings")
    if not isinstance(findings, list) or len(findings) != 4:
        issues.append(
            "legal_content_review.preflight.findings must contain four findings"
        )
        findings = []

    seen_ids = []
    for index, finding in enumerate(findings):
        label = f"legal_content_review.preflight.findings[{index}]"
        if not isinstance(finding, dict):
            issues.append(f"{label} must be an object")
            continue
        finding_id = finding.get("finding_id")
        if not isinstance(finding_id, str) or not _PF_ID_RE.match(finding_id):
            issues.append(f"{label}.finding_id must use PF-NN identifiers")
        else:
            seen_ids.append(finding_id)
        for key in ("title", "evidence", "recommended_action"):
            value = finding.get(key)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"{label}.{key} must be a non-empty string")

        allowed_statuses = {
            "PF-01": {"OPEN", "FIXED_PENDING_RECHECK"},
            "PF-02": {"OPEN", "FIXED_PENDING_RECHECK"},
            "PF-03": {"OPEN"},
            "PF-04": {"OPEN"},
        }
        status = finding.get("status")
        if status not in allowed_statuses.get(finding_id, {"OPEN"}):
            issues.append(
                f"{label}.status is not allowed for {finding_id!r}"
            )
        if status == "FIXED_PENDING_RECHECK":
            fix_evidence = finding.get("fix_evidence")
            if not isinstance(fix_evidence, str) or not fix_evidence.strip():
                issues.append(
                    f"{label}.fix_evidence is required for FIXED_PENDING_RECHECK"
                )

        affected = finding.get("affected_documents")
        if (
            not isinstance(affected, list)
            or not affected
            or any(document not in DOCUMENT_TYPES for document in affected)
        ):
            issues.append(
                f"{label}.affected_documents must be a non-empty list of known "
                "document types"
            )

        for key, pattern in (
            ("linked_questions", _LRQ_ID_RE),
            ("linked_gaps", _GAP_ID_RE),
        ):
            values = finding.get(key)
            if (
                not isinstance(values, list)
                or not values
                or any(
                    not isinstance(value, str) or not pattern.match(value)
                    for value in values
                )
            ):
                issues.append(f"{label}.{key} contains invalid identifiers")

    if preflight.get("finding_ids") != seen_ids:
        issues.append(
            "legal_content_review.preflight.finding_ids must match the findings "
            "in order"
        )

    non_claims = preflight.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims or not all(
        isinstance(item, str) and item.strip() for item in non_claims
    ):
        issues.append(
            "legal_content_review.preflight.non_claims must be a non-empty list "
            "of strings"
        )


def _check_scoped_engineering_authorization(
    data: Dict[str, Any], issues: List[str]
) -> None:
    auth = data.get("scoped_engineering_authorization")
    if not isinstance(auth, dict):
        issues.append("scoped_engineering_authorization must be an object")
        return

    if auth.get("status") != "IMPLEMENTED_PENDING_RECHECK":
        issues.append(
            "scoped_engineering_authorization.status must be "
            "'IMPLEMENTED_PENDING_RECHECK'"
        )
    if not _date_is_iso(auth.get("authorized_date")):
        issues.append(
            "scoped_engineering_authorization.authorized_date must be an ISO date"
        )
    if auth.get("scope") != ["PF-01", "PF-02"]:
        issues.append(
            "scoped_engineering_authorization.scope must be exactly PF-01 and PF-02"
        )
    if auth.get("excluded_findings") != ["PF-03", "PF-04"]:
        issues.append(
            "scoped_engineering_authorization.excluded_findings must be exactly "
            "PF-03 and PF-04"
        )
    if auth.get("overall_implementation_authorization") != "NOT_AUTHORIZED":
        issues.append(
            "scoped_engineering_authorization.overall_implementation_authorization "
            "must remain 'NOT_AUTHORIZED'"
        )
    samples_path = auth.get("recheck_samples_path")
    if not isinstance(samples_path, str) or not samples_path.startswith(
        "test_samples/"
    ):
        issues.append(
            "scoped_engineering_authorization.recheck_samples_path must be under "
            "test_samples/"
        )
    if auth.get("recheck_samples_status") not in {
        "GENERATED_TEXT_VERIFIED_VISUAL_PENDING",
        "VISUAL_VERIFIED",
    }:
        issues.append(
            "scoped_engineering_authorization.recheck_samples_status is not "
            "a supported state"
        )
    for key in (
        "files_changed",
        "tests",
        "recheck_requirements",
        "non_claims",
    ):
        _require_string_list(auth, key, issues)


def _check_mapping_registry_consistency(
    data: Dict[str, Any],
    mapping_registry: Optional[Dict[str, Any]],
    issues: List[str],
) -> None:
    if mapping_registry is None:
        return
    if not isinstance(mapping_registry, dict):
        issues.append("case-template-mapping registry must be a JSON object")
        return

    mappings = mapping_registry.get("mappings")
    if not isinstance(mappings, list):
        issues.append(
            "case-template-mapping registry must contain a 'mappings' list"
        )
        return

    rental = [
        mapping
        for mapping in mappings
        if isinstance(mapping, dict) and mapping.get("case_type") == "rental"
    ]
    if len(rental) != 3:
        issues.append(
            "case-template-mapping registry must contain exactly three rental mappings"
        )
        return

    by_document = {
        mapping.get("document_type"): mapping for mapping in rental
    }
    if set(by_document) != set(DOCUMENT_TYPES):
        issues.append(
            "case-template-mapping rental entries must cover all three document types"
        )
        return

    for document_type in DOCUMENT_TYPES:
        mapping = by_document[document_type]
        label = f"case-template-mapping rental {document_type}"
        expected_id = RENTAL_MAPPING_IDS[document_type]
        if mapping.get("mapping_id") != expected_id:
            issues.append(f"{label}: mapping_id must be {expected_id!r}")
        expected_status = EXPECTED_RENTAL_MAPPING_STATUSES[document_type]
        if mapping.get("mapping_status") != expected_status:
            issues.append(f"{label}: mapping_status must be {expected_status!r}")
        if mapping.get("approval_status") != "NOT_REQUESTED":
            issues.append(f"{label}: approval_status must remain 'NOT_REQUESTED'")
        if document_type == "civil_complaint":
            refs = mapping.get("candidate_source_ids")
            if not isinstance(refs, list) or "spc-2025-notice-pdf" not in refs:
                issues.append(
                    f"{label}: candidate_source_ids must include "
                    "'spc-2025-notice-pdf'"
                )


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
    data: Any,
    source_registry: Optional[Dict[str, Any]] = None,
    mapping_registry: Optional[Dict[str, Any]] = None,
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
    if data.get("central_mapping_registry_updated") is not True:
        issues.append(
            "central_mapping_registry_updated must be true after the mapping review"
        )
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
    _check_text_and_structure_comparison(data, candidate_ids, issues)
    _check_case_mapping_review(data, issues)
    _check_legal_content_review(data, issues)
    _check_scoped_engineering_authorization(data, issues)
    _check_registry_consistency(data, candidate_ids, source_registry, issues)
    _check_mapping_registry_consistency(data, mapping_registry, issues)

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
    parser.add_argument(
        "--mapping-registry", type=Path, default=DEFAULT_MAPPING_REGISTRY
    )
    args = parser.parse_args(argv)

    issues: List[str] = []
    data = _load(args.package, issues)
    registry = _load(args.source_registry, issues)
    mapping_registry = _load(args.mapping_registry, issues)
    if data is not None:
        issues.extend(validate_package(data, registry, mapping_registry))

    if issues:
        print("FAIL rental governance work package is invalid:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(
        "OK   rental governance work package is valid "
        "(PF-01/PF-02 fixed pending recheck, formal review not performed, NO-GO)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
