#!/usr/bin/env python
# File: tools/check_template_crosswalk.py
# Purpose: Deterministic, offline validation of the Phase 1-B official-template
#          crosswalk and gap-analysis records.
# Encoding: UTF-8
"""Validate the official-template gap-analysis records.

Checks the analytical records under
``docs/legal-template-governance/official-gap-analysis/``:

* ``source-extraction-ledger.json``
* ``official-element-inventory.json``
* ``application-field-inventory.json``
* ``field-crosswalk.json``
* ``gap-register.json``
* ``document-route-assessment.json``

The validator is standard-library only, runs offline, reads repository metadata
only, has no side effects and returns a nonzero exit code when the records are
inconsistent.

**Scope of what it proves.** It proves *internal consistency* — that identifiers
resolve, that the fifteen routes exist, that no record claims an approval that
did not happen. It does **not** re-verify the official PDF (it never fetches it)
and it cannot establish source authenticity or legal correctness.

Usage::

    python tools/check_template_crosswalk.py
    python tools/check_template_crosswalk.py --analysis-dir <dir> --source-registry <file>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_DIR = REPO_ROOT / "docs" / "legal-template-governance" / "official-gap-analysis"
DEFAULT_SOURCE_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"

# --- enums -----------------------------------------------------------------

CASE_TYPES = frozenset({"loan", "contract", "property", "labor", "divorce"})
DOCUMENT_TYPES = frozenset({
    "civil_complaint", "evidence_list", "service_address_confirmation",
})

ELEMENT_KINDS = frozenset({
    "PARTY_IDENTITY", "CONTACT", "REPRESENTATIVE", "CLAIM", "FACT",
    "PROCEDURAL", "EVIDENCE", "LEGAL_REFERENCE", "SIGNATURE", "INSTRUCTION",
})
REQUIREMENT_CLASSES = frozenset({
    "REQUIRED_IN_SOURCE", "CONDITIONAL_IN_SOURCE", "OPTIONAL_IN_SOURCE",
    "EXPLANATORY_ONLY", "UNDETERMINED",
})
ORIGIN_KINDS = frozenset({
    "BLANK_FORM", "FILLING_INSTRUCTION", "FILLED_EXAMPLE", "GENERAL_OFFICIAL_GUIDANCE",
})
EXTRACTION_CONFIDENCE = frozenset({
    "TEXT_AND_VISUAL_VERIFIED", "TEXT_VERIFIED", "VISUAL_VERIFIED", "UNVERIFIED", "BLOCKED",
})
COVERAGE_STATUSES = frozenset({
    "DIRECT_MATCH", "PARTIAL_MATCH", "SEMANTIC_MISMATCH", "CONDITIONAL_MISMATCH",
    "CALCULATION_REVIEW_REQUIRED", "NO_CURRENT_APPLICATION_FIELD",
    "APPLICATION_ONLY_ELEMENT", "NOT_APPLICABLE", "SOURCE_UNVERIFIED",
})
GAP_CATEGORIES = frozenset({
    "MISSING_INPUT", "MISSING_OUTPUT", "PARTIAL_FIELD_COVERAGE", "SEMANTIC_DIFFERENCE",
    "CONDITIONALITY_DIFFERENCE", "FACT_INTEGRITY_RISK", "CALCULATION_RISK",
    "PROCEDURAL_APPLICABILITY", "EVIDENCE_PRESENTATION", "PARTY_STRUCTURE",
    "FORMATTING_DIFFERENCE", "SOURCE_VERIFICATION_GAP", "UNRESOLVED_LEGAL_QUESTION",
})
SEVERITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"})
ROUTE_CLASSES = frozenset({
    "CANDIDATE_OFFICIAL_COMPLAINT", "OFFICIAL_SECTION_ONLY",
    "STANDALONE_EQUIVALENCE_UNVERIFIED", "NO_COUNTERPART_IN_INSPECTED_SOURCE",
    "ADDITIONAL_SOURCE_REQUIRED", "BLOCKED",
})
REVIEW_STATUSES = frozenset({"NOT_REQUESTED", "REQUESTED", "IN_REVIEW", "COMPLETED"})
APPROVAL_STATUSES = frozenset({"NOT_REQUESTED", "PENDING", "APPROVED", "REJECTED"})

ELEMENT_REQUIRED = (
    "element_id", "case_type", "official_category_title", "source_id", "source_sha256",
    "pdf_page_start", "pdf_page_end", "document_section", "element_label_or_short_description",
    "element_kind", "requirement_classification", "condition_or_dependency", "origin_kind",
    "extraction_confidence", "verification_evidence", "review_status", "notes",
)
FIELD_REQUIRED = (
    "field_id", "case_type_or_shared", "ui_location", "ui_field_or_widget",
    "presenter_location", "presenter_attribute", "model_location", "model_attribute",
    "calculation_or_condition", "output_document_types", "rendering_location",
    "fact_classification", "missing_value_behavior", "source_code_evidence", "notes",
)
CROSSWALK_REQUIRED = (
    "crosswalk_id", "case_type", "document_type", "official_element_id",
    "application_field_ids", "coverage_status", "semantic_comparison",
    "condition_comparison", "data_provenance_comparison", "output_placement",
    "source_evidence", "code_evidence", "gap_ids", "review_required",
    "open_questions", "notes",
)
GAP_REQUIRED = (
    "gap_id", "case_type", "document_type", "gap_category", "severity",
    "official_element_ids", "application_field_ids", "observed_current_behavior",
    "source_supported_expectation", "difference_description", "risk_if_changed_without_review",
    "potential_remediation", "legal_review_required", "engineering_review_required",
    "source_evidence", "code_evidence", "review_status",
)
ROUTE_REQUIRED = (
    "route_id", "case_type", "document_type", "current_generator", "current_output_summary",
    "official_source_ids", "official_counterpart_classification", "source_verification_status",
    "comparison_scope", "gap_ids", "unresolved_questions", "legal_review_required",
    "approval_status",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BARE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

ANALYSIS_FILES = {
    "ledger": "source-extraction-ledger.json",
    "elements": "official-element-inventory.json",
    "fields": "application-field-inventory.json",
    "crosswalk": "field-crosswalk.json",
    "gaps": "gap-register.json",
    "routes": "document-route-assessment.json",
}


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load(path: Path, issues: List[str]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        issues.append(f"{path}: file not found")
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
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


def _check_enum(label, field, value, allowed, issues, *, optional=False) -> bool:
    if value is None:
        if optional:
            return True
        issues.append(f"{label}: {field} must be a string, got null")
        return False
    if not isinstance(value, str):
        issues.append(f"{label}: {field} must be a string, got {type(value).__name__}")
        return False
    if value not in allowed:
        issues.append(f"{label}: invalid {field} {value!r}")
        return False
    return True


def validate_analysis(analysis_dir: Path, source_registry_path: Path) -> List[str]:
    """Return a list of human-readable issues (empty list == consistent)."""
    issues: List[str] = []

    data: Dict[str, Dict[str, Any]] = {}
    for key, filename in ANALYSIS_FILES.items():
        loaded = _load(Path(analysis_dir) / filename, issues)
        if loaded is not None:
            data[key] = loaded

    # --- source registry (existing, must resolve) --------------------------
    registry_ids: Dict[str, str] = {}
    registry = _load(Path(source_registry_path), issues)
    if registry is not None:
        for src in registry.get("sources", []) if isinstance(registry.get("sources"), list) else []:
            if isinstance(src, dict) and _nonempty_str(src.get("source_id")):
                registry_ids[src["source_id"]] = src.get("content_hash_if_verified") or ""

    ledger = data.get("ledger")
    expected_pages = None
    analyzed_hash = None
    if ledger is not None:
        retrieval = ledger.get("retrieval") if isinstance(ledger.get("retrieval"), dict) else {}
        expected_pages = retrieval.get("pdf_page_count")
        analyzed_hash = retrieval.get("sha256")
        if not isinstance(expected_pages, int) or expected_pages <= 0:
            issues.append("ledger: retrieval.pdf_page_count must be a positive integer")
            expected_pages = None
        if not _nonempty_str(analyzed_hash) or not _BARE_HASH_RE.match(analyzed_hash or ""):
            issues.append("ledger: retrieval.sha256 must be a 64-character lowercase hex digest")
            analyzed_hash = None
        match = (ledger.get("registry_hash_comparison") or {}).get("SOURCE_HASH_MATCH")
        if match not in ("PASS", "FAIL"):
            issues.append("ledger: registry_hash_comparison.SOURCE_HASH_MATCH must be PASS or FAIL")
        if match == "FAIL":
            issues.append("ledger: SOURCE_HASH_MATCH is FAIL — authoritative field claims are blocked")

    source_ids_used: set = set()

    # --- official elements --------------------------------------------------
    elements_by_id: Dict[str, Dict[str, Any]] = {}
    element_case_types: set = set()
    elements = data.get("elements")
    if elements is not None:
        records = elements.get("elements")
        if not isinstance(records, list):
            issues.append("official-element-inventory: 'elements' must be a list")
            records = []
        for index, e in enumerate(records):
            label = f"element[{index}]"
            if not isinstance(e, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in ELEMENT_REQUIRED:
                if field not in e:
                    issues.append(f"{label}: missing required field {field!r}")
            eid = e.get("element_id")
            if isinstance(eid, str):
                label = f"element {eid!r}"
                if not _ID_RE.match(eid):
                    issues.append(f"{label}: element_id has an invalid format")
                if eid in elements_by_id:
                    issues.append(f"{label}: duplicate element_id")
                else:
                    elements_by_id[eid] = e
            elif eid is not None:
                issues.append(f"{label}: element_id must be a string")

            case = e.get("case_type")
            if case in CASE_TYPES:
                element_case_types.add(case)
            else:
                issues.append(f"{label}: unknown case_type {case!r}")

            _check_enum(label, "element_kind", e.get("element_kind"), ELEMENT_KINDS, issues)
            _check_enum(label, "requirement_classification", e.get("requirement_classification"),
                        REQUIREMENT_CLASSES, issues)
            _check_enum(label, "origin_kind", e.get("origin_kind"), ORIGIN_KINDS, issues)
            _check_enum(label, "extraction_confidence", e.get("extraction_confidence"),
                        EXTRACTION_CONFIDENCE, issues)
            _check_enum(label, "review_status", e.get("review_status"), REVIEW_STATUSES, issues)

            sid = e.get("source_id")
            if _nonempty_str(sid):
                source_ids_used.add(sid)
                if registry_ids and sid not in registry_ids:
                    issues.append(f"{label}: source_id {sid!r} does not resolve in the source registry")
            else:
                issues.append(f"{label}: source_id must be a non-empty string")

            sha = e.get("source_sha256")
            if not _nonempty_str(sha) or not _BARE_HASH_RE.match(sha or ""):
                issues.append(f"{label}: source_sha256 must be a 64-character lowercase hex digest")
            elif analyzed_hash and sha != analyzed_hash:
                issues.append(f"{label}: source_sha256 does not match the analyzed ledger hash")

            start, end = e.get("pdf_page_start"), e.get("pdf_page_end")
            if not isinstance(start, int) or not isinstance(end, int):
                issues.append(f"{label}: pdf_page_start/pdf_page_end must be integers")
            else:
                if start < 1 or end < 1 or start > end:
                    issues.append(f"{label}: invalid PDF page range {start}-{end}")
                if expected_pages is not None and (start > expected_pages or end > expected_pages):
                    issues.append(f"{label}: PDF page range {start}-{end} exceeds the observed page count {expected_pages}")

            if not _nonempty_str(e.get("verification_evidence")):
                issues.append(f"{label}: verification_evidence is required for a verified claim")

    if element_case_types and element_case_types != CASE_TYPES:
        issues.append(f"official-element-inventory: case types {sorted(element_case_types)} != all five")

    # --- application fields -------------------------------------------------
    fields_by_id: Dict[str, Dict[str, Any]] = {}
    field_case_types: set = set()
    fields = data.get("fields")
    if fields is not None:
        records = fields.get("fields")
        if not isinstance(records, list):
            issues.append("application-field-inventory: 'fields' must be a list")
            records = []
        for index, f in enumerate(records):
            label = f"field[{index}]"
            if not isinstance(f, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in FIELD_REQUIRED:
                if field not in f:
                    issues.append(f"{label}: missing required field {field!r}")
            fid = f.get("field_id")
            if isinstance(fid, str):
                label = f"field {fid!r}"
                if not _ID_RE.match(fid):
                    issues.append(f"{label}: field_id has an invalid format")
                if fid in fields_by_id:
                    issues.append(f"{label}: duplicate field_id")
                else:
                    fields_by_id[fid] = f
            elif fid is not None:
                issues.append(f"{label}: field_id must be a string")

            case = f.get("case_type_or_shared")
            if case == "shared":
                pass
            elif case in CASE_TYPES:
                field_case_types.add(case)
            else:
                issues.append(f"{label}: unknown case_type_or_shared {case!r}")

            docs = f.get("output_document_types")
            if not isinstance(docs, list):
                issues.append(f"{label}: output_document_types must be a list")
            else:
                for d in docs:
                    if d not in DOCUMENT_TYPES:
                        issues.append(f"{label}: unknown document type {d!r}")

    if field_case_types and field_case_types != CASE_TYPES:
        issues.append(f"application-field-inventory: case types {sorted(field_case_types)} != all five")

    # --- crosswalk ----------------------------------------------------------
    crosswalk_ids: set = set()
    crosswalk_case_types: set = set()
    covered_elements: set = set()
    reverse_covered_fields: set = set()
    crosswalks = data.get("crosswalk")
    if crosswalks is not None:
        records = crosswalks.get("crosswalks")
        if not isinstance(records, list):
            issues.append("field-crosswalk: 'crosswalks' must be a list")
            records = []
        for index, c in enumerate(records):
            label = f"crosswalk[{index}]"
            if not isinstance(c, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in CROSSWALK_REQUIRED:
                if field not in c:
                    issues.append(f"{label}: missing required field {field!r}")
            cid = c.get("crosswalk_id")
            if isinstance(cid, str):
                label = f"crosswalk {cid!r}"
                if not _ID_RE.match(cid):
                    issues.append(f"{label}: crosswalk_id has an invalid format")
                if cid in crosswalk_ids:
                    issues.append(f"{label}: duplicate crosswalk_id")
                else:
                    crosswalk_ids.add(cid)
            elif cid is not None:
                issues.append(f"{label}: crosswalk_id must be a string")

            case = c.get("case_type")
            if case in CASE_TYPES:
                crosswalk_case_types.add(case)
            else:
                issues.append(f"{label}: unknown case_type {case!r}")

            _check_enum(label, "document_type", c.get("document_type"), DOCUMENT_TYPES, issues)
            _check_enum(label, "coverage_status", c.get("coverage_status"), COVERAGE_STATUSES, issues)

            eid = c.get("official_element_id")
            if eid is None:
                if c.get("coverage_status") != "APPLICATION_ONLY_ELEMENT":
                    issues.append(f"{label}: a null official_element_id requires coverage_status APPLICATION_ONLY_ELEMENT")
            elif isinstance(eid, str):
                if eid not in elements_by_id:
                    issues.append(f"{label}: official_element_id {eid!r} does not resolve")
                else:
                    covered_elements.add(eid)
            else:
                issues.append(f"{label}: official_element_id must be a string or null")

            fids = c.get("application_field_ids")
            if not isinstance(fids, list):
                issues.append(f"{label}: application_field_ids must be a list")
            else:
                for fid in fids:
                    if not isinstance(fid, str):
                        issues.append(f"{label}: application_field_ids entries must be strings, got {type(fid).__name__}")
                    elif fid not in fields_by_id:
                        issues.append(f"{label}: application_field_ids {fid!r} does not resolve")
                    else:
                        reverse_covered_fields.add(fid)

            gids = c.get("gap_ids")
            if not isinstance(gids, list):
                issues.append(f"{label}: gap_ids must be a list")
            else:
                for gid in gids:
                    if not isinstance(gid, str):
                        issues.append(f"{label}: gap_ids entries must be strings")

            if not isinstance(c.get("review_required"), bool):
                issues.append(f"{label}: review_required must be a boolean")
            if not _nonempty_str(c.get("source_evidence")):
                issues.append(f"{label}: source_evidence is required")

    if crosswalk_case_types and crosswalk_case_types != CASE_TYPES:
        issues.append(f"field-crosswalk: case types {sorted(crosswalk_case_types)} != all five")

    # every official element must have a crosswalk record
    missing = sorted(set(elements_by_id) - covered_elements)
    if missing:
        issues.append(f"field-crosswalk: {len(missing)} official element(s) have no crosswalk record: {missing[:5]}")

    # --- gaps ---------------------------------------------------------------
    gaps_by_id: Dict[str, Dict[str, Any]] = {}
    gap_case_types: set = set()
    gaps = data.get("gaps")
    if gaps is not None:
        records = gaps.get("gaps")
        if not isinstance(records, list):
            issues.append("gap-register: 'gaps' must be a list")
            records = []
        for index, g in enumerate(records):
            label = f"gap[{index}]"
            if not isinstance(g, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in GAP_REQUIRED:
                if field not in g:
                    issues.append(f"{label}: missing required field {field!r}")
            gid = g.get("gap_id")
            if isinstance(gid, str):
                label = f"gap {gid!r}"
                if not _ID_RE.match(gid):
                    issues.append(f"{label}: gap_id has an invalid format")
                if gid in gaps_by_id:
                    issues.append(f"{label}: duplicate gap_id")
                else:
                    gaps_by_id[gid] = g
            elif gid is not None:
                issues.append(f"{label}: gap_id must be a string")

            case = g.get("case_type")
            if case in CASE_TYPES:
                gap_case_types.add(case)
            else:
                issues.append(f"{label}: unknown case_type {case!r}")

            _check_enum(label, "document_type", g.get("document_type"), DOCUMENT_TYPES, issues)
            _check_enum(label, "gap_category", g.get("gap_category"), GAP_CATEGORIES, issues)
            _check_enum(label, "severity", g.get("severity"), SEVERITIES, issues)
            _check_enum(label, "review_status", g.get("review_status"), REVIEW_STATUSES, issues)

            for field in ("observed_current_behavior", "source_supported_expectation",
                          "difference_description", "potential_remediation"):
                if not _nonempty_str(g.get(field)):
                    issues.append(f"{label}: {field} must be a non-empty string")

            for eid in g.get("official_element_ids") or []:
                if not isinstance(eid, str) or eid not in elements_by_id:
                    issues.append(f"{label}: official_element_ids {eid!r} does not resolve")
            for fid in g.get("application_field_ids") or []:
                if not isinstance(fid, str) or fid not in fields_by_id:
                    issues.append(f"{label}: application_field_ids {fid!r} does not resolve")

    if gap_case_types and gap_case_types != CASE_TYPES:
        issues.append(f"gap-register: case types {sorted(gap_case_types)} != all five")

    # crosswalk gap references must resolve
    if crosswalks is not None:
        for c in crosswalks.get("crosswalks", []) if isinstance(crosswalks.get("crosswalks"), list) else []:
            if not isinstance(c, dict):
                continue
            for gid in c.get("gap_ids") or []:
                if isinstance(gid, str) and gid not in gaps_by_id:
                    issues.append(f"crosswalk {c.get('crosswalk_id')!r}: gap_ids {gid!r} does not resolve")

    # --- routes -------------------------------------------------------------
    route_ids: set = set()
    route_combos: set = set()
    routes = data.get("routes")
    if routes is not None:
        records = routes.get("routes")
        if not isinstance(records, list):
            issues.append("document-route-assessment: 'routes' must be a list")
            records = []
        for index, r in enumerate(records):
            label = f"route[{index}]"
            if not isinstance(r, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in ROUTE_REQUIRED:
                if field not in r:
                    issues.append(f"{label}: missing required field {field!r}")
            rid = r.get("route_id")
            if isinstance(rid, str):
                label = f"route {rid!r}"
                if not _ID_RE.match(rid):
                    issues.append(f"{label}: route_id has an invalid format")
                if rid in route_ids:
                    issues.append(f"{label}: duplicate route_id")
                else:
                    route_ids.add(rid)
            elif rid is not None:
                issues.append(f"{label}: route_id must be a string")

            case, doc = r.get("case_type"), r.get("document_type")
            if case not in CASE_TYPES:
                issues.append(f"{label}: unknown case_type {case!r}")
            if doc not in DOCUMENT_TYPES:
                issues.append(f"{label}: unknown document_type {doc!r}")
            if case in CASE_TYPES and doc in DOCUMENT_TYPES:
                combo = (case, doc)
                if combo in route_combos:
                    issues.append(f"{label}: duplicate case-document route {combo}")
                else:
                    route_combos.add(combo)

            _check_enum(label, "official_counterpart_classification",
                        r.get("official_counterpart_classification"), ROUTE_CLASSES, issues)
            _check_enum(label, "approval_status", r.get("approval_status"), APPROVAL_STATUSES, issues)

            if r.get("approval_status") == "APPROVED":
                issues.append(f"{label}: an analytical route must never be APPROVED")

            for sid in r.get("official_source_ids") or []:
                if not isinstance(sid, str) or (registry_ids and sid not in registry_ids):
                    issues.append(f"{label}: official_source_ids {sid!r} does not resolve in the source registry")
                else:
                    source_ids_used.add(sid)
            for gid in r.get("gap_ids") or []:
                if isinstance(gid, str) and gid not in gaps_by_id:
                    issues.append(f"{label}: gap_ids {gid!r} does not resolve")

            if not isinstance(r.get("legal_review_required"), bool):
                issues.append(f"{label}: legal_review_required must be a boolean")
            if not _nonempty_str(r.get("current_generator")):
                issues.append(f"{label}: current_generator must be a non-empty string")

    expected_combos = {(c, d) for c in CASE_TYPES for d in DOCUMENT_TYPES}
    if route_combos and route_combos != expected_combos:
        issues.append(f"document-route-assessment: routes {sorted(route_combos)} != all 15 combinations")
    if route_combos and len(route_combos) != 15:
        issues.append(f"document-route-assessment: expected exactly 15 unique routes, found {len(route_combos)}")

    # --- approval integrity -------------------------------------------------
    for key, records_field in (("crosswalk", "crosswalks"), ("gaps", "gaps")):
        block = data.get(key)
        if not isinstance(block, dict):
            continue
        for rec in block.get(records_field) or []:
            if isinstance(rec, dict) and rec.get("approval_status") == "APPROVED":
                issues.append(f"{key}: record claims APPROVED, which is not permitted in the analysis")

    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the official-template crosswalk and gap-analysis records."
    )
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--source-registry", default=str(DEFAULT_SOURCE_REGISTRY))
    args = parser.parse_args(argv)

    issues = validate_analysis(Path(args.analysis_dir), Path(args.source_registry))

    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        print(f"FAIL template crosswalk records: {len(issues)} issue(s)")
        return 1

    print("OK   template crosswalk records are internally consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
