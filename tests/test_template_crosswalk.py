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
