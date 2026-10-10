# File: tests/test_template_governance.py
# Purpose: Positive and negative tests for the legal-template governance metadata
#          and its validator.
# Encoding: UTF-8
"""Governance metadata validation tests.

These tests are pure Python (no Qt) and use fictional fixture data only. No real
litigant data, no network access, and no repository mutation.
"""

import copy
import json
from pathlib import Path

import pytest

from tools import check_template_governance as ctg

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"
MAPPING_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "case-template-mapping.json"


# --- fixtures ---------------------------------------------------------------


def _valid_source(**overrides):
    source = {
        "source_id": "test-source",
        "title": "示例来源",
        "issuing_authority": "示例机关",
        "source_type": "OFFICIAL_NOTICE",
        "official_url": "https://example.invalid/notice",
        "publication_date": None,
        "document_date": None,
        "retrieval_or_review_date": "2026-10-10",
        "source_level": "A",
        "verification_status": "ANNOUNCEMENT_VERIFIED",
        "verification_evidence": "retrieved and read on 2026-10-10",
        "local_artifact_status": "NOT_STORED_IN_REPOSITORY",
        "content_hash_if_verified": None,
        "legal_or_copyright_review_status": "NOT_REVIEWED",
        "notes": "",
    }
    source.update(overrides)
    return source


def _valid_mapping(case_type="loan", document_type="civil_complaint", **overrides):
    mapping = {
        "mapping_id": f"map-{case_type}-{document_type.replace('_', '-')}",
        "case_type": case_type,
        "document_type": document_type,
        "current_generator": "utils/doc_generator.py :: export_x",
        "current_output_status": "IMPLEMENTED_AND_TESTED",
        "candidate_source_ids": [],
        "mapping_status": "UNVERIFIED",
        "mapping_confidence_or_evidence": "",
        "jurisdictional_scope": None,
        "applicability_notes": "",
        "unverified_assumptions": [],
        "required_manual_review": True,
        "approval_status": "NOT_REQUESTED",
        "notes": "",
    }
    mapping.update(overrides)
    return mapping


def _all_mappings(**overrides):
    return [
        _valid_mapping(case_type, document_type, **overrides)
        for case_type in sorted(ctg.CASE_TYPES)
        for document_type in sorted(ctg.DOCUMENT_TYPES)
    ]


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_pair(tmp_path, sources, mappings):
    return (
        _write(tmp_path, "source-registry.json", {"sources": sources}),
        _write(tmp_path, "case-template-mapping.json", {"mappings": mappings}),
    )


def _issues(tmp_path, sources, mappings):
    source_path, mapping_path = _write_pair(tmp_path, sources, mappings)
    return ctg.validate_registries(source_path, mapping_path)


# --- positive tests ---------------------------------------------------------


def test_repository_registry_is_valid():
    assert ctg.validate_registries(SOURCE_REGISTRY, MAPPING_REGISTRY) == []
    assert ctg.main(["--source-registry", str(SOURCE_REGISTRY),
                     "--mapping-registry", str(MAPPING_REGISTRY)]) == 0


def test_repository_registry_covers_all_case_types():
    data = json.loads(MAPPING_REGISTRY.read_text(encoding="utf-8"))
    assert {m["case_type"] for m in data["mappings"]} == set(ctg.CASE_TYPES)


def test_repository_registry_covers_all_document_types():
    data = json.loads(MAPPING_REGISTRY.read_text(encoding="utf-8"))
    assert {m["document_type"] for m in data["mappings"]} == set(ctg.DOCUMENT_TYPES)


def test_repository_registry_has_exactly_fifteen_combinations():
    data = json.loads(MAPPING_REGISTRY.read_text(encoding="utf-8"))
    combos = {(m["case_type"], m["document_type"]) for m in data["mappings"]}
    assert len(combos) == 15
    assert len(data["mappings"]) == 15


def test_unverified_mappings_are_permitted(tmp_path):
    issues = _issues(tmp_path, [_valid_source()], _all_mappings(mapping_status="UNVERIFIED"))
    assert issues == []


def test_announcement_verification_does_not_imply_template_verification(tmp_path):
    # An announcement-only source (no hash) is valid ...
    ok = _issues(tmp_path, [_valid_source(verification_status="ANNOUNCEMENT_VERIFIED")],
                 _all_mappings())
    assert ok == []
    # ... but claiming the file itself was verified without a hash is not.
    bad = _issues(tmp_path, [_valid_source(verification_status="SOURCE_FILE_VERIFIED")],
                  _all_mappings())
    assert any("content hash" in issue for issue in bad)


def test_approval_with_documented_evidence_is_accepted(tmp_path):
    mappings = _all_mappings()
    mappings[0] = _valid_mapping(
        mappings[0]["case_type"],
        mappings[0]["document_type"],
        mapping_status="APPROVED",
        approval_status="APPROVED",
        approved_by_or_review_role="示例审查角色",
        approval_date="2026-10-10",
        approval_evidence="示例审批记录",
    )
    assert _issues(tmp_path, [_valid_source()], mappings) == []


