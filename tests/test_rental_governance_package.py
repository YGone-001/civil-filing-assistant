# File: tests/test_rental_governance_package.py
# Purpose: Guard the post-baseline rental governance work package against false approvals.
# Encoding: UTF-8

import json
from pathlib import Path

import pytest

from tools import check_rental_governance_package as crgp

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = (
    REPO_ROOT
    / "docs"
    / "legal-template-governance"
    / "official-adaptation-planning"
    / "rental-contract-work-package.json"
)
SOURCE_REGISTRY = (
    REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"
)
MAPPING_REGISTRY = (
    REPO_ROOT / "docs" / "legal-template-governance" / "case-template-mapping.json"
)


def _load():
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


def _registry():
    return json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))


def _mapping_registry():
    return json.loads(MAPPING_REGISTRY.read_text(encoding="utf-8"))


def test_real_rental_governance_package_is_valid():
    issues = crgp.validate_package(_load(), _registry(), _mapping_registry())
    assert issues == [], issues


def test_package_rejects_a_non_rental_case_type():
    data = _load()
    data["case_type"] = "loan"
    assert any("case_type" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_selected_source():
    data = _load()
    data["source_discovery"]["selected_source_id"] = "spc-2025-notice-pdf"
    assert any("selected_source_id" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_unknown_candidate_source():
    data = _load()
    data["source_discovery"]["candidate_source_ids"] = ["invented-source"]
    issues = crgp.validate_package(data, _registry())
    assert any("candidate_source_ids" in issue for issue in issues)


def test_package_rejects_candidate_identification_without_candidates():
    data = _load()
    data["source_discovery"]["candidate_source_ids"] = []
    assert any(
        "candidate_source_ids" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_unknown_counterpart_after_candidate_identification():
    data = _load()
    data["source_discovery"]["official_counterpart"] = "UNKNOWN"
    assert any("official_counterpart" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_hash_that_does_not_match_the_registry():
    data = _load()
    data["source_verification"]["sha256"] = "0" * 64
    issues = crgp.validate_package(data, _registry())
    assert any("sha256" in issue for issue in issues)


def test_package_rejects_a_source_stored_in_the_repository():
    data = _load()
    data["source_verification"]["local_artifact_status"] = "IN_REPOSITORY"
    assert any(
        "local_artifact_status" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_invalid_source_verification_metadata():
    data = _load()
    data["source_verification"]["page_count"] = 0
    assert any("page_count" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_standalone_official_evidence_list_claim():
    data = _load()
    data["counterpart_assessment"]["evidence_list"][
        "classification"
    ] = "CANDIDATE_OFFICIAL_COMPLAINT"
    assert any("evidence_list" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_official_service_address_counterpart():
    data = _load()
    data["counterpart_assessment"]["service_address_confirmation"][
        "classification"
    ] = "CANDIDATE_OFFICIAL_COMPLAINT"
    assert any(
        "service_address_confirmation" in issue
        for issue in crgp.validate_package(data)
    )


def test_package_rejects_an_inverted_page_range():
    data = _load()
    data["counterpart_assessment"]["civil_complaint"]["blank_form_pdf_pages"] = [176, 171]
    assert any("blank_form_pdf_pages" in issue for issue in crgp.validate_package(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("implementation_authorization", "AUTHORIZED"),
        ("legal_review_status", "REVIEWED"),
        ("rights_review_status", "REVIEWED"),
        ("release_gate", "GO"),
        ("frozen_planning_records_modified", True),
        ("assigned_reviewers", ["invented reviewer"]),
    ],
)
def test_package_rejects_false_approval_states(field, value):
    data = _load()
    data[field] = value
    assert crgp.validate_package(data), f"{field} should be rejected"


def test_package_requires_the_central_mapping_update():
    data = _load()
    data["central_mapping_registry_updated"] = False
    assert any(
        "central_mapping_registry_updated" in issue
        for issue in crgp.validate_package(data)
    )


def test_package_rejects_missing_rental_mapping_entries():
    data = _load()
    registry = _mapping_registry()
    registry["mappings"] = [
        mapping for mapping in registry["mappings"]
        if mapping.get("case_type") != "rental"
    ]
    issues = crgp.validate_package(data, _registry(), registry)
    assert any("three rental mappings" in issue for issue in issues)


def test_package_rejects_an_approved_rental_mapping():
    data = _load()
    registry = _mapping_registry()
    for mapping in registry["mappings"]:
        if mapping.get("mapping_id") == "map-rental-complaint":
            mapping["mapping_status"] = "APPROVED"
            mapping["approval_status"] = "APPROVED"
    issues = crgp.validate_package(data, _registry(), registry)
    assert any("approval_status" in issue for issue in issues)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "COMPLETE"),
        ("review_performed", True),
        ("reviewer_assigned", True),
        ("review_date", "2026-11-26"),
    ],
)
def test_package_rejects_a_performed_legal_review(field, value):
    data = _load()
    data["legal_content_review"][field] = value
    assert crgp.validate_package(data), f"{field} should be rejected"


def test_package_rejects_a_legal_question_count_mismatch():
    data = _load()
    data["legal_content_review"]["question_count"] = 20
    assert any(
        "question_count" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_missing_review_agenda():
    data = _load()
    data["legal_content_review"]["agenda_document"] = "other.md"
    assert any(
        "agenda_document" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_confirmed_reviewer_candidate():
    data = _load()
    data["legal_content_review"]["reviewer_candidate"]["status"] = "ASSIGNED"
    assert any(
        "reviewer_candidate" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_missing_preflight():
    data = _load()
    del data["legal_content_review"]["preflight"]
    assert any(
        "preflight" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_non_complete_preflight():
    data = _load()
    data["legal_content_review"]["preflight"]["status"] = "NOT_STARTED"
    assert any(
        "preflight.status" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_closed_preflight_finding():
    data = _load()
    data["legal_content_review"]["preflight"]["findings"][0]["status"] = "APPROVED"
    assert any(
        "findings[0].status" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_preflight_finding_count_mismatch():
    data = _load()
    data["legal_content_review"]["preflight"]["findings"].pop()
    assert any(
        "four findings" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_pf03_fix():
    data = _load()
    data["legal_content_review"]["preflight"]["findings"][2][
        "status"
    ] = "FIXED_PENDING_RECHECK"
    assert any(
        "findings[2]" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_scoped_authorization_outside_pf01_pf02():
    data = _load()
    data["scoped_engineering_authorization"]["scope"].append("PF-03")
    assert any(
        "scope" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_scoped_authorization_as_overall_authorization():
    data = _load()
    data["scoped_engineering_authorization"][
        "overall_implementation_authorization"
    ] = "AUTHORIZED"
    assert any(
        "overall_implementation_authorization" in issue
        for issue in crgp.validate_package(data)
    )


def test_package_rejects_an_incomplete_document_set():
    data = _load()
    data["document_types"] = ["civil_complaint", "evidence_list"]
    assert any("document_types" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_skipped_stage():
    data = _load()
    data["current_stage"] = "ENGINEERING_IMPLEMENTATION"
    assert any("current_stage" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_non_complete_comparison():
    data = _load()
    data["text_and_structure_comparison"]["status"] = "NOT_STARTED"
    assert any(
        "text_and_structure_comparison.status" in issue
        for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_comparison_gap_count_mismatch():
    data = _load()
    data["text_and_structure_comparison"]["gap_count"] = 34
    assert any(
        "gap_count" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_a_comparison_page_range_mismatch():
    data = _load()
    data["text_and_structure_comparison"]["blank_form_pdf_pages"] = [170, 176]
    assert any(
        "blank_form_pdf_pages" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_an_invalid_comparison_gap_id():
    data = _load()
    data["text_and_structure_comparison"]["gap_register_ids"][0] = "GAP-01"
    assert any(
        "gap_register_ids" in issue for issue in crgp.validate_package(data)
    )


def test_package_rejects_an_incomplete_past_stage():
    data = _load()
    data["tasks"][0]["status"] = "NOT_STARTED"
    assert any("tasks[0]" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_incomplete_comparison_stage():
    data = _load()
    data["tasks"][2]["status"] = "NOT_STARTED"
    assert any("tasks[2]" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_incomplete_mapping_review_stage():
    data = _load()
    data["tasks"][3]["status"] = "NOT_STARTED"
    assert any("tasks[3]" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_completed_current_stage():
    data = _load()
    data["tasks"][4]["status"] = "COMPLETE"
    assert any("tasks[4]" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_completed_later_task():
    data = _load()
    data["tasks"][5]["status"] = "COMPLETE"
    assert any("completion" in issue for issue in crgp.validate_package(data))


@pytest.mark.parametrize("field", ["source_discovery", "source_verification",
                                   "counterpart_assessment",
                                   "text_and_structure_comparison",
                                   "case_mapping_review",
                                   "legal_content_review",
                                   "scoped_engineering_authorization"])
def test_package_rejects_missing_evidence_sections(field):
    data = _load()
    del data[field]
    assert any(field in issue for issue in crgp.validate_package(data))


def test_package_rejects_out_of_order_task_stages():
    data = _load()
    data["tasks"][0], data["tasks"][1] = data["tasks"][1], data["tasks"][0]
    assert any("stage" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_invalid_baseline_commit():
    data = _load()
    data["baseline_commit"] = "not-a-sha"
    assert any("baseline_commit" in issue for issue in crgp.validate_package(data))


def test_package_cli_accepts_the_real_file(capsys):
    assert crgp.main(["--package", str(PACKAGE)]) == 0
    assert "OK" in capsys.readouterr().out
