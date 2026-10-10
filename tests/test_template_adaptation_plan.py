# File: tests/test_template_adaptation_plan.py
# Purpose: Positive and negative tests for the offline official-template
#          adaptation planning validator.
# Encoding: UTF-8
"""Adaptation planning validation tests.

Pure Python (no Qt), fictional fixtures only, no network access, no repository
mutation. The real planning records are used as the positive control; every
negative case mutates a copy in a temporary directory.

The tests assert two things for every malformed input: the validator completes
**without raising**, and it returns a relevant issue.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import check_template_adaptation_plan as ctap

REPO_ROOT = Path(__file__).resolve().parents[1]
GOV = REPO_ROOT / "docs" / "legal-template-governance"
PLANNING_DIR = GOV / "official-adaptation-planning"
ANALYSIS_DIR = GOV / "official-gap-analysis"
SOURCE_REGISTRY = GOV / "source-registry.json"
MAPPING_REGISTRY = GOV / "case-template-mapping.json"

FILES = ctap.PLANNING_FILES


def _records():
    return {key: json.loads((PLANNING_DIR / name).read_text(encoding="utf-8"))
            for key, name in FILES.items()}


def _write(tmp_path, records):
    target = tmp_path / "planning"
    target.mkdir(parents=True, exist_ok=True)
    for key, name in FILES.items():
        (target / name).write_text(json.dumps(records[key], ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return target


def _issues(tmp_path, records):
    return ctap.validate_plan(_write(tmp_path, records), ANALYSIS_DIR,
                              SOURCE_REGISTRY, MAPPING_REGISTRY)


def _mutated(tmp_path, mutate):
    records = _records()
    mutate(records)
    return _issues(tmp_path, records)


def _mutated_safe(tmp_path, mutate):
    """Run the validator on a mutated fixture, failing if it raises."""
    records = _records()
    mutate(records)
    target = _write(tmp_path, records)
    try:
        return ctap.validate_plan(target, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    except Exception as exc:  # noqa: BLE001 - the point of the test is no raise
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")


def _find_route(records, route_id):
    for r in records["readiness"]["routes"]:
        if r["route_id"] == route_id:
            return r
    raise KeyError(route_id)


def _find_gap(records, gap_id):
    for g in records["prioritization"]["gaps"]:
        if g["gap_id"] == gap_id:
            return g
    raise KeyError(gap_id)


def _find_wp(records, work_package_id):
    for w in records["packages"]["work_packages"]:
        if w["work_package_id"] == work_package_id:
            return w
    raise KeyError(work_package_id)


def _frozen_gap_ids():
    data = json.loads((ANALYSIS_DIR / "gap-register.json").read_text(encoding="utf-8"))
    return {g["gap_id"] for g in data["gaps"]}


# --- positive controls ------------------------------------------------------

def test_planning_records_are_consistent():
    assert ctap.validate_plan(PLANNING_DIR, ANALYSIS_DIR, SOURCE_REGISTRY,
                              MAPPING_REGISTRY) == []
    assert ctap.main(["--planning-dir", str(PLANNING_DIR),
                      "--analysis-dir", str(ANALYSIS_DIR),
                      "--source-registry", str(SOURCE_REGISTRY),
                      "--mapping-registry", str(MAPPING_REGISTRY)]) == 0


def test_validator_is_deterministic():
    first = ctap.validate_plan(PLANNING_DIR, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    second = ctap.validate_plan(PLANNING_DIR, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    assert first == second == []


def test_exactly_fifteen_routes_are_assessed():
    routes = _records()["readiness"]["routes"]
    assert len(routes) == 15
    combos = {(r["case_type"], r["document_type"]) for r in routes}
    assert len(combos) == 15
    assert {c for c, _ in combos} == set(ctap.CASE_TYPES)
    assert {d for _, d in combos} == set(ctap.DOCUMENT_TYPES)


def test_all_frozen_gaps_are_prioritized_exactly_once():
    records = _records()
    prioritized = [g["gap_id"] for g in records["prioritization"]["gaps"]]
    assert len(prioritized) == 131
    assert len(set(prioritized)) == 131
    assert set(prioritized) == _frozen_gap_ids()


def test_high_severity_gaps_are_p0_and_not_deferrable():
    records = _records()
    high = [g for g in records["prioritization"]["gaps"] if g["frozen_severity"] == "HIGH"]
    assert len(high) == 4
    assert {g["gap_id"] for g in high} == {
        "GAP-LOAN-INTEREST-BASIS", "GAP-LOAN-REPAYMENT-STATUS",
        "GAP-LABOR-ARBITRATION", "GAP-DIVORCE-COMBINED-SCOPE",
    }
    for g in high:
        assert g["planning_priority"] == "P0"
        assert g["can_be_deferred"] is False
        assert g["review_dependencies"]


def test_every_route_and_work_package_is_unauthorized():
    records = _records()
    for r in records["readiness"]["routes"]:
        assert r["implementation_authorization"] == "NOT_AUTHORIZED"
    for w in records["packages"]["work_packages"]:
        assert w["implementation_authorization"] == "NOT_AUTHORIZED"
    assert len(records["packages"]["work_packages"]) == 15


def test_no_planning_record_claims_an_approval():
    records = _records()
    for r in records["readiness"]["routes"]:
        assert r["legal_content_review_state"] == "NOT_REQUESTED"
        assert r["rights_review_state"] == "NOT_REVIEWED"
        assert r["source_verification_state"] != "APPROVED_FOR_ADAPTATION"
        assert r["mapping_review_state"] != "APPROVED"
    for g in records["prioritization"]["gaps"]:
        assert g["planning_priority"] in ctap.PLANNING_PRIORITIES


def test_work_packages_reference_their_own_route():
    records = _records()
    frozen_routes = json.loads(
        (ANALYSIS_DIR / "document-route-assessment.json").read_text(encoding="utf-8"))["routes"]
    by_combo = {(r["case_type"], r["document_type"]): r["route_id"] for r in frozen_routes}
    for w in records["packages"]["work_packages"]:
        assert w["linked_route_id"] == by_combo[(w["case_type"], w["document_type"])]


def test_validator_does_not_modify_the_records(tmp_path):
    target = _write(tmp_path, _records())
    before = {name: (target / name).read_bytes() for name in FILES.values()}
    ctap.validate_plan(target, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    after = {name: (target / name).read_bytes() for name in FILES.values()}
    assert before == after


def test_frozen_analysis_is_not_modified_by_validation(tmp_path):
    analysis_before = {p.name: p.read_bytes() for p in sorted(ANALYSIS_DIR.glob("*.json"))}
    _issues(tmp_path, _records())
    analysis_after = {p.name: p.read_bytes() for p in sorted(ANALYSIS_DIR.glob("*.json"))}
    assert analysis_before == analysis_after


# --- negative controls: coverage and identity ------------------------------

def test_missing_route_is_rejected(tmp_path):
    def mutate(records):
        records["readiness"]["routes"].pop()
    issues = _mutated(tmp_path, mutate)
    assert any("15 route records" in issue for issue in issues)


def test_duplicate_route_is_rejected(tmp_path):
    def mutate(records):
        routes = records["readiness"]["routes"]
        routes.append(copy.deepcopy(routes[0]))
    issues = _mutated(tmp_path, mutate)
    assert any("duplicate route_id" in issue for issue in issues)


def test_unknown_route_id_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["route_id"] = "route-ghost-complaint"
    issues = _mutated(tmp_path, mutate)
    assert any("does not resolve in the frozen route inventory" in issue for issue in issues)


def test_route_case_document_mismatch_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["document_type"] = "evidence_list"
    issues = _mutated(tmp_path, mutate)
    assert any("does not match the frozen route" in issue for issue in issues)


def test_unknown_gap_in_prioritization_is_rejected(tmp_path):
    def mutate(records):
        g = copy.deepcopy(records["prioritization"]["gaps"][0])
        g["gap_id"] = "GAP-FABRICATED"
        records["prioritization"]["gaps"].append(g)
    issues = _mutated(tmp_path, mutate)
    assert any("is not a frozen gap" in issue for issue in issues)


def test_gap_with_wrong_case_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["case_type"] = "divorce"
    issues = _mutated(tmp_path, mutate)
    assert any("does not match the frozen gap record" in issue for issue in issues)


def test_wrong_document_type_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["document_type"] = "evidence_list"
    issues = _mutated(tmp_path, mutate)
    assert any("does not match the frozen gap record" in issue for issue in issues)


def test_duplicate_prioritized_gap_is_rejected(tmp_path):
    def mutate(records):
        gaps = records["prioritization"]["gaps"]
        gaps.append(copy.deepcopy(gaps[0]))
    issues = _mutated(tmp_path, mutate)
    assert any("duplicate prioritized gap_id" in issue for issue in issues)


def test_dropped_high_severity_gap_is_rejected(tmp_path):
    def mutate(records):
        records["prioritization"]["gaps"] = [
            g for g in records["prioritization"]["gaps"]
            if g["gap_id"] != "GAP-LOAN-INTEREST-BASIS"]
    issues = _mutated(tmp_path, mutate)
    assert any("are not prioritized" in issue for issue in issues)


def test_high_severity_gap_must_be_p0(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["planning_priority"] = "P2"
    issues = _mutated(tmp_path, mutate)
    assert any("must be planning_priority P0" in issue for issue in issues)


def test_high_severity_gap_must_not_be_deferrable(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LABOR-ARBITRATION")["can_be_deferred"] = True
    issues = _mutated(tmp_path, mutate)
    assert any("must not be deferrable" in issue for issue in issues)


def test_high_severity_gap_must_record_review_dependencies(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-DIVORCE-COMBINED-SCOPE")["review_dependencies"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("review_dependencies" in issue for issue in issues)


def test_missing_blocking_condition_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["blocking_conditions"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("blocking_conditions" in issue for issue in issues)


def test_review_required_cannot_be_false(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["review_required"] = False
    issues = _mutated(tmp_path, mutate)
    assert any("review_required must not be false" in issue for issue in issues)


# --- negative controls: work packages --------------------------------------

def test_unknown_crosswalk_in_work_package_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["linked_crosswalk_ids"] = ["cw-9999-ghost"]
    issues = _mutated(tmp_path, mutate)
    assert any("linked crosswalk" in issue and "does not resolve" in issue for issue in issues)


def test_unknown_source_in_work_package_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["source_ids"] = ["spc-does-not-exist"]
    issues = _mutated(tmp_path, mutate)
    assert any("does not resolve in the source registry" in issue for issue in issues)


def test_unknown_gap_in_work_package_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["linked_gap_ids"] = ["GAP-FABRICATED"]
    issues = _mutated(tmp_path, mutate)
    assert any("linked gap" in issue and "does not resolve" in issue for issue in issues)


def test_gap_from_another_case_in_work_package_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["linked_gap_ids"] = ["GAP-LABOR-ARBITRATION"]
    issues = _mutated(tmp_path, mutate)
    assert any("belongs to a different case/document" in issue for issue in issues)


def test_wrong_route_in_work_package_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["linked_route_id"] = "route-loan-evidence-list"
    issues = _mutated(tmp_path, mutate)
    assert any("is not the route for" in issue for issue in issues)


def test_missing_work_package_review_dependency_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["review_dependencies"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("review_dependencies" in issue for issue in issues)


def test_unknown_review_dependency_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["review_dependencies"] = ["VIBES_REVIEW"]
    issues = _mutated(tmp_path, mutate)
    assert any("unknown review dependency" in issue for issue in issues)


def test_unknown_implementation_stage_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["implementation_sequence"] = ["SHIP_IT"]
    issues = _mutated(tmp_path, mutate)
    assert any("unknown implementation stage" in issue for issue in issues)


def test_dropped_work_package_is_rejected(tmp_path):
    def mutate(records):
        records["packages"]["work_packages"].pop()
    issues = _mutated(tmp_path, mutate)
    assert any("15 work packages" in issue for issue in issues)


# --- negative controls: false authorization --------------------------------

def test_false_route_authorization_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["implementation_authorization"] = \
            "AUTHORIZED"
    issues = _mutated(tmp_path, mutate)
    assert any("only 'NOT_AUTHORIZED' is valid" in issue for issue in issues)


def test_false_work_package_authorization_is_rejected(tmp_path):
    def mutate(records):
        _find_wp(records, "wp-loan-complaint")["implementation_authorization"] = \
            "APPROVED_FOR_IMPLEMENTATION"
    issues = _mutated(tmp_path, mutate)
    assert any("only 'NOT_AUTHORIZED' is valid" in issue for issue in issues)


def test_missing_authorization_fails_closed(tmp_path):
    def mutate(records):
        del _find_route(records, "route-loan-civil-complaint")["implementation_authorization"]
    issues = _mutated(tmp_path, mutate)
    assert any("missing authorization fails closed" in issue for issue in issues)


def test_false_approved_source_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["source_verification_state"] = \
            "APPROVED_FOR_ADAPTATION"
    issues = _mutated(tmp_path, mutate)
    assert any("requires source_approval_evidence" in issue for issue in issues)


def test_source_file_verified_cannot_back_an_approved_mapping(tmp_path):
    def mutate(records):
        r = _find_route(records, "route-loan-civil-complaint")
        r["source_verification_state"] = "SOURCE_FILE_VERIFIED"
        r["mapping_review_state"] = "APPROVED"
    issues = _mutated(tmp_path, mutate)
    assert any("cannot back an APPROVED mapping" in issue for issue in issues)


def test_false_approved_mapping_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["mapping_review_state"] = "APPROVED"
    issues = _mutated(tmp_path, mutate)
    assert any("APPROVED" in issue for issue in issues)


def test_rights_gate_cannot_be_cleared_without_evidence(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["rights_review_state"] = "REVIEWED"
    issues = _mutated(tmp_path, mutate)
    assert any("requires rights_review_evidence" in issue for issue in issues)


def test_completed_legal_review_requires_evidence(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["legal_content_review_state"] = \
            "COMPLETED"
    issues = _mutated(tmp_path, mutate)
    assert any("requires legal_content_review_evidence" in issue for issue in issues)


def test_approval_claim_with_evidence_still_requires_a_valid_state(tmp_path):
    def mutate(records):
        r = _find_route(records, "route-loan-civil-complaint")
        r["rights_review_state"] = "CLEARED"
        r["rights_review_evidence"] = "reviewer said so"
    issues = _mutated(tmp_path, mutate)
    assert any("invalid rights_review_state" in issue for issue in issues)


# --- negative controls: type safety ----------------------------------------

ENUM_TARGETS = [
    pytest.param(("readiness", "route-loan-civil-complaint"), "case_type", id="route.case_type"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "document_type", id="route.document_type"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "readiness_classification",
                 id="route.readiness_classification"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "engineering_readiness",
                 id="route.engineering_readiness"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "source_verification_state",
                 id="route.source_verification_state"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "mapping_review_state",
                 id="route.mapping_review_state"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "legal_content_review_state",
                 id="route.legal_content_review_state"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "rights_review_state",
                 id="route.rights_review_state"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "procedural_applicability_state",
                 id="route.procedural_applicability_state"),
    pytest.param(("prioritization", "GAP-LOAN-INTEREST-BASIS"), "planning_priority",
                 id="gap.planning_priority"),
    pytest.param(("packages", "wp-loan-complaint"), "case_type", id="wp.case_type"),
    pytest.param(("packages", "wp-loan-complaint"), "document_type", id="wp.document_type"),
]

BAD_ENUM_VALUES = [
    pytest.param([], "empty-array", id="empty-array"),
    pytest.param({}, "empty-object", id="empty-object"),
    pytest.param(["loan"], "array-of-string", id="array-of-string"),
    pytest.param({"value": "loan"}, "object-of-string", id="object-of-string"),
    pytest.param(123, "number", id="number"),
    pytest.param(True, "true", id="true"),
    pytest.param(None, "null", id="null"),
    pytest.param("", "empty-string", id="empty-string"),
    pytest.param("UNKNOWN_ENUM_VALUE", "unknown-string", id="unknown-string"),
]


def _target(records, spec):
    kind, ident = spec
    if kind == "readiness":
        return _find_route(records, ident)
    if kind == "prioritization":
        return _find_gap(records, ident)
    if kind == "packages":
        return _find_wp(records, ident)
    raise KeyError(spec)


@pytest.mark.parametrize("spec,field", ENUM_TARGETS)
@pytest.mark.parametrize("value,label", BAD_ENUM_VALUES)
def test_malformed_enum_value_is_rejected_without_exception(tmp_path, spec, field, value, label):
    def mutate(records):
        _target(records, spec)[field] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert issues, (spec, field, value)
    assert any(field in issue for issue in issues), (spec, field, value, issues)


NESTED_IDENTIFIER_CASES = [
    pytest.param(("readiness", "route-loan-civil-complaint"), "linked_gap_ids",
                 [["GAP-LOAN-INTEREST-BASIS"]], id="route-linked_gap_ids-nested-array"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "source_ids",
                 [["spc-2025-notice-pdf"]], id="route-source_ids-nested-array"),
    pytest.param(("readiness", "route-loan-civil-complaint"), "blocking_conditions",
                 "not-a-list", id="route-blocking_conditions-string"),
    pytest.param(("prioritization", "GAP-LOAN-INTEREST-BASIS"), "review_dependencies",
                 {"a": 1}, id="gap-review_dependencies-object"),
    pytest.param(("prioritization", "GAP-LOAN-INTEREST-BASIS"), "risk_dimensions",
                 ["not", "an", "object"], id="gap-risk_dimensions-array"),
    pytest.param(("packages", "wp-loan-complaint"), "linked_crosswalk_ids",
                 {"a": 1}, id="wp-linked_crosswalk_ids-object"),
    pytest.param(("packages", "wp-loan-complaint"), "linked_gap_ids",
                 [["GAP-LOAN-INTEREST-BASIS"]], id="wp-linked_gap_ids-nested-array"),
    pytest.param(("packages", "wp-loan-complaint"), "review_dependencies",
                 "LEGAL_CONTENT_REVIEW", id="wp-review_dependencies-string"),
    pytest.param(("packages", "wp-loan-complaint"), "implementation_sequence",
                 {"SOURCE_AND_LEGAL_REVIEW": True}, id="wp-implementation_sequence-object"),
]


@pytest.mark.parametrize("spec,field,value", NESTED_IDENTIFIER_CASES)
def test_malformed_relationship_is_rejected_without_exception(tmp_path, spec, field, value):
    def mutate(records):
        _target(records, spec)[field] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert issues, (spec, field, value)
    assert any(field in issue for issue in issues), (spec, field, value, issues)


@pytest.mark.parametrize("value,label", [
    pytest.param([], "empty-array", id="empty-array"),
    pytest.param([1], "nonempty-array", id="nonempty-array"),
    pytest.param("high", "string", id="string"),
    pytest.param(True, "boolean", id="boolean"),
])
def test_malformed_risk_dimension_value_is_rejected(tmp_path, value, label):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["risk_dimensions"]["factual_integrity_impact"] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any("factual_integrity_impact" in issue for issue in issues), issues


def test_unknown_risk_dimension_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["risk_dimensions"]["vibes"] = 1
    issues = _mutated_safe(tmp_path, mutate)
    assert any("unknown risk dimension" in issue for issue in issues)


def test_malformed_priority_score_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-LOAN-INTEREST-BASIS")["priority_score"] = "high"
    issues = _mutated_safe(tmp_path, mutate)
    assert any("priority_score must be an integer" in issue for issue in issues)


def test_malformed_json_is_rejected(tmp_path):
    target = _write(tmp_path, _records())
    (target / FILES["readiness"]).write_text("{ not json ", encoding="utf-8")
    issues = ctap.validate_plan(target, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    assert any("invalid JSON" in issue for issue in issues)


def test_missing_planning_file_is_rejected(tmp_path):
    target = _write(tmp_path, _records())
    (target / FILES["packages"]).unlink()
    issues = ctap.validate_plan(target, ANALYSIS_DIR, SOURCE_REGISTRY, MAPPING_REGISTRY)
    assert any("file not found" in issue for issue in issues)


def test_record_block_must_be_a_list(tmp_path):
    def mutate(records):
        records["readiness"]["routes"] = 5
    issues = _mutated_safe(tmp_path, mutate)
    assert any("'routes' must be a list" in issue for issue in issues)


def test_non_object_record_is_rejected(tmp_path):
    def mutate(records):
        records["prioritization"]["gaps"].append("not-an-object")
    issues = _mutated_safe(tmp_path, mutate)
    assert any("record must be a JSON object" in issue for issue in issues)


# --- CLI integration --------------------------------------------------------

def test_cli_rejects_invalid_planning_records(tmp_path):
    records = _records()
    _find_route(records, "route-loan-civil-complaint")["implementation_authorization"] = "AUTHORIZED"
    target = _write(tmp_path, records)
    result = subprocess.run(
        [sys.executable, "tools/check_template_adaptation_plan.py",
         "--planning-dir", str(target), "--analysis-dir", str(ANALYSIS_DIR),
         "--source-registry", str(SOURCE_REGISTRY),
         "--mapping-registry", str(MAPPING_REGISTRY)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "Traceback" not in result.stdout and "Traceback" not in result.stderr


def test_cli_rejects_malformed_enum_without_traceback(tmp_path):
    records = _records()
    records["readiness"]["routes"][0]["case_type"] = ["loan"]
    target = _write(tmp_path, records)
    result = subprocess.run(
        [sys.executable, "tools/check_template_adaptation_plan.py",
         "--planning-dir", str(target), "--analysis-dir", str(ANALYSIS_DIR),
         "--source-registry", str(SOURCE_REGISTRY),
         "--mapping-registry", str(MAPPING_REGISTRY)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "case_type" in result.stdout
    assert "Traceback" not in result.stdout and "Traceback" not in result.stderr


def test_cli_accepts_the_real_records():
    result = subprocess.run(
        [sys.executable, "tools/check_template_adaptation_plan.py"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "OK   template adaptation planning records are internally consistent" in result.stdout
