#!/usr/bin/env python
# File: tools/check_template_adaptation_plan.py
# Purpose: Deterministic, offline validation of the Phase 1-C adaptation planning
#          records against the frozen Phase 1-B analysis.
# Encoding: UTF-8
"""Validate the official-template adaptation planning records.

Reads (read-only):

* ``docs/legal-template-governance/source-registry.json``
* ``docs/legal-template-governance/case-template-mapping.json``
* ``docs/legal-template-governance/official-gap-analysis/`` (frozen analysis)
* ``docs/legal-template-governance/official-adaptation-planning/`` (this plan)

and checks that the plan is internally consistent **and** that it grants nothing:

* all fifteen routes are assessed exactly once and resolve to a frozen route;
* every frozen gap is accounted for exactly once and no unknown gap is introduced;
* every work-package reference (route, gap, crosswalk, source) resolves;
* review dependencies are explicit and a HIGH-severity gap is never deferrable;
* every route and every work package is ``NOT_AUTHORIZED``;
* no planning record may claim an approval, a completed review, a cleared rights
  gate or an approved source without recorded evidence for that stage;
* missing or malformed authorization data fails closed.

The validator is standard-library only, runs offline, reads repository metadata
only and has no side effects.

**What it cannot do.** It proves planning consistency. It cannot establish legal
correctness, rights ownership, the authenticity of a human reviewer, court
acceptance, actual approval authority, or the suitability of any final document.
A passing run is **not** a legal approval and **not** an implementation
authorization.

Usage::

    python tools/check_template_adaptation_plan.py
    python tools/check_template_adaptation_plan.py --planning-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DIR = REPO_ROOT / "docs" / "legal-template-governance"
DEFAULT_ANALYSIS_DIR = GOVERNANCE_DIR / "official-gap-analysis"
DEFAULT_PLANNING_DIR = GOVERNANCE_DIR / "official-adaptation-planning"
DEFAULT_SOURCE_REGISTRY = GOVERNANCE_DIR / "source-registry.json"
DEFAULT_MAPPING_REGISTRY = GOVERNANCE_DIR / "case-template-mapping.json"

# --- enums -----------------------------------------------------------------

CASE_TYPES = frozenset({"loan", "contract", "property", "labor", "divorce"})
DOCUMENT_TYPES = frozenset({
    "civil_complaint", "evidence_list", "service_address_confirmation",
})

READINESS_CLASSIFICATIONS = frozenset({
    "ANALYSIS_COMPLETE", "PLANNING_READY", "SOURCE_REVIEW_REQUIRED",
    "LEGAL_REVIEW_REQUIRED", "RIGHTS_REVIEW_REQUIRED", "PROCEDURAL_REVIEW_REQUIRED",
    "ENGINEERING_DESIGN_REQUIRED", "BLOCKED",
})
ENGINEERING_READINESS = frozenset({
    "ENGINEERING_DESIGN_REQUIRED", "ENGINEERING_DESIGN_BLOCKED",
})
SOURCE_VERIFICATION_STATES = frozenset({
    "DISCOVERED", "ANNOUNCEMENT_VERIFIED", "SOURCE_FILE_VERIFIED", "CONTENT_REVIEWED",
    "MAPPING_REVIEWED", "APPROVED_FOR_ADAPTATION", "REJECTED", "UNAVAILABLE",
    "NO_CANDIDATE_SOURCE_IDENTIFIED", "NOT_ASSESSED",
})
MAPPING_REVIEW_STATES = frozenset({
    "UNVERIFIED", "CANDIDATE_SOURCE_IDENTIFIED", "MAPPING_REVIEWED", "APPROVED",
    "REJECTED", "NO_OFFICIAL_SOURCE_IDENTIFIED",
})
REVIEW_STATES = frozenset({"NOT_REQUESTED", "REQUESTED", "IN_REVIEW", "COMPLETED"})
RIGHTS_REVIEW_STATES = frozenset({"NOT_REVIEWED", "REVIEWED", "NOT_APPLICABLE"})
PROCEDURAL_STATES = frozenset({
    "NOT_APPLICABLE", "PROCEDURAL_REVIEW_REQUIRED", "PROCEDURAL_REVIEW_COMPLETED",
})
# The only implementation authorization value permitted anywhere in the plan.
AUTHORIZATION_STATES = frozenset({"NOT_AUTHORIZED"})
PLANNING_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
SEVERITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"})
REVIEW_DEPENDENCIES = frozenset({
    "SOURCE_VERIFICATION", "MAPPING_APPLICABILITY_REVIEW", "LEGAL_CONTENT_REVIEW",
    "RIGHTS_REVIEW", "PROCEDURAL_REVIEW", "ENGINEERING_DESIGN",
})
IMPLEMENTATION_SEQUENCE_STAGES = frozenset({
    "SOURCE_AND_LEGAL_REVIEW", "ENGINEERING_DESIGN", "FIELD_COLLECTION",
    "DATA_FLOW_INTEGRATION", "DOCUMENT_RENDERING", "REGRESSION_AND_VISUAL_INSPECTION",
    "RELEASE_REVIEW",
})
RISK_DIMENSIONS = (
    "factual_integrity_impact", "monetary_calculation_impact", "procedural_applicability",
    "source_verification_dependency", "legal_content_review_dependency",
    "rights_redistribution_dependency", "engineering_implementation_complexity",
    "regression_risk", "reversibility", "cross_case_impact", "user_facing_consequence",
)

ROUTE_REQUIRED = (
    "route_id", "case_type", "document_type", "governance_mapping_id", "source_ids",
    "candidate_source_ids", "official_counterpart_classification", "linked_gap_ids",
    "high_risk_gap_ids", "readiness_classification", "source_verification_state",
    "mapping_review_state", "legal_content_review_state", "rights_review_state",
    "procedural_applicability_state", "engineering_readiness",
    "implementation_authorization", "blocking_conditions", "review_required",
    "recommended_next_action", "evidence_references",
)
GAP_PRIORITY_REQUIRED = (
    "gap_id", "case_type", "document_type", "frozen_severity", "frozen_gap_category",
    "planning_priority", "priority_score", "risk_dimensions", "review_dependencies",
    "candidate_work_package_ids", "can_be_deferred", "deferral_rationale",
    "evidence_references",
)
WORK_PACKAGE_REQUIRED = (
    "work_package_id", "title", "case_type", "document_type", "linked_route_id",
    "linked_gap_ids", "linked_crosswalk_ids", "source_ids", "objective",
    "proposed_ui_changes", "proposed_model_changes", "proposed_presenter_changes",
    "proposed_docx_changes", "calculation_effects", "fact_integrity_requirements",
    "review_dependencies", "rights_dependencies", "regression_test_requirements",
    "rollback_requirements", "implementation_sequence", "implementation_authorization",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")

ANALYSIS_FILES = {
    "elements": "official-element-inventory.json",
    "fields": "application-field-inventory.json",
    "crosswalk": "field-crosswalk.json",
    "gaps": "gap-register.json",
    "routes": "document-route-assessment.json",
}
PLANNING_FILES = {
    "readiness": "route-readiness.json",
    "prioritization": "gap-prioritization.json",
    "packages": "adaptation-work-packages.json",
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


def _check_enum(label, field, value, allowed, issues, *, optional=False) -> Optional[str]:
    """Validate an enumeration; type is established before membership."""
    if value is None:
        if optional:
            return None
        issues.append(f"{label}: {field} must be a string, got null")
        return None
    if not isinstance(value, str):
        issues.append(f"{label}: {field} must be a string, got {type(value).__name__}")
        return None
    if value not in allowed:
        issues.append(f"{label}: invalid {field} {value!r}")
        return None
    return value


def _check_string_list(label, field, value, issues, *, optional=False) -> Optional[List[str]]:
    if value is None:
        if optional:
            return None
        issues.append(f"{label}: {field} must be a list, got null")
        return None
    if not isinstance(value, list):
        issues.append(f"{label}: {field} must be a list, got {type(value).__name__}")
        return None
    for item in value:
        if not isinstance(item, str):
            issues.append(f"{label}: {field} entries must be strings, got {type(item).__name__}")
            return None
    return value


def _check_nonempty_string_list(label, field, value, issues) -> Optional[List[str]]:
    items = _check_string_list(label, field, value, issues)
    if items is None:
        return None
    if not items:
        issues.append(f"{label}: {field} must not be empty")
        return None
    for item in items:
        if not item.strip():
            issues.append(f"{label}: {field} must not contain blank entries")
            return None
    return items


def _check_bool(label, field, value, issues) -> Optional[bool]:
    if not isinstance(value, bool):
        issues.append(f"{label}: {field} must be a boolean, got {type(value).__name__}")
        return None
    return value


def _require_not_authorized(label, value, issues) -> bool:
    """Fail closed: anything other than the literal NOT_AUTHORIZED is an error."""
    if value is None:
        issues.append(f"{label}: implementation_authorization is required and must be "
                      f"'NOT_AUTHORIZED' (missing authorization fails closed)")
        return False
    if not isinstance(value, str):
        issues.append(f"{label}: implementation_authorization must be a string, "
                      f"got {type(value).__name__}")
        return False
    if value not in AUTHORIZATION_STATES:
        issues.append(f"{label}: implementation_authorization {value!r} is not permitted; "
                      f"only 'NOT_AUTHORIZED' is valid in the planning phase")
        return False
    return True


def validate_plan(planning_dir: Path, analysis_dir: Path, source_registry_path: Path,
                  mapping_registry_path: Path) -> List[str]:
    """Return a list of human-readable issues (empty list == consistent)."""
    issues: List[str] = []

    analysis: Dict[str, Dict[str, Any]] = {}
    for key, filename in ANALYSIS_FILES.items():
        loaded = _load(Path(analysis_dir) / filename, issues)
        if loaded is not None:
            analysis[key] = loaded

    plan: Dict[str, Dict[str, Any]] = {}
    for key, filename in PLANNING_FILES.items():
        loaded = _load(Path(planning_dir) / filename, issues)
        if loaded is not None:
            plan[key] = loaded

    # --- frozen inputs ------------------------------------------------------
    registry_ids: Dict[str, Dict[str, Any]] = {}
    registry = _load(Path(source_registry_path), issues)
    if registry is not None:
        sources = registry.get("sources")
        if not isinstance(sources, list):
            issues.append(f"{source_registry_path}: 'sources' must be a list")
            sources = []
        for index, src in enumerate(sources):
            if not isinstance(src, dict):
                issues.append(f"source-registry sources[{index}]: record must be a JSON object")
                continue
            sid = src.get("source_id")
            if _nonempty_str(sid):
                registry_ids[sid] = src

    mapping_ids: Dict[str, Dict[str, Any]] = {}
    mapping_by_key: Dict[Any, Dict[str, Any]] = {}
    mappings_doc = _load(Path(mapping_registry_path), issues)
    if mappings_doc is not None:
        records = mappings_doc.get("mappings")
        if not isinstance(records, list):
            issues.append(f"{mapping_registry_path}: 'mappings' must be a list")
            records = []
        for index, m in enumerate(records):
            if not isinstance(m, dict):
                issues.append(f"case-template-mapping mappings[{index}]: record must be a JSON object")
                continue
            mid = m.get("mapping_id")
            if _nonempty_str(mid):
                mapping_ids[mid] = m
                mapping_by_key[(m.get("case_type"), m.get("document_type"))] = m

    elements_by_id: Dict[str, Dict[str, Any]] = {}
    if "elements" in analysis:
        for e in analysis["elements"].get("elements") or []:
            if isinstance(e, dict) and _nonempty_str(e.get("element_id")):
                elements_by_id[e["element_id"]] = e

    fields_by_id: Dict[str, Dict[str, Any]] = {}
    if "fields" in analysis:
        for f in analysis["fields"].get("fields") or []:
            if isinstance(f, dict) and _nonempty_str(f.get("field_id")):
                fields_by_id[f["field_id"]] = f

    crosswalk_ids: set = set()
    if "crosswalk" in analysis:
        for c in analysis["crosswalk"].get("crosswalks") or []:
            if isinstance(c, dict) and _nonempty_str(c.get("crosswalk_id")):
                crosswalk_ids.add(c["crosswalk_id"])

    frozen_gaps: Dict[str, Dict[str, Any]] = {}
    if "gaps" in analysis:
        for g in analysis["gaps"].get("gaps") or []:
            if isinstance(g, dict) and _nonempty_str(g.get("gap_id")):
                frozen_gaps[g["gap_id"]] = g

    frozen_routes: Dict[str, Dict[str, Any]] = {}
    route_by_combo: Dict[Any, Dict[str, Any]] = {}
    if "routes" in analysis:
        for r in analysis["routes"].get("routes") or []:
            if isinstance(r, dict) and _nonempty_str(r.get("route_id")):
                frozen_routes[r["route_id"]] = r
                route_by_combo[(r.get("case_type"), r.get("document_type"))] = r

    # --- route readiness ----------------------------------------------------
    readiness_ids: set = set()
    readiness_combos: set = set()
    high_gaps_seen: set = set()
    readiness_records = plan.get("readiness")
    if readiness_records is not None:
        records = readiness_records.get("routes")
        if not isinstance(records, list):
            issues.append("route-readiness: 'routes' must be a list")
            records = []
        for index, r in enumerate(records):
            label = f"readiness[{index}]"
            if not isinstance(r, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in ROUTE_REQUIRED:
                if field not in r:
                    issues.append(f"{label}: missing required field {field!r}")
            rid = r.get("route_id")
            if isinstance(rid, str):
                label = f"readiness {rid!r}"
                if not _ID_RE.match(rid):
                    issues.append(f"{label}: route_id has an invalid format")
                if rid in readiness_ids:
                    issues.append(f"{label}: duplicate route_id")
                else:
                    readiness_ids.add(rid)
            elif rid is not None:
                issues.append(f"{label}: route_id must be a string")

            case = _check_enum(label, "case_type", r.get("case_type"), CASE_TYPES, issues)
            doc = _check_enum(label, "document_type", r.get("document_type"), DOCUMENT_TYPES, issues)

            frozen = frozen_routes.get(rid) if isinstance(rid, str) else None
            if isinstance(rid, str) and frozen is None:
                issues.append(f"{label}: route_id does not resolve in the frozen route inventory")
            elif frozen is not None:
                if frozen.get("case_type") != case or frozen.get("document_type") != doc:
                    issues.append(
                        f"{label}: case/document ({case!r}, {doc!r}) does not match the frozen "
                        f"route ({frozen.get('case_type')!r}, {frozen.get('document_type')!r})"
                    )
                expected_gaps = sorted(g for g in (frozen.get("gap_ids") or [])
                                       if isinstance(g, str))
                listed = _check_string_list(label, "linked_gap_ids",
                                            r.get("linked_gap_ids"), issues)
                if listed is not None and sorted(listed) != expected_gaps:
                    issues.append(
                        f"{label}: linked_gap_ids do not match the frozen route gap set "
                        f"({len(listed)} listed vs {len(expected_gaps)} frozen)"
                    )
                if listed is not None:
                    for gid in listed:
                        if gid not in frozen_gaps:
                            issues.append(f"{label}: linked gap {gid!r} is not a frozen gap")
                expected_high = sorted(g for g in expected_gaps
                                       if frozen_gaps.get(g, {}).get("severity") == "HIGH")
                high = _check_string_list(label, "high_risk_gap_ids",
                                          r.get("high_risk_gap_ids"), issues)
                if high is not None and sorted(high) != expected_high:
                    issues.append(f"{label}: high_risk_gap_ids do not match the frozen HIGH set")
                if high is not None:
                    high_gaps_seen.update(high)

            if case is not None and doc is not None:
                combo = (case, doc)
                if combo in readiness_combos:
                    issues.append(f"{label}: duplicate case-document route {combo}")
                else:
                    readiness_combos.add(combo)

            mid = r.get("governance_mapping_id")
            if not _nonempty_str(mid):
                issues.append(f"{label}: governance_mapping_id must be a non-empty string")
            elif mid not in mapping_ids:
                issues.append(f"{label}: governance_mapping_id {mid!r} does not resolve")
            else:
                m = mapping_ids[mid]
                if m.get("case_type") != case or m.get("document_type") != doc:
                    issues.append(f"{label}: governance mapping {mid!r} covers a different case/document")

            for field in ("source_ids", "candidate_source_ids"):
                ids = _check_string_list(label, field, r.get(field), issues, optional=True)
                for sid in ids or []:
                    if sid not in registry_ids:
                        issues.append(f"{label}: {field} {sid!r} does not resolve in the source registry")

            _check_enum(label, "readiness_classification", r.get("readiness_classification"),
                        READINESS_CLASSIFICATIONS, issues)
            _check_enum(label, "engineering_readiness", r.get("engineering_readiness"),
                        ENGINEERING_READINESS, issues)
            _check_enum(label, "official_counterpart_classification",
                        r.get("official_counterpart_classification"),
                        frozenset({
                            "CANDIDATE_OFFICIAL_COMPLAINT", "OFFICIAL_SECTION_ONLY",
                            "STANDALONE_EQUIVALENCE_UNVERIFIED",
                            "NO_COUNTERPART_IN_INSPECTED_SOURCE", "ADDITIONAL_SOURCE_REQUIRED",
                            "BLOCKED",
                        }), issues)

            source_state = _check_enum(label, "source_verification_state",
                                       r.get("source_verification_state"),
                                       SOURCE_VERIFICATION_STATES, issues)
            _check_enum(label, "mapping_review_state", r.get("mapping_review_state"),
                        MAPPING_REVIEW_STATES, issues)
            legal_state = _check_enum(label, "legal_content_review_state",
                                      r.get("legal_content_review_state"), REVIEW_STATES, issues)
            rights_state = _check_enum(label, "rights_review_state",
                                       r.get("rights_review_state"), RIGHTS_REVIEW_STATES, issues)
            _check_enum(label, "procedural_applicability_state",
                        r.get("procedural_applicability_state"), PROCEDURAL_STATES, issues)

            # No planning status may masquerade as legal approval.
            if legal_state == "COMPLETED" and not _nonempty_str(r.get("legal_content_review_evidence")):
                issues.append(
                    f"{label}: legal_content_review_state 'COMPLETED' requires "
                    f"legal_content_review_evidence"
                )
            if rights_state == "REVIEWED" and not _nonempty_str(r.get("rights_review_evidence")):
                issues.append(
                    f"{label}: rights_review_state 'REVIEWED' requires rights_review_evidence"
                )
            if source_state == "APPROVED_FOR_ADAPTATION" and not _nonempty_str(
                    r.get("source_approval_evidence")):
                issues.append(
                    f"{label}: source_verification_state 'APPROVED_FOR_ADAPTATION' requires "
                    f"source_approval_evidence"
                )
            # A verified file is not an approved source.
            if source_state == "SOURCE_FILE_VERIFIED" and r.get("mapping_review_state") == "APPROVED":
                issues.append(
                    f"{label}: a SOURCE_FILE_VERIFIED source cannot back an APPROVED mapping"
                )

            _check_nonempty_string_list(label, "blocking_conditions",
                                        r.get("blocking_conditions"), issues)
            _check_bool(label, "review_required", r.get("review_required"), issues)
            if r.get("review_required") is False:
                issues.append(f"{label}: review_required must not be false in the planning phase")
            if not _nonempty_str(r.get("recommended_next_action")):
                issues.append(f"{label}: recommended_next_action must be a non-empty string")
            _check_nonempty_string_list(label, "evidence_references",
                                        r.get("evidence_references"), issues)
            _require_not_authorized(label, r.get("implementation_authorization"), issues)

    if readiness_records is not None and len(readiness_ids) != 15:
        issues.append(f"route-readiness: expected exactly 15 route records, found {len(readiness_ids)}")
    if readiness_combos and len(readiness_combos) != 15:
        issues.append(f"route-readiness: expected 15 unique case-document routes, found {len(readiness_combos)}")

    # --- gap prioritization -------------------------------------------------
    prioritization_ids: set = set()
    prioritized_high: set = set()
    prioritization = plan.get("prioritization")
    if prioritization is not None:
        records = prioritization.get("gaps")
        if not isinstance(records, list):
            issues.append("gap-prioritization: 'gaps' must be a list")
            records = []
        for index, p in enumerate(records):
            label = f"prioritization[{index}]"
            if not isinstance(p, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in GAP_PRIORITY_REQUIRED:
                if field not in p:
                    issues.append(f"{label}: missing required field {field!r}")
            gid = p.get("gap_id")
            if isinstance(gid, str):
                label = f"prioritization {gid!r}"
                if gid in prioritization_ids:
                    issues.append(f"{label}: duplicate prioritized gap_id")
                else:
                    prioritization_ids.add(gid)
                if gid not in frozen_gaps:
                    issues.append(f"{label}: gap_id is not a frozen gap and must not be introduced")
            elif gid is not None:
                issues.append(f"{label}: gap_id must be a string")

            frozen = frozen_gaps.get(gid) if isinstance(gid, str) else None
            if frozen is not None:
                if p.get("case_type") != frozen.get("case_type") or \
                        p.get("document_type") != frozen.get("document_type"):
                    issues.append(f"{label}: case/document does not match the frozen gap record")
                if p.get("frozen_severity") != frozen.get("severity"):
                    issues.append(f"{label}: frozen_severity does not match the frozen gap record")
                if p.get("frozen_gap_category") != frozen.get("gap_category"):
                    issues.append(f"{label}: frozen_gap_category does not match the frozen gap record")
            else:
                _check_enum(label, "case_type", p.get("case_type"), CASE_TYPES, issues)
                _check_enum(label, "document_type", p.get("document_type"), DOCUMENT_TYPES, issues)
                _check_enum(label, "frozen_severity", p.get("frozen_severity"), SEVERITIES, issues)

            priority = _check_enum(label, "planning_priority", p.get("planning_priority"),
                                   PLANNING_PRIORITIES, issues)
            score = p.get("priority_score")
            if not isinstance(score, int) or isinstance(score, bool) or not (0 <= score <= 100):
                issues.append(f"{label}: priority_score must be an integer between 0 and 100")

            dims = p.get("risk_dimensions")
            if not isinstance(dims, dict):
                issues.append(f"{label}: risk_dimensions must be a JSON object")
            else:
                for key in RISK_DIMENSIONS:
                    value = dims.get(key)
                    if not isinstance(value, int) or isinstance(value, bool) or not (0 <= value <= 3):
                        issues.append(f"{label}: risk_dimensions.{key} must be an integer 0-3")
                for key in dims:
                    if key not in RISK_DIMENSIONS:
                        issues.append(f"{label}: unknown risk dimension {key!r}")

            deps = _check_nonempty_string_list(label, "review_dependencies",
                                               p.get("review_dependencies"), issues)
            for dep in deps or []:
                if dep not in REVIEW_DEPENDENCIES:
                    issues.append(f"{label}: unknown review dependency {dep!r}")

            wps = _check_nonempty_string_list(label, "candidate_work_package_ids",
                                              p.get("candidate_work_package_ids"), issues)
            if wps is None:
                pass  # already reported
            else:
                for wid in wps:
                    if wid not in {
                        wp.get("work_package_id")
                        for wp in (plan.get("packages", {}).get("work_packages") or [])
                        if isinstance(wp, dict)
                    }:
                        issues.append(f"{label}: candidate work package {wid!r} does not resolve")

            can_defer = _check_bool(label, "can_be_deferred", p.get("can_be_deferred"), issues)
            if not _nonempty_str(p.get("deferral_rationale")):
                issues.append(f"{label}: deferral_rationale must be a non-empty string")
            _check_nonempty_string_list(label, "evidence_references",
                                        p.get("evidence_references"), issues)

            if frozen is not None and frozen.get("severity") == "HIGH":
                prioritized_high.add(gid)
                if priority is not None and priority != "P0":
                    issues.append(f"{label}: a HIGH-severity gap must be planning_priority P0")
                if can_defer is True:
                    issues.append(f"{label}: a HIGH-severity gap must not be deferrable")
                if deps is not None and not deps:
                    issues.append(f"{label}: a HIGH-severity gap must record review dependencies")

    # coverage: every frozen gap exactly once, nothing invented
    missing = sorted(set(frozen_gaps) - prioritization_ids)
    if missing:
        issues.append(f"gap-prioritization: {len(missing)} frozen gap(s) are not prioritized: {missing[:5]}")
    extra = sorted(prioritization_ids - set(frozen_gaps))
    if extra:
        issues.append(f"gap-prioritization: {len(extra)} unknown gap(s) introduced: {extra[:5]}")

    # --- work packages ------------------------------------------------------
    package_ids: set = set()
    packages = plan.get("packages")
    if packages is not None:
        records = packages.get("work_packages")
        if not isinstance(records, list):
            issues.append("adaptation-work-packages: 'work_packages' must be a list")
            records = []
        for index, wp in enumerate(records):
            label = f"work_package[{index}]"
            if not isinstance(wp, dict):
                issues.append(f"{label}: record must be a JSON object")
                continue
            for field in WORK_PACKAGE_REQUIRED:
                if field not in wp:
                    issues.append(f"{label}: missing required field {field!r}")
            wid = wp.get("work_package_id")
            if isinstance(wid, str):
                label = f"work_package {wid!r}"
                if not _ID_RE.match(wid):
                    issues.append(f"{label}: work_package_id has an invalid format")
                if wid in package_ids:
                    issues.append(f"{label}: duplicate work_package_id")
                else:
                    package_ids.add(wid)
            elif wid is not None:
                issues.append(f"{label}: work_package_id must be a string")

            case = _check_enum(label, "case_type", wp.get("case_type"), CASE_TYPES, issues)
            doc = _check_enum(label, "document_type", wp.get("document_type"),
                              DOCUMENT_TYPES, issues)

            rid = wp.get("linked_route_id")
            if not _nonempty_str(rid):
                issues.append(f"{label}: linked_route_id must be a non-empty string")
            elif rid not in frozen_routes:
                issues.append(f"{label}: linked_route_id {rid!r} does not resolve")
            else:
                frozen_route = frozen_routes[rid]
                if frozen_route.get("case_type") != case or \
                        frozen_route.get("document_type") != doc:
                    issues.append(f"{label}: linked route covers a different case/document")

            if case is not None and doc is not None:
                expected_route = route_by_combo.get((case, doc))
                if expected_route is not None and rid != expected_route.get("route_id"):
                    issues.append(
                        f"{label}: linked_route_id {rid!r} is not the route for ({case!r}, {doc!r})"
                    )

            gaps_list = _check_nonempty_string_list(label, "linked_gap_ids",
                                                    wp.get("linked_gap_ids"), issues)
            for gid in gaps_list or []:
                if gid not in frozen_gaps:
                    issues.append(f"{label}: linked gap {gid!r} does not resolve")
                elif frozen_gaps[gid].get("case_type") != case or \
                        frozen_gaps[gid].get("document_type") != doc:
                    issues.append(f"{label}: linked gap {gid!r} belongs to a different case/document")

            cross_list = _check_string_list(label, "linked_crosswalk_ids",
                                            wp.get("linked_crosswalk_ids"), issues)
            for cid in cross_list or []:
                if cid not in crosswalk_ids:
                    issues.append(f"{label}: linked crosswalk {cid!r} does not resolve")

            src_list = _check_string_list(label, "source_ids", wp.get("source_ids"), issues)
            for sid in src_list or []:
                if sid not in registry_ids:
                    issues.append(f"{label}: source_id {sid!r} does not resolve in the source registry")

            for field in ("objective", "calculation_effects"):
                if not _nonempty_str(wp.get(field)):
                    issues.append(f"{label}: {field} must be a non-empty string")
            for field in ("title",):
                if not _nonempty_str(wp.get(field)):
                    issues.append(f"{label}: {field} must be a non-empty string")

            for field in ("proposed_ui_changes", "proposed_model_changes",
                          "proposed_presenter_changes", "proposed_docx_changes",
                          "fact_integrity_requirements", "rights_dependencies",
                          "regression_test_requirements", "rollback_requirements"):
                _check_nonempty_string_list(label, field, wp.get(field), issues)

            deps = _check_nonempty_string_list(label, "review_dependencies",
                                               wp.get("review_dependencies"), issues)
            for dep in deps or []:
                if dep not in REVIEW_DEPENDENCIES:
                    issues.append(f"{label}: unknown review dependency {dep!r}")

            seq = _check_nonempty_string_list(label, "implementation_sequence",
                                              wp.get("implementation_sequence"), issues)
            for stage in seq or []:
                if stage not in IMPLEMENTATION_SEQUENCE_STAGES:
                    issues.append(f"{label}: unknown implementation stage {stage!r}")

            _require_not_authorized(label, wp.get("implementation_authorization"), issues)

    if packages is not None and len(package_ids) != 15:
        issues.append(f"adaptation-work-packages: expected exactly 15 work packages, found {len(package_ids)}")

    # every HIGH-severity gap must be analysed by the route that owns it
    for gid in sorted(prioritized_high):
        if gid not in high_gaps_seen:
            issues.append(f"gap {gid!r}: a HIGH-severity gap must appear in its route's high_risk_gap_ids")

    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the official-template adaptation planning records."
    )
    parser.add_argument("--planning-dir", default=str(DEFAULT_PLANNING_DIR))
    parser.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR))
    parser.add_argument("--source-registry", default=str(DEFAULT_SOURCE_REGISTRY))
    parser.add_argument("--mapping-registry", default=str(DEFAULT_MAPPING_REGISTRY))
    args = parser.parse_args(argv)

    issues = validate_plan(Path(args.planning_dir), Path(args.analysis_dir),
                           Path(args.source_registry), Path(args.mapping_registry))

    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        print(f"FAIL template adaptation planning records: {len(issues)} issue(s)")
        return 1

    print("OK   template adaptation planning records are internally consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
