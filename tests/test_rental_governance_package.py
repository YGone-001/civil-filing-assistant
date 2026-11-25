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


def _load():
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


def test_real_rental_governance_package_is_valid():
    issues = crgp.validate_package(_load())
    assert issues == [], issues


def test_package_rejects_a_non_rental_case_type():
    data = _load()
    data["case_type"] = "loan"
    assert any("case_type" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_selected_source_before_discovery():
    data = _load()
    data["source_discovery"]["selected_source_id"] = "spc-2025-notice-pdf"
    assert any("selected_source_id" in issue for issue in crgp.validate_package(data))


def test_package_rejects_candidate_sources_in_the_initial_snapshot():
    data = _load()
    data["source_discovery"]["candidate_source_ids"] = ["spc-2025-notice-pdf"]
    assert any("candidate_source_ids" in issue for issue in crgp.validate_package(data))


@pytest.mark.parametrize(
    "field,value",
    [
        ("implementation_authorization", "AUTHORIZED"),
        ("legal_review_status", "REVIEWED"),
        ("rights_review_status", "REVIEWED"),
        ("release_gate", "GO"),
        ("central_mapping_registry_updated", True),
        ("frozen_planning_records_modified", True),
        ("assigned_reviewers", ["invented reviewer"]),
    ],
)
def test_package_rejects_false_approval_states(field, value):
    data = _load()
    data[field] = value
    assert crgp.validate_package(data), f"{field} should be rejected"


def test_package_rejects_an_incomplete_document_set():
    data = _load()
    data["document_types"] = ["civil_complaint", "evidence_list"]
    assert any("document_types" in issue for issue in crgp.validate_package(data))


def test_package_rejects_a_completed_task():
    data = _load()
    data["tasks"][0]["status"] = "COMPLETE"
    assert any("completion" in issue for issue in crgp.validate_package(data))


def test_package_rejects_out_of_order_task_stages():
    data = _load()
    data["tasks"][0], data["tasks"][1] = data["tasks"][1], data["tasks"][0]
    assert any("stage" in issue for issue in crgp.validate_package(data))


def test_package_rejects_an_invalid_baseline_commit():
    data = _load()
    data["baseline_commit"] = "not-a-sha"
    assert any("baseline_commit" in issue for issue in crgp.validate_package(data))


def test_package_rejects_missing_source_discovery():
    data = _load()
    del data["source_discovery"]
    assert any("source_discovery" in issue for issue in crgp.validate_package(data))


def test_package_cli_accepts_the_real_file(capsys):
    assert crgp.main(["--package", str(PACKAGE)]) == 0
    assert "OK" in capsys.readouterr().out
