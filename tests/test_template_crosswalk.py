# File: tests/test_template_crosswalk.py
# Purpose: Positive and negative tests for the offline official-template
#          crosswalk / gap-analysis validator.
# Encoding: UTF-8
"""Crosswalk record validation tests.

Pure Python (no Qt), fictional fixtures only, no network access, no repository
mutation. The real records under
``docs/legal-template-governance/official-gap-analysis/`` are used as the
positive control; every negative case mutates a copy in a temporary directory.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import check_template_crosswalk as ctc

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = REPO_ROOT / "docs" / "legal-template-governance" / "official-gap-analysis"
SOURCE_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"

FILES = ctc.ANALYSIS_FILES


def _records():
    return {key: json.loads((ANALYSIS_DIR / name).read_text(encoding="utf-8"))
            for key, name in FILES.items()}


def _write(tmp_path, records):
    target = tmp_path / "analysis"
    target.mkdir(parents=True, exist_ok=True)
    for key, name in FILES.items():
        (target / name).write_text(json.dumps(records[key], ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _issues(tmp_path, records):
    return ctc.validate_analysis(_write(tmp_path, records), SOURCE_REGISTRY)


def _mutated(tmp_path, mutate):
    records = _records()
    mutate(records)
    return _issues(tmp_path, records)


# --- positive controls ------------------------------------------------------


def test_repository_crosswalk_records_are_consistent():
    assert ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY) == []
    assert ctc.main(["--analysis-dir", str(ANALYSIS_DIR),
                     "--source-registry", str(SOURCE_REGISTRY)]) == 0


def test_all_five_case_types_represented():
    records = _records()
    assert {e["case_type"] for e in records["elements"]["elements"]} == set(ctc.CASE_TYPES)
    assert {c["case_type"] for c in records["crosswalk"]["crosswalks"]} == set(ctc.CASE_TYPES)


def test_all_three_document_types_represented():
    records = _records()
    assert {r["document_type"] for r in records["routes"]["routes"]} == set(ctc.DOCUMENT_TYPES)


def test_exactly_fifteen_unique_routes():
    routes = _records()["routes"]["routes"]
    combos = {(r["case_type"], r["document_type"]) for r in routes}
    assert len(combos) == 15
    assert len(routes) == 15


def test_every_official_element_has_a_crosswalk_record():
    records = _records()
    element_ids = {e["element_id"] for e in records["elements"]["elements"]}
    covered = {c["official_element_id"] for c in records["crosswalk"]["crosswalks"]
               if c["official_element_id"]}
    assert element_ids - covered == set()


def test_honest_uncertainty_is_accepted(tmp_path):
    """UNVERIFIED / SECTION_ONLY / NO_COUNTERPART outcomes must remain valid."""
    records = _records()
    records["crosswalk"]["crosswalks"][0]["coverage_status"] = "SOURCE_UNVERIFIED"
    assert _issues(tmp_path, records) == []


def test_validator_is_deterministic():
    first = ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY)
    second = ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY)
    assert first == second == []


# --- negative controls ------------------------------------------------------


def test_malformed_json_is_rejected(tmp_path):
    target = _write(tmp_path, _records())
    (target / FILES["crosswalk"]).write_text("{ not json ", encoding="utf-8")
    issues = ctc.validate_analysis(target, SOURCE_REGISTRY)
    assert any("invalid JSON" in issue for issue in issues)


def test_duplicate_official_element_id_is_rejected(tmp_path):
    def mutate(records):
        elements = records["elements"]["elements"]
        elements.append(copy.deepcopy(elements[0]))
    issues = _mutated(tmp_path, mutate)
    assert any("duplicate element_id" in issue for issue in issues)


def test_duplicate_application_field_id_is_rejected(tmp_path):
    def mutate(records):
        fields = records["fields"]["fields"]
        fields.append(copy.deepcopy(fields[0]))
    issues = _mutated(tmp_path, mutate)
    assert any("duplicate field_id" in issue for issue in issues)


def test_duplicate_route_id_is_rejected(tmp_path):
    def mutate(records):
        routes = records["routes"]["routes"]
        routes.append(copy.deepcopy(routes[0]))
    issues = _mutated(tmp_path, mutate)
    assert any("duplicate route_id" in issue for issue in issues)


def test_missing_route_is_rejected(tmp_path):
    def mutate(records):
        records["routes"]["routes"].pop()
    issues = _mutated(tmp_path, mutate)
    assert any("15" in issue and "route" in issue.lower() for issue in issues)


def test_unknown_case_type_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["case_type"] = "not-a-case"
    issues = _mutated(tmp_path, mutate)
    assert any("unknown case_type" in issue for issue in issues)


def test_unknown_document_type_is_rejected(tmp_path):
    def mutate(records):
        records["routes"]["routes"][0]["document_type"] = "not-a-document"
    issues = _mutated(tmp_path, mutate)
    assert any("unknown document_type" in issue for issue in issues)


def test_unknown_source_id_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["source_id"] = "does-not-exist"
    issues = _mutated(tmp_path, mutate)
    assert any("does not resolve in the source registry" in issue for issue in issues)


def test_broken_element_reference_is_rejected(tmp_path):
    def mutate(records):
        records["crosswalk"]["crosswalks"][0]["official_element_id"] = "ghost.element"
    issues = _mutated(tmp_path, mutate)
    assert any("official_element_id" in issue and "does not resolve" in issue for issue in issues)


def test_broken_application_field_reference_is_rejected(tmp_path):
    def mutate(records):
        records["crosswalk"]["crosswalks"][0]["application_field_ids"] = ["ghost.field"]
    issues = _mutated(tmp_path, mutate)
    assert any("does not resolve" in issue and "ghost.field" in issue for issue in issues)


def test_broken_gap_reference_is_rejected(tmp_path):
    def mutate(records):
        records["crosswalk"]["crosswalks"][0]["gap_ids"] = ["GAP-DOES-NOT-EXIST"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-DOES-NOT-EXIST" in issue for issue in issues)


def test_invalid_coverage_status_is_rejected(tmp_path):
    def mutate(records):
        records["crosswalk"]["crosswalks"][0]["coverage_status"] = "PROBABLY_FINE"
    issues = _mutated(tmp_path, mutate)
    assert any("invalid coverage_status" in issue for issue in issues)


def test_invalid_approval_status_is_rejected(tmp_path):
    def mutate(records):
        records["routes"]["routes"][0]["approval_status"] = "MAYBE"
    issues = _mutated(tmp_path, mutate)
    assert any("invalid approval_status" in issue for issue in issues)


def test_false_approved_route_is_rejected(tmp_path):
    def mutate(records):
        records["routes"]["routes"][0]["approval_status"] = "APPROVED"
    issues = _mutated(tmp_path, mutate)
    assert any("must never be APPROVED" in issue for issue in issues)


def test_missing_source_evidence_for_verified_claim_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["verification_evidence"] = ""
    issues = _mutated(tmp_path, mutate)
    assert any("verification_evidence is required" in issue for issue in issues)


def test_invalid_pdf_page_number_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["pdf_page_start"] = "134"
    issues = _mutated(tmp_path, mutate)
    assert any("must be integers" in issue for issue in issues)


def test_out_of_range_page_number_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["pdf_page_end"] = 99999
    issues = _mutated(tmp_path, mutate)
    assert any("exceeds the observed page count" in issue for issue in issues)


def test_inconsistent_source_hash_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["source_sha256"] = "0" * 64
    issues = _mutated(tmp_path, mutate)
    assert any("does not match the analyzed ledger hash" in issue for issue in issues)


def test_malformed_source_hash_is_rejected(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["source_sha256"] = "not-a-hash"
    issues = _mutated(tmp_path, mutate)
    assert any("64-character lowercase hex" in issue for issue in issues)


def test_failed_hash_match_blocks_the_analysis(tmp_path):
    def mutate(records):
        records["ledger"]["registry_hash_comparison"]["SOURCE_HASH_MATCH"] = "FAIL"
    issues = _mutated(tmp_path, mutate)
    assert any("SOURCE_HASH_MATCH is FAIL" in issue for issue in issues)


def test_missing_unresolved_review_classification_is_rejected(tmp_path):
    def mutate(records):
        records["gaps"]["gaps"][0]["gap_category"] = "NOT_A_CATEGORY"
    issues = _mutated(tmp_path, mutate)
    assert any("invalid gap_category" in issue for issue in issues)


def test_missing_gap_field_is_rejected(tmp_path):
    def mutate(records):
        del records["gaps"]["gaps"][0]["potential_remediation"]
    issues = _mutated(tmp_path, mutate)
    assert any("potential_remediation" in issue for issue in issues)


def test_malformed_non_string_metadata_is_rejected(tmp_path):
    def mutate(records):
        records["crosswalk"]["crosswalks"][0]["application_field_ids"] = [["nested"]]
    issues = _mutated(tmp_path, mutate)
    assert any("must be strings" in issue for issue in issues)


def test_unhashable_enum_value_does_not_crash(tmp_path):
    """Type safety: a list value must be reported, not raise."""
    def mutate(records):
        records["elements"]["elements"][0]["element_kind"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("element_kind" in issue for issue in issues)


def test_missing_analysis_file_is_rejected(tmp_path):
    target = _write(tmp_path, _records())
    (target / FILES["routes"]).unlink()
    issues = ctc.validate_analysis(target, SOURCE_REGISTRY)
    assert any("file not found" in issue for issue in issues)


def test_null_official_element_requires_application_only_status(tmp_path):
    def mutate(records):
        for c in records["crosswalk"]["crosswalks"]:
            if c["official_element_id"] is None:
                c["coverage_status"] = "DIRECT_MATCH"
                break
    issues = _mutated(tmp_path, mutate)
    assert any("APPLICATION_ONLY_ELEMENT" in issue for issue in issues)


def test_cli_rejects_inconsistent_records(tmp_path):
    records = _records()
    records["crosswalk"]["crosswalks"][0]["coverage_status"] = "NOPE"
    target = _write(tmp_path, records)
    result = subprocess.run(
        [sys.executable, "tools/check_template_crosswalk.py",
         "--analysis-dir", str(target), "--source-registry", str(SOURCE_REGISTRY)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "Traceback" not in result.stdout and "Traceback" not in result.stderr


def test_cli_accepts_the_real_records():
    result = subprocess.run(
        [sys.executable, "tools/check_template_crosswalk.py"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "OK   template crosswalk records are internally consistent" in result.stdout


def test_validator_does_not_modify_the_records(tmp_path):
    target = _write(tmp_path, _records())
    before = {name: (target / name).read_bytes() for name in FILES.values()}
    ctc.validate_analysis(target, SOURCE_REGISTRY)
    after = {name: (target / name).read_bytes() for name in FILES.values()}
    assert before == after


# ===========================================================================
# C1 — cross-case application-field integrity
# ===========================================================================

FROZEN_REVISION = "639179933c51f111ea43060157e897fa0a1e4d30"
SOURCE_HASH = "07fc626a7b703beb27b1dab9b5d7aa47b6dc58b4165048813e02663f9fd11b88"


def _find_crosswalk(records, crosswalk_id):
    for c in records["crosswalk"]["crosswalks"]:
        if c["crosswalk_id"] == crosswalk_id:
            return c
    raise KeyError(crosswalk_id)


def _find_gap(records, gap_id):
    for g in records["gaps"]["gaps"]:
        if g["gap_id"] == gap_id:
            return g
    raise KeyError(gap_id)


def _find_route(records, route_id):
    for r in records["routes"]["routes"]:
        if r["route_id"] == route_id:
            return r
    raise KeyError(route_id)


def _crosswalk_code_evidence(*clauses):
    return "revision " + FROZEN_REVISION + "; " + "; ".join(clauses)


def _source_evidence(page):
    return f"spc-2025-notice-pdf p{page} sha256:{SOURCE_HASH}"


@pytest.mark.parametrize("crosswalk_id, foreign_field", [
    ("cw-0027-loan", "labor.is_no_contract"),        # N01 / C1-T01
    ("cw-0069-contract", "labor.is_no_contract"),    # N02 / C1-T02
    ("cw-0105-property", "labor.is_no_contract"),    # N03 / C1-T03
    ("cw-0078-contract", "property.demand_record"),  # N04 / C1-T04
])
def test_cross_case_application_field_reference_is_rejected(tmp_path, crosswalk_id, foreign_field):
    def mutate(records):
        _find_crosswalk(records, crosswalk_id)["application_field_ids"] = [foreign_field]
    issues = _mutated(tmp_path, mutate)
    assert any("belongs to case_type" in issue and foreign_field in issue for issue in issues)


def test_official_element_from_another_case_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["official_element_id"] = \
            "contract.party.plaintiff.name"
    issues = _mutated(tmp_path, mutate)
    assert any("belongs to case_type 'contract'" in issue for issue in issues)


def test_legitimate_shared_field_reference_is_accepted(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["application_field_ids"] = \
            ["shared.party.plaintiff.name"]
    assert _mutated(tmp_path, mutate) == []


def test_legitimate_same_case_field_reference_is_accepted(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0022-loan")["application_field_ids"] = \
            ["loan.principal", "loan.loan_date"]
    assert _mutated(tmp_path, mutate) == []


def test_unknown_application_field_in_a_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["application_field_ids"] = ["ghost.field"]
    issues = _mutated(tmp_path, mutate)
    assert any("ghost.field" in issue and "does not resolve" in issue for issue in issues)


def test_every_crosswalk_record_passes_ownership_validation():
    records = _records()
    field_owner = {f["field_id"]: f["case_type_or_shared"] for f in records["fields"]["fields"]}
    element_case = {e["element_id"]: e["case_type"] for e in records["elements"]["elements"]}
    crosswalks = records["crosswalk"]["crosswalks"]
    assert len(crosswalks) == 199
    for c in crosswalks:
        if c["official_element_id"]:
            assert element_case[c["official_element_id"]] == c["case_type"]
        for fid in c["application_field_ids"]:
            assert field_owner[fid] in ("shared", c["case_type"])


# ===========================================================================
# C2 — semantic match reassessment
# ===========================================================================

def test_contract_demand_cannot_be_a_property_direct_match(tmp_path):
    def mutate(records):
        c = _find_crosswalk(records, "cw-0078-contract")
        c["coverage_status"] = "DIRECT_MATCH"
        c["application_field_ids"] = ["property.demand_record"]
        c["match_mechanism"] = "USER_INPUT_FIELD"
    issues = _mutated(tmp_path, mutate)
    assert any("belongs to case_type 'property'" in issue for issue in issues)


def test_valid_same_case_direct_match_remains_valid(tmp_path):
    def mutate(records):
        c = _find_crosswalk(records, "cw-0004-loan")
        assert c["coverage_status"] == "DIRECT_MATCH"
        c["application_field_ids"] = ["shared.party.plaintiff.address"]
    assert _mutated(tmp_path, mutate) == []


def test_empty_field_direct_match_without_static_evidence_is_rejected(tmp_path):
    def mutate(records):
        c = _find_crosswalk(records, "cw-0019-loan")
        c["match_mechanism"] = "USER_INPUT_FIELD"
    issues = _mutated(tmp_path, mutate)
    assert any("requires match_mechanism STATIC_RENDERING" in issue for issue in issues)


def test_static_direct_match_without_rendering_evidence_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0020-loan")["rendering_evidence"] = ""
    issues = _mutated(tmp_path, mutate)
    assert any("requires rendering_evidence" in issue for issue in issues)


def test_verified_static_signature_and_date_placeholders_are_accepted():
    records = _records()
    for cid in ("cw-0019-loan", "cw-0020-loan", "cw-0059-contract",
                "cw-0100-property", "cw-0134-labor", "cw-0167-divorce"):
        c = _find_crosswalk(records, cid)
        assert c["coverage_status"] == "DIRECT_MATCH"
        assert c["match_mechanism"] == "STATIC_RENDERING"
        assert c["application_field_ids"] == []
        assert "add_footer()" in c["rendering_evidence"]


def test_invalid_match_mechanism_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["match_mechanism"] = "PROBABLY_FINE"
    issues = _mutated(tmp_path, mutate)
    assert any("invalid match_mechanism" in issue for issue in issues)


@pytest.mark.parametrize("crosswalk_id", [
    "cw-0027-loan", "cw-0069-contract", "cw-0078-contract", "cw-0105-property",
])
def test_corrected_cross_case_defects_are_resolved(crosswalk_id):
    records = _records()
    field_owner = {f["field_id"]: f["case_type_or_shared"] for f in records["fields"]["fields"]}
    c = _find_crosswalk(records, crosswalk_id)
    for fid in c["application_field_ids"]:
        assert field_owner[fid] in ("shared", c["case_type"])
    assert c["gap_ids"], "a corrected mismatch must remain traceable to a gap"


# ===========================================================================
# C3 — crosswalk-to-gap traceability
# ===========================================================================

@pytest.mark.parametrize("crosswalk_id, status", [
    ("cw-0022-loan", "PARTIAL_MATCH"),
    ("cw-0109-property", "SEMANTIC_MISMATCH"),
    ("cw-0013-loan", "CONDITIONAL_MISMATCH"),
    ("cw-0002-loan", "NO_CURRENT_APPLICATION_FIELD"),
])
def test_material_mismatch_without_a_gap_is_rejected(tmp_path, crosswalk_id, status):
    def mutate(records):
        c = _find_crosswalk(records, crosswalk_id)
        assert c["coverage_status"] == status
        c["gap_ids"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("requires at least one gap" in issue for issue in issues)


def test_crosswalk_linking_a_different_case_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["gap_ids"] = ["GAP-CONTRACT-FORMATION"]
    issues = _mutated(tmp_path, mutate)
    assert any("belongs to" in issue and "GAP-CONTRACT-FORMATION" in issue for issue in issues)


def test_crosswalk_linking_a_different_document_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["gap_ids"] = ["GAP-ROUTE-EVIDENCE-STANDALONE"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-ROUTE-EVIDENCE-STANDALONE" in issue and "belongs to" in issue for issue in issues)


def test_gap_not_covering_the_linked_official_element_is_rejected(tmp_path):
    def mutate(records):
        g = _find_gap(records, "GAP-PARTY-IDENTITY-DETAILS")
        g["official_element_ids"] = [e for e in g["official_element_ids"]
                                     if e != "loan.party.plaintiff.identity_details"]
    issues = _mutated(tmp_path, mutate)
    assert any("does not cover official element" in issue for issue in issues)


def test_valid_aggregate_gap_remains_usable():
    records = _records()
    c = _find_crosswalk(records, "cw-0173-divorce")
    assert "GAP-DIVORCE-COMBINED-SCOPE" in c["gap_ids"]
    g = _find_gap(records, "GAP-DIVORCE-COMBINED-SCOPE")
    assert c["official_element_id"] in g["official_element_ids"]
    assert len(g["official_element_ids"]) > 1


def test_previously_missing_gap_links_are_resolved():
    records = _records()
    previously_missing = [
        "cw-0024-loan", "cw-0027-loan", "cw-0029-loan", "cw-0032-loan",
        "cw-0069-contract", "cw-0075-contract", "cw-0077-contract",
        "cw-0105-property", "cw-0115-property",
        "cw-0138-labor", "cw-0139-labor", "cw-0144-labor", "cw-0149-labor",
        "cw-0173-divorce", "cw-0174-divorce", "cw-0181-divorce", "cw-0182-divorce",
        "cw-0185-divorce",
    ]
    for cid in previously_missing:
        assert _find_crosswalk(records, cid)["gap_ids"], cid


# ===========================================================================
# C4 — gap-to-route integrity
# ===========================================================================

def test_complaint_route_without_applicable_gaps_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["gap_ids"] = []
    issues = _mutated(tmp_path, mutate)
    assert any("is not linked from" in issue for issue in issues)


def test_route_linking_another_case_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["gap_ids"] = ["GAP-LABOR-ARBITRATION"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-LABOR-ARBITRATION" in issue and "belongs to" in issue for issue in issues)


def test_contract_evidence_route_referencing_loan_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-contract-evidence-list")["gap_ids"] = \
            ["GAP-ROUTE-EVIDENCE-STANDALONE"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-ROUTE-EVIDENCE-STANDALONE" in issue and "belongs to" in issue for issue in issues)


def test_property_address_route_referencing_loan_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-property-service-address-confirmation")["gap_ids"] = \
            ["GAP-ROUTE-ADDRESS-NO-COUNTERPART"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-ROUTE-ADDRESS-NO-COUNTERPART" in issue and "belongs to" in issue
               for issue in issues)


def test_route_linking_a_gap_of_another_document_type_is_rejected(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-evidence-list")["gap_ids"] = ["GAP-PARTY-IDENTITY-DETAILS"]
    issues = _mutated(tmp_path, mutate)
    assert any("GAP-PARTY-IDENTITY-DETAILS" in issue and "belongs to" in issue for issue in issues)


def test_every_route_has_case_scoped_gaps():
    records = _records()
    gap_owner = {g["gap_id"]: (g["case_type"], g["document_type"])
                 for g in records["gaps"]["gaps"]}
    routes = records["routes"]["routes"]
    assert len(routes) == 15
    for r in routes:
        assert r["gap_ids"], r["route_id"]
        for gid in r["gap_ids"]:
            assert gap_owner[gid] == (r["case_type"], r["document_type"])


def test_every_gap_is_reachable_from_its_route():
    records = _records()
    route_by_combo = {(r["case_type"], r["document_type"]): r
                      for r in records["routes"]["routes"]}
    for g in records["gaps"]["gaps"]:
        combo = (g["case_type"], g["document_type"])
        assert combo in route_by_combo
        assert g["gap_id"] in route_by_combo[combo]["gap_ids"]


# ===========================================================================
# C5 — evidence provenance
# ===========================================================================

def test_positive_source_claim_without_page_evidence_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["source_evidence"] = \
            f"spc-2025-notice-pdf sha256:{SOURCE_HASH}"
    issues = _mutated(tmp_path, mutate)
    assert any("source_evidence must cite" in issue for issue in issues)


def test_source_page_outside_verified_bounds_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["source_evidence"] = _source_evidence(99999)
    issues = _mutated(tmp_path, mutate)
    assert any("exceeds the observed page count" in issue for issue in issues)


def test_source_hash_mismatch_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["source_evidence"] = \
            f"spc-2025-notice-pdf p134 sha256:{'0' * 64}"
    issues = _mutated(tmp_path, mutate)
    assert any("does not match the analyzed ledger hash" in issue for issue in issues)


def test_crosswalk_code_evidence_without_a_file_path_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["code_evidence"] = \
            "revision " + FROZEN_REVISION + "; 当事人信息/原告"
    issues = _mutated(tmp_path, mutate)
    assert any("code_evidence clause" in issue for issue in issues)


def test_gap_code_evidence_without_a_file_path_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["code_evidence"] = "revision " + FROZEN_REVISION
    issues = _mutated(tmp_path, mutate)
    assert any("code_evidence must start with" in issue or "code_evidence clause" in issue
               for issue in issues)


def test_code_evidence_without_a_symbol_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["code_evidence"] = \
            "revision " + FROZEN_REVISION + "; models/case_model.py"
    issues = _mutated(tmp_path, mutate)
    assert any("code_evidence clause" in issue for issue in issues)


def test_code_evidence_path_that_does_not_exist_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["code_evidence"] = \
            _crosswalk_code_evidence("models/ghost.py :: GhostModel.render()")
    issues = _mutated(tmp_path, mutate)
    assert any("does not exist in the repository" in issue for issue in issues)


def test_code_evidence_citing_another_case_model_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["code_evidence"] = \
            _crosswalk_code_evidence("models/case_model.py :: ContractCaseModel.render_facts()")
    issues = _mutated(tmp_path, mutate)
    assert any("ContractCaseModel" in issue and "not 'loan'" in issue for issue in issues)


def test_unsupported_visual_verification_claim_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["source_evidence"] = \
            f"spc-2025-notice-pdf p134 sha256:{SOURCE_HASH} VISUAL_VERIFIED"
    issues = _mutated(tmp_path, mutate)
    assert any("must not claim visual verification" in issue for issue in issues)


def test_bounded_negative_search_evidence_is_accepted(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-PARTY-IDENTITY-DETAILS")["source_evidence"] = (
            f'spc-2025-notice-pdf pages 134-136 search:"身份信息" sha256:{SOURCE_HASH}'
        )
    assert _mutated(tmp_path, mutate) == []


def test_current_source_and_code_evidence_is_accepted():
    records = _records()
    assert ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY) == []
    for c in records["crosswalk"]["crosswalks"]:
        assert c["source_evidence"].startswith("spc-2025-notice-pdf")
        assert c["code_evidence"].startswith("revision " + FROZEN_REVISION)
    for g in records["gaps"]["gaps"]:
        assert g["source_evidence"].startswith("spc-2025-notice-pdf")
        assert g["code_evidence"].startswith("revision " + FROZEN_REVISION)


# ===========================================================================
# N25–N28 — defensive validation and determinism
# ===========================================================================

def test_malformed_relationship_metadata_is_rejected_without_exception(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["gap_ids"] = [["nested"]]
    issues = _mutated(tmp_path, mutate)
    assert any("gap_ids entries must be strings" in issue for issue in issues)


def test_malformed_gap_reference_list_is_rejected_without_exception(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["official_element_ids"] = {"not": "a list"}
    issues = _mutated(tmp_path, mutate)
    assert any("official_element_ids must be a list" in issue for issue in issues)


def test_unsupported_approved_state_on_a_gap_is_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["approval_status"] = "APPROVED"
    issues = _mutated(tmp_path, mutate)
    assert any("APPROVED" in issue for issue in issues)


def test_invalid_records_produce_deterministic_issues(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0001-loan")["application_field_ids"] = ["labor.is_no_contract"]
    first = _mutated(tmp_path, mutate)
    second = _mutated(tmp_path, mutate)
    assert first == second
    assert first


def test_corrected_records_validate_end_to_end():
    assert ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY) == []
    assert ctc.main(["--analysis-dir", str(ANALYSIS_DIR),
                     "--source-registry", str(SOURCE_REGISTRY)]) == 0


# ===========================================================================
# Phase 1-B-D — defensive validation
#
# Two remaining defect classes are covered here:
#   D1  a static DIRECT_MATCH could cite a syntactically plausible but
#       nonexistent / unrelated renderer, because only a regex was applied;
#   D2/D3 malformed but syntactically valid JSON metadata could reach set
#       membership, dictionary lookup, tuple construction or nested access and
#       raise an uncaught TypeError/AttributeError.
# ===========================================================================

STATIC_RENDER_CROSSWALKS = (
    "cw-0019-loan", "cw-0020-loan",
    "cw-0059-contract", "cw-0060-contract",
    "cw-0100-property", "cw-0101-property",
    "cw-0134-labor", "cw-0135-labor",
    "cw-0167-divorce", "cw-0168-divorce",
)
FOOTER_EVIDENCE = "utils/doc_generator.py :: DocumentGenerator.add_footer()"


def _mutated_safe(tmp_path, mutate):
    """Run the validator on a mutated fixture, failing if it raises."""
    records = _records()
    mutate(records)
    target = _write(tmp_path, records)
    try:
        return ctc.validate_analysis(target, SOURCE_REGISTRY)
    except Exception as exc:  # noqa: BLE001 - the point of the test is no raise
        pytest.fail(f"validator raised {type(exc).__name__}: {exc}")


def _target(records, spec):
    """Resolve a (kind, identifier) target inside the record set."""
    kind, ident = spec
    if kind == "ledger":
        return records["ledger"]
    if kind == "element":
        return records["elements"]["elements"][ident]
    if kind == "field":
        return records["fields"]["fields"][ident]
    if kind == "crosswalk":
        return _find_crosswalk(records, ident)
    if kind == "gap":
        return _find_gap(records, ident)
    if kind == "route":
        return _find_route(records, ident)
    raise KeyError(spec)


# --- S: static rendering evidence authenticity -----------------------------

def test_s01_verified_footer_renderer_is_accepted():
    issues = []
    accepted = ctc._check_static_rendering_evidence(
        "test", "loan.closing.signature", "civil_complaint", FOOTER_EVIDENCE, issues
    )
    assert accepted is True
    assert issues == []


@pytest.mark.parametrize("crosswalk_id", STATIC_RENDER_CROSSWALKS)
def test_s02_all_frozen_static_matches_are_accepted(tmp_path, crosswalk_id):
    records = _records()
    c = _find_crosswalk(records, crosswalk_id)
    assert c["coverage_status"] == "DIRECT_MATCH"
    assert c["match_mechanism"] == "STATIC_RENDERING"
    assert c["application_field_ids"] == []
    assert c["rendering_evidence"] == FOOTER_EVIDENCE

    def mutate(recs):
        _find_crosswalk(recs, crosswalk_id)["rendering_evidence"] = FOOTER_EVIDENCE
    assert _mutated_safe(tmp_path, mutate) == []


@pytest.mark.parametrize("evidence,reason", [
    pytest.param("nonexistent/renderer.py :: ImaginaryRenderer.render()",
                 "does not exist in the repository", id="s03-nonexistent-file"),
    pytest.param("utils/doc_generator.py :: ImaginaryRenderer.render()",
                 "is not defined in", id="s04-nonexistent-class"),
    pytest.param("utils/doc_generator.py :: DocumentGenerator.imaginary_method()",
                 "is not defined in", id="s05-nonexistent-method"),
    pytest.param("/etc/passwd.py :: DocumentGenerator.add_footer()",
                 "must stay inside the repository", id="s07-absolute-path"),
    pytest.param("../external.py :: DocumentGenerator.add_footer()",
                 "must stay inside the repository", id="s08-parent-traversal"),
    pytest.param("utils/../../outside.py :: DocumentGenerator.add_footer()",
                 "must stay inside the repository", id="s08b-deep-traversal"),
    pytest.param("utils/doc_generator.py :: add_footer()",
                 "must be '<Class>.<method>'", id="s11b-missing-class-qualifier"),
    pytest.param("not a clause at all",
                 "must be '<repo-relative .py path> :: <symbol>'", id="s11-invalid-syntax"),
    pytest.param("",
                 "requires rendering_evidence", id="s10-missing-evidence"),
])
def test_s03_s11_fabricated_static_rendering_evidence_is_rejected(tmp_path, evidence, reason):
    def mutate(records):
        _find_crosswalk(records, "cw-0019-loan")["rendering_evidence"] = evidence
    issues = _mutated_safe(tmp_path, mutate)
    assert any(reason in issue for issue in issues), issues


@pytest.mark.parametrize("crosswalk_id,evidence", [
    pytest.param("cw-0019-loan", "utils/doc_generator.py :: DocumentGenerator.export_address_form()",
                 id="s06-signature-via-address-form"),
    pytest.param("cw-0019-loan", "utils/doc_generator.py :: DocumentGenerator.export_evidence_list()",
                 id="s06b-signature-via-evidence-list"),
    pytest.param("cw-0020-loan", "utils/doc_generator.py :: DocumentGenerator.export_evidence_list()",
                 id="s09-date-via-evidence-list"),
])
def test_s06_s09_unrelated_static_renderer_is_rejected(tmp_path, crosswalk_id, evidence):
    def mutate(records):
        _find_crosswalk(records, crosswalk_id)["rendering_evidence"] = evidence
    issues = _mutated_safe(tmp_path, mutate)
    assert any("does not emit the" in issue for issue in issues), issues


def test_s09b_static_rendering_requires_a_contract_for_the_element(tmp_path):
    def mutate(records):
        c = _find_crosswalk(records, "cw-0004-loan")
        c["application_field_ids"] = []
        c["match_mechanism"] = "STATIC_RENDERING"
        c["rendering_evidence"] = FOOTER_EVIDENCE
    issues = _mutated_safe(tmp_path, mutate)
    assert any("no static-rendering contract is defined" in issue for issue in issues), issues


def test_s12_non_static_direct_match_without_a_field_is_rejected(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0019-loan")["match_mechanism"] = "USER_INPUT_FIELD"
    issues = _mutated_safe(tmp_path, mutate)
    assert any("requires match_mechanism STATIC_RENDERING" in issue for issue in issues)


def test_s12b_static_rendering_must_not_link_application_fields(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0019-loan")["application_field_ids"] = \
            ["shared.party.plaintiff.name"]
    issues = _mutated_safe(tmp_path, mutate)
    assert any("must not link application fields" in issue for issue in issues)


def test_s_rendering_evidence_cannot_escape_the_repository(tmp_path):
    def mutate(records):
        _find_crosswalk(records, "cw-0019-loan")["code_evidence"] = \
            "revision " + FROZEN_REVISION + "; ../outside.py :: DocumentGenerator.add_footer()"
    issues = _mutated_safe(tmp_path, mutate)
    assert any("must stay inside the repository" in issue for issue in issues)


# --- E: enumeration type safety -------------------------------------------

ENUM_TARGETS = [
    pytest.param(("element", 0), "case_type", id="element.case_type"),
    pytest.param(("field", 0), "case_type_or_shared", id="field.case_type_or_shared"),
    pytest.param(("crosswalk", "cw-0001-loan"), "case_type", id="crosswalk.case_type"),
    pytest.param(("crosswalk", "cw-0001-loan"), "coverage_status", id="crosswalk.coverage_status"),
    pytest.param(("crosswalk", "cw-0001-loan"), "match_mechanism", id="crosswalk.match_mechanism"),
    pytest.param(("gap", "GAP-ID-TYPE"), "case_type", id="gap.case_type"),
    pytest.param(("route", "route-loan-civil-complaint"), "case_type", id="route.case_type"),
    pytest.param(("route", "route-loan-civil-complaint"), "document_type", id="route.document_type"),
]

BAD_ENUM_VALUES = [
    pytest.param([], "empty-array", id="empty-array"),
    pytest.param({}, "empty-object", id="empty-object"),
    pytest.param(["loan"], "array-of-string", id="array-of-string"),
    pytest.param({"value": "loan"}, "object-of-string", id="object-of-string"),
    pytest.param(123, "number", id="number"),
    pytest.param(True, "true", id="true"),
    pytest.param(False, "false", id="false"),
    pytest.param(None, "null", id="null"),
    pytest.param("", "empty-string", id="empty-string"),
    pytest.param("UNKNOWN_ENUM_VALUE", "unknown-string", id="unknown-string"),
]


@pytest.mark.parametrize("spec,field", ENUM_TARGETS)
@pytest.mark.parametrize("value,label", BAD_ENUM_VALUES)
def test_e_enumeration_metadata_rejects_malformed_values(tmp_path, spec, field, value, label):
    """E01–E19: every malformed enum value yields an issue, never a traceback."""
    def mutate(records):
        _target(records, spec)[field] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert issues, (spec, field, value)
    assert any(field in issue for issue in issues), (spec, field, value, issues)


@pytest.mark.parametrize("spec,field", ENUM_TARGETS)
def test_e20_valid_enumeration_strings_remain_accepted(spec, field):
    """E20: the real dataset keeps its valid enumeration strings."""
    records = _records()
    value = _target(records, spec)[field]
    assert isinstance(value, str) and value
    assert ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY) == []


def test_e_optional_null_enum_semantics_are_preserved():
    """A null enum is rejected unless the caller marks the field optional."""
    issues = []
    assert ctc._check_enum("t", "case_type", None, ctc.CASE_TYPES, issues) is None
    assert issues and "null" in issues[0]

    optional_issues = []
    assert ctc._check_enum("t", "case_type", None, ctc.CASE_TYPES, optional_issues,
                           optional=True) is None
    assert optional_issues == []


@pytest.mark.parametrize("value,label", [
    pytest.param([["civil_complaint"]], "nested-array", id="nested-array"),
    pytest.param([{"a": 1}], "nested-object", id="nested-object"),
    pytest.param({"a": 1}, "object", id="object"),
    pytest.param("civil_complaint", "string", id="string"),
    pytest.param(5, "number", id="number"),
    pytest.param(True, "boolean", id="boolean"),
    pytest.param(None, "null", id="null"),
])
def test_e_output_document_types_rejects_malformed_values(tmp_path, value, label):
    """E05/E06: a nested container inside output_document_types must not crash."""
    def mutate(records):
        records["fields"]["fields"][0]["output_document_types"] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any("output_document_types" in issue for issue in issues), issues


def test_e_valid_output_document_types_remain_accepted(tmp_path):
    def mutate(records):
        records["fields"]["fields"][0]["output_document_types"] = ["civil_complaint"]
    assert _mutated_safe(tmp_path, mutate) == []


# --- R: nested metadata and relationship safety ---------------------------

@pytest.mark.parametrize("value,label", [
    pytest.param([], "empty-array", id="empty-array"),
    pytest.param([1], "nonempty-array", id="nonempty-array"),
    pytest.param("PASS", "string", id="string"),
    pytest.param(5, "number", id="number"),
    pytest.param(True, "boolean", id="boolean"),
])
def test_r01_r02_nested_ledger_hash_comparison_is_rejected_safely(tmp_path, value, label):
    def mutate(records):
        records["ledger"]["registry_hash_comparison"] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any("registry_hash_comparison" in issue for issue in issues), issues


@pytest.mark.parametrize("value,label", [
    pytest.param([], "array", id="array"),
    pytest.param("x", "string", id="string"),
    pytest.param(5, "number", id="number"),
])
def test_r01b_nested_ledger_retrieval_is_rejected_safely(tmp_path, value, label):
    def mutate(records):
        records["ledger"]["retrieval"] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any("retrieval" in issue for issue in issues), issues


RELATIONSHIP_CASES = [
    pytest.param(("crosswalk", "cw-0001-loan"), "application_field_ids", {"a": 1},
                 "must be a list", id="r03-crosswalk-application_field_ids-object"),
    pytest.param(("crosswalk", "cw-0001-loan"), "application_field_ids",
                 "shared.party.plaintiff.name", "must be a list",
                 id="r03b-crosswalk-application_field_ids-string"),
    pytest.param(("crosswalk", "cw-0001-loan"), "gap_ids", {"a": 1},
                 "must be a list", id="r05-crosswalk-gap_ids-object"),
    pytest.param(("gap", "GAP-ID-TYPE"), "official_element_ids", {"a": 1},
                 "must be a list", id="r04-gap-official_element_ids-object"),
    pytest.param(("gap", "GAP-ID-TYPE"), "official_element_ids",
                 "loan.party.plaintiff.id_document", "must be a list",
                 id="r04b-gap-official_element_ids-string"),
    pytest.param(("gap", "GAP-ID-TYPE"), "application_field_ids", {"a": 1},
                 "must be a list", id="r04c-gap-application_field_ids-object"),
    pytest.param(("route", "route-loan-civil-complaint"), "official_source_ids", {"a": 1},
                 "must be a list", id="r06-route-official_source_ids-object"),
    pytest.param(("route", "route-loan-civil-complaint"), "official_source_ids", 7,
                 "must be a list", id="r06b-route-official_source_ids-number"),
    pytest.param(("route", "route-loan-civil-complaint"), "official_source_ids",
                 "spc-2025-notice-pdf", "must be a list",
                 id="r06c-route-official_source_ids-string"),
    pytest.param(("route", "route-loan-civil-complaint"), "official_source_ids",
                 [["spc-2025-notice-pdf"]], "entries must be strings",
                 id="r07-route-official_source_ids-nested-array"),
    pytest.param(("route", "route-loan-civil-complaint"), "gap_ids", {"a": 1},
                 "must be a list", id="r05b-route-gap_ids-object"),
    pytest.param(("field", 0), "output_document_types", [["civil_complaint"]],
                 "entries must be strings", id="r07b-field-output_document_types-nested"),
]


@pytest.mark.parametrize("spec,field,value,reason", RELATIONSHIP_CASES)
def test_r03_r07_relationship_metadata_is_rejected_safely(tmp_path, spec, field, value, reason):
    def mutate(records):
        _target(records, spec)[field] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any(field in issue and reason in issue for issue in issues), issues


@pytest.mark.parametrize("key,field_name,value,label", [
    pytest.param("crosswalk", "crosswalks", 5, "number", id="crosswalk-number"),
    pytest.param("crosswalk", "crosswalks", {"a": 1}, "object", id="crosswalk-object"),
    pytest.param("gaps", "gaps", 5, "number", id="gaps-number"),
    pytest.param("gaps", "gaps", {"a": 1}, "object", id="gaps-object"),
    pytest.param("routes", "routes", 5, "number", id="routes-number"),
    pytest.param("elements", "elements", 5, "number", id="elements-number"),
    pytest.param("fields", "fields", 5, "number", id="fields-number"),
])
def test_record_block_type_is_rejected_safely(tmp_path, key, field_name, value, label):
    """A non-list record block must not reach iteration or the approval loop."""
    def mutate(records):
        records[key][field_name] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any(field_name in issue for issue in issues), issues


@pytest.mark.parametrize("value,label", [
    pytest.param(["loan"], "array", id="array"),
    pytest.param({"loan": True}, "object", id="object"),
])
def test_r08_unhashable_gap_key_never_reaches_route_lookup(tmp_path, value, label):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["case_type"] = value
    issues = _mutated_safe(tmp_path, mutate)
    assert any("case_type must be a string" in issue for issue in issues), issues


def test_r09_unhashable_route_key_never_reaches_combination_lookup(tmp_path):
    def mutate(records):
        _find_route(records, "route-loan-civil-complaint")["case_type"] = ["loan"]
    issues = _mutated_safe(tmp_path, mutate)
    assert any("case_type must be a string" in issue for issue in issues), issues
    # the malformed route is dropped, so its gaps are reported as unreachable
    assert any("no route assessment exists" in issue for issue in issues), issues


def test_r10_malformed_metadata_diagnostics_are_deterministic(tmp_path):
    def mutate(records):
        records["elements"]["elements"][0]["case_type"] = ["loan"]
        _find_gap(records, "GAP-ID-TYPE")["case_type"] = ["loan"]
        _find_route(records, "route-loan-civil-complaint")["document_type"] = {"x": 1}
    first = _mutated_safe(tmp_path, mutate)
    second = _mutated_safe(tmp_path, mutate)
    assert first
    assert first == second


def test_r11_r12_cli_rejects_malformed_metadata_without_traceback(tmp_path):
    records = _records()
    records["elements"]["elements"][0]["case_type"] = ["loan"]
    records["ledger"]["registry_hash_comparison"] = [1]
    target = _write(tmp_path, records)
    result = subprocess.run(
        [sys.executable, "tools/check_template_crosswalk.py",
         "--analysis-dir", str(target), "--source-registry", str(SOURCE_REGISTRY)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "case_type" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_r13_approved_state_is_still_rejected(tmp_path):
    def mutate(records):
        _find_gap(records, "GAP-ID-TYPE")["approval_status"] = "APPROVED"
    issues = _mutated_safe(tmp_path, mutate)
    assert any("APPROVED" in issue for issue in issues), issues


def test_r14_real_analytical_records_are_unchanged():
    records = _records()
    assert len(records["elements"]["elements"]) == 185
    assert len(records["fields"]["fields"]) == 52
    assert len(records["crosswalk"]["crosswalks"]) == 199
    assert len(records["gaps"]["gaps"]) == 131
    assert len(records["routes"]["routes"]) == 15
    assert ctc.validate_analysis(ANALYSIS_DIR, SOURCE_REGISTRY) == []