def test_validator_is_deterministic(tmp_path):
    source_path, mapping_path = _write_pair(
        tmp_path, [_valid_source()], _all_mappings()
    )
    first = ctg.validate_registries(source_path, mapping_path)
    second = ctg.validate_registries(source_path, mapping_path)
    assert first == second == []


# --- negative tests ---------------------------------------------------------


def test_malformed_registry_is_rejected(tmp_path):
    bad = tmp_path / "source-registry.json"
    bad.write_text("{ this is not json ", encoding="utf-8")
    mapping_path = _write(tmp_path, "case-template-mapping.json", {"mappings": _all_mappings()})
    issues = ctg.validate_registries(bad, mapping_path)
    assert any("invalid JSON" in issue for issue in issues)


def test_missing_source_id_is_rejected(tmp_path):
    source = _valid_source()
    del source["source_id"]
    issues = _issues(tmp_path, [source], _all_mappings())
    assert any("source_id" in issue for issue in issues)


def test_duplicate_source_id_is_rejected(tmp_path):
    issues = _issues(tmp_path, [_valid_source(), _valid_source()], _all_mappings())
    assert any("duplicate source_id" in issue for issue in issues)


def test_invalid_source_type_is_rejected(tmp_path):
    issues = _issues(tmp_path, [_valid_source(source_type="MADE_UP_TYPE")], _all_mappings())
    assert any("unknown source_type" in issue for issue in issues)


def test_invalid_verification_status_is_rejected(tmp_path):
    issues = _issues(tmp_path, [_valid_source(verification_status="PROBABLY_FINE")], _all_mappings())
    assert any("invalid verification_status" in issue for issue in issues)


def test_unverified_source_marked_approved_is_rejected(tmp_path):
    source = _valid_source(
        verification_status="APPROVED_FOR_ADAPTATION",
        legal_or_copyright_review_status="NOT_REVIEWED",
    )
    issues = _issues(tmp_path, [source], _all_mappings())
    assert any("APPROVED_FOR_ADAPTATION" in issue for issue in issues)


def test_mapping_referencing_unknown_source_is_rejected(tmp_path):
    mapping = _valid_mapping(candidate_source_ids=["does-not-exist"])
    issues = _issues(tmp_path, [_valid_source()], [mapping])
    assert any("unknown source_id" in issue for issue in issues)


def test_duplicate_case_document_mapping_is_rejected(tmp_path):
    first = _valid_mapping("loan", "civil_complaint")
    second = _valid_mapping("loan", "civil_complaint", mapping_id="map-loan-complaint-2")
    issues = _issues(tmp_path, [_valid_source()], [first, second])
    assert any("duplicate case-document combination" in issue for issue in issues)


def test_missing_required_case_document_mapping_is_rejected(tmp_path):
    mappings = _all_mappings()
    mappings = [m for m in mappings if not (m["case_type"] == "divorce"
                                           and m["document_type"] == "evidence_list")]
    issues = _issues(tmp_path, [_valid_source()], mappings)
    assert any("missing case-document combinations" in issue for issue in issues)


def test_invalid_official_source_hash_is_rejected(tmp_path):
    source = _valid_source(
        verification_status="SOURCE_FILE_VERIFIED",
        content_hash_if_verified="sha256:NOT-A-REAL-HASH",
    )
    issues = _issues(tmp_path, [source], _all_mappings())
    assert any("content hash" in issue for issue in issues)


def test_discovered_source_with_hash_is_rejected(tmp_path):
    source = _valid_source(
        verification_status="DISCOVERED",
        content_hash_if_verified="sha256:" + "0" * 64,
    )
    issues = _issues(tmp_path, [source], _all_mappings())
    assert any("DISCOVERED" in issue for issue in issues)


def test_approval_record_without_evidence_is_rejected(tmp_path):
    mapping = _valid_mapping(mapping_status="APPROVED", approval_status="APPROVED")
    issues = _issues(tmp_path, [_valid_source()], [mapping])
    assert any("approval claimed without documented" in issue for issue in issues)


def test_invalid_date_is_rejected(tmp_path):
    source = _valid_source(publication_date="2025-13-45")
    issues = _issues(tmp_path, [source], _all_mappings())
    assert any("date" in issue for issue in issues)


def test_unknown_case_type_is_rejected(tmp_path):
    mapping = _valid_mapping()
    mapping["case_type"] = "not-a-case"
    issues = _issues(tmp_path, [_valid_source()], [mapping])
    assert any("unknown case_type" in issue for issue in issues)


def test_unknown_document_type_is_rejected(tmp_path):
    mapping = _valid_mapping()
    mapping["document_type"] = "not-a-document"
    issues = _issues(tmp_path, [_valid_source()], [mapping])
    assert any("unknown document_type" in issue for issue in issues)
