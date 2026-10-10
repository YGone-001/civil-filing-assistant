# File: tests/test_template_governance.py
# Purpose: Positive and negative tests for the legal-template governance metadata
#          and its approval-integrity validator.
# Encoding: UTF-8
"""Governance metadata validation tests.

These tests are pure Python (no Qt) and use fictional fixture data only. No real
litigant data, no network access, and no repository mutation.

**Approval-integrity contract under test:** populating approval text fields is
not sufficient for approval. An ``APPROVED`` mapping must bind one explicitly
selected source that is itself an eligible official template which has reached
``APPROVED_FOR_ADAPTATION`` with a verified hash, a completed legal/content
review and distinct evidence for each review stage.

All synthetic approval records below are **test fixtures only**. They are never
written into the real registries and are never a real legal approval.
"""

import json
from pathlib import Path

import pytest

from tools import check_template_governance as ctg

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "source-registry.json"
MAPPING_REGISTRY = REPO_ROOT / "docs" / "legal-template-governance" / "case-template-mapping.json"

SYNTHETIC_SOURCE_ID = "synthetic-approved-template"
SYNTHETIC_HASH = "sha256:" + "a" * 64


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


def _synthetic_approved_source(**overrides):
    """A structurally complete, clearly-fictional approved template fixture."""
    source = _valid_source(
        source_id=SYNTHETIC_SOURCE_ID,
        title="[TEST FIXTURE] Synthetic approved official template",
        issuing_authority="Fictional Issuing Authority (test fixture)",
        source_type="OFFICIAL_TEMPLATE",
        source_level="A",
        verification_status="APPROVED_FOR_ADAPTATION",
        verification_evidence="Synthetic fixture: file retrieved and hashed",
        content_hash_if_verified=SYNTHETIC_HASH,
        legal_or_copyright_review_status="REVIEWED",
        content_review_evidence="Synthetic content review fixture",
        mapping_review_evidence="Synthetic applicability review fixture",
        legal_content_review_evidence="Synthetic legal review fixture",
        approval_evidence="Synthetic source approval fixture",
        notes="TEST FIXTURE ONLY - not a real legal approval",
    )
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


def _approved_mapping(case_type="contract", document_type="civil_complaint", **overrides):
    """A fully-populated approved mapping fixture bound to the synthetic source."""
    mapping = _valid_mapping(
        case_type,
        document_type,
        candidate_source_ids=[SYNTHETIC_SOURCE_ID],
        mapping_status="APPROVED",
        approval_status="APPROVED",
        approved_source_id=SYNTHETIC_SOURCE_ID,
        approved_by_or_review_role="Fictional Review Role (test fixture)",
        approval_date="2026-10-10",
        approval_evidence="Synthetic mapping approval fixture",
    )
    mapping.update(overrides)
    return mapping


def _fixture_mappings(approved=None):
    """All fifteen combinations; *approved* replaces its own slot when supplied."""
    mappings = []
    for case_type in sorted(ctg.CASE_TYPES):
        for document_type in sorted(ctg.DOCUMENT_TYPES):
            if (
                approved is not None
                and approved.get("case_type") == case_type
                and approved.get("document_type") == document_type
            ):
                mappings.append(approved)
            else:
                mappings.append(_valid_mapping(case_type, document_type))
    return mappings


def _all_mappings(**overrides):
    return [_valid_mapping(c, d, **overrides)
            for c in sorted(ctg.CASE_TYPES) for d in sorted(ctg.DOCUMENT_TYPES)]


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


def _approval_issues(tmp_path, source, mapping_overrides=None, approved=None):
    """Validate one synthetic approved mapping against one synthetic source."""
    mapping = approved if approved is not None else _approved_mapping(**(mapping_overrides or {}))
    return _issues(tmp_path, [source], _fixture_mappings(mapping))


# --- repository registry (positive) -----------------------------------------


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


def test_repository_registry_has_no_approved_mapping():
    data = json.loads(MAPPING_REGISTRY.read_text(encoding="utf-8"))
    assert [m for m in data["mappings"] if m["approval_status"] == "APPROVED"] == []
    assert [m for m in data["mappings"] if m["mapping_status"] == "APPROVED"] == []
    assert all("approved_source_id" not in m or m["approved_source_id"] is None
               for m in data["mappings"])


def test_repository_source_verification_states_unchanged():
    data = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    by_id = {s["source_id"]: s["verification_status"] for s in data["sources"]}
    assert len(by_id) == 7
    assert by_id["spc-2025-notice-pdf"] == "SOURCE_FILE_VERIFIED"
    assert "APPROVED_FOR_ADAPTATION" not in by_id.values()


def test_unverified_mappings_are_permitted(tmp_path):
    issues = _issues(tmp_path, [_valid_source()], _all_mappings(mapping_status="UNVERIFIED"))
    assert issues == []


def test_announcement_verification_does_not_imply_template_verification(tmp_path):
    ok = _issues(tmp_path, [_valid_source(verification_status="ANNOUNCEMENT_VERIFIED")], _all_mappings())
    assert ok == []
    bad = _issues(tmp_path, [_valid_source(verification_status="SOURCE_FILE_VERIFIED")], _all_mappings())
    assert any("content hash" in issue for issue in bad)


def test_validator_is_deterministic(tmp_path):
    source_path, mapping_path = _write_pair(tmp_path, [_valid_source()], _all_mappings())
    assert ctg.validate_registries(source_path, mapping_path) == []
    assert ctg.validate_registries(source_path, mapping_path) == []


# --- C3-T01 / C2-T10: the valid synthetic approval fixture -------------------


def test_valid_synthetic_approval_fixture_is_accepted(tmp_path):
    """C3-T01 / C2-T10 / C4-T10: a complete, consistent approval is accepted."""
    assert _approval_issues(tmp_path, _synthetic_approved_source()) == []


def test_valid_synthetic_approval_fixture_with_reproduced_level_b_source(tmp_path):
    """A verified level-B official reproduction is also an eligible source."""
    source = _synthetic_approved_source(
        source_id=SYNTHETIC_SOURCE_ID,
        source_type="REPRODUCED_OFFICIAL_SOURCE",
        source_level="B",
    )
    assert _approval_issues(tmp_path, source) == []


# --- C5: corrected former positive test -------------------------------------


def test_approval_with_metadata_but_no_source_is_rejected(tmp_path):
    """Corrected former positive test: approval metadata alone is not approval."""
    issues = _approval_issues(
        tmp_path,
        _valid_source(),
        approved=_approved_mapping(candidate_source_ids=[], approved_source_id=None),
    )
    assert any("approved_source_id" in issue for issue in issues)


# --- C1: approved mapping must reference an eligible source ------------------


def test_c1_t01_approved_mapping_without_source_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(candidate_source_ids=[], approved_source_id=None),
    )
    assert any("approved_source_id" in issue for issue in issues)


def test_c1_t02_approved_mapping_with_unknown_source_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(candidate_source_ids=["ghost"], approved_source_id="ghost"),
    )
    assert any("does not exist in the source registry" in issue for issue in issues)


def test_c1_t03_approved_mapping_referencing_official_notice_is_rejected(tmp_path):
    source = _synthetic_approved_source(source_type="OFFICIAL_NOTICE")
    issues = _approval_issues(tmp_path, source)
    assert any("not eligible for approval" in issue for issue in issues)


def test_c1_t04_approved_mapping_referencing_application_output_is_rejected(tmp_path):
    source = _synthetic_approved_source(
        source_type="CURRENT_APPLICATION_OUTPUT", source_level=None
    )
    issues = _approval_issues(tmp_path, source)
    assert any("not eligible for approval" in issue for issue in issues)


def test_c1_t05_approved_mapping_referencing_level_c_source_is_rejected(tmp_path):
    source = _synthetic_approved_source(source_level="C")
    issues = _approval_issues(tmp_path, source)
    assert any("source_level" in issue for issue in issues)


def test_c1_t06_approved_mapping_with_invalid_source_id_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(approved_source_id=123),
    )
    assert any("approved_source_id" in issue for issue in issues)


def test_c1_t07_other_verified_candidate_does_not_authorize_selected_source(tmp_path):
    """A verified sibling candidate must not authorise an ineligible selected one."""
    good = _synthetic_approved_source()
    bad = _valid_source(source_id="weak-source", verification_status="ANNOUNCEMENT_VERIFIED")
    mapping = _approved_mapping(
        candidate_source_ids=[SYNTHETIC_SOURCE_ID, "weak-source"],
        approved_source_id="weak-source",
    )
    issues = _issues(tmp_path, [good, bad], _fixture_mappings(mapping))
    assert any("approved source 'weak-source' is not eligible" in issue for issue in issues)


# --- C2: source verification and review dependencies -------------------------


@pytest.mark.parametrize(
    "verification_status",
    ["DISCOVERED", "ANNOUNCEMENT_VERIFIED", "SOURCE_FILE_VERIFIED",
     "CONTENT_REVIEWED", "MAPPING_REVIEWED", "REJECTED", "UNAVAILABLE"],
)
def test_c2_source_below_approved_state_cannot_support_approval(tmp_path, verification_status):
    """C2-T01..T06: only APPROVED_FOR_ADAPTATION may back an approved mapping."""
    source = _synthetic_approved_source(verification_status=verification_status)
    issues = _approval_issues(tmp_path, source)
    assert any("not eligible for approval" in issue for issue in issues)


def test_c2_t07_hash_alone_does_not_authorize_approval(tmp_path):
    source = _synthetic_approved_source(
        verification_status="SOURCE_FILE_VERIFIED",
        content_hash_if_verified=SYNTHETIC_HASH,
        legal_or_copyright_review_status="NOT_REVIEWED",
        content_review_evidence=None,
        mapping_review_evidence=None,
        legal_content_review_evidence=None,
        approval_evidence=None,
    )
    issues = _approval_issues(tmp_path, source)
    assert any("not eligible for approval" in issue for issue in issues)


def test_c2_t08_approved_source_with_incomplete_review_metadata_is_rejected(tmp_path):
    source = _synthetic_approved_source(mapping_review_evidence=None)
    issues = _approval_issues(tmp_path, source)
    assert any("mapping_review_evidence" in issue for issue in issues)


@pytest.mark.parametrize("legal_review", ["NOT_REVIEWED", "IN_PROGRESS", "PENDING", "REJECTED", "NOT_APPLICABLE"])
def test_c2_t09_incomplete_legal_review_cannot_support_approval(tmp_path, legal_review):
    source = _synthetic_approved_source(legal_or_copyright_review_status=legal_review)
    issues = _approval_issues(tmp_path, source)
    assert any("legal/content review is not completed" in issue for issue in issues)


# --- C3: mapping / approval status consistency -------------------------------


@pytest.mark.parametrize(
    "mapping_status,approval_status",
    [
        ("APPROVED", "NOT_REQUESTED"),
        ("APPROVED", "PENDING"),
        ("APPROVED", "REJECTED"),
        ("UNVERIFIED", "APPROVED"),
        ("CANDIDATE_SOURCE_IDENTIFIED", "APPROVED"),
        ("MAPPING_REVIEWED", "APPROVED"),
        ("NO_OFFICIAL_SOURCE_IDENTIFIED", "APPROVED"),
        ("REJECTED", "APPROVED"),
    ],
)
def test_c3_contradictory_status_combinations_are_rejected(tmp_path, mapping_status, approval_status):
    """C3-T02..T09: the two status fields must agree."""
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(mapping_status=mapping_status, approval_status=approval_status),
    )
    assert any("inconsistent" in issue for issue in issues)


def test_c3_t10_existing_unapproved_mappings_remain_valid(tmp_path):
    issues = _issues(tmp_path, [_valid_source()], _all_mappings())
    assert issues == []


# --- C4: approval evidence integrity ----------------------------------------


def test_c4_t01_missing_approval_date_is_rejected(tmp_path):
    mapping = _approved_mapping()
    del mapping["approval_date"]
    issues = _approval_issues(tmp_path, _synthetic_approved_source(), approved=mapping)
    assert any("approval_date" in issue for issue in issues)


def test_c4_t02_invalid_approval_date_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path, _synthetic_approved_source(), approved=_approved_mapping(approval_date="2025-13-45")
    )
    assert any("approval_date" in issue for issue in issues)


def test_c4_t03_missing_reviewer_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path, _synthetic_approved_source(), approved=_approved_mapping(approved_by_or_review_role="")
    )
    assert any("approved_by_or_review_role" in issue for issue in issues)


def test_c4_t04_missing_approval_evidence_is_rejected(tmp_path):
    mapping = _approved_mapping()
    del mapping["approval_evidence"]
    issues = _approval_issues(tmp_path, _synthetic_approved_source(), approved=mapping)
    assert any("approval_evidence" in issue for issue in issues)


def test_c4_t05_whitespace_only_evidence_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path, _synthetic_approved_source(), approved=_approved_mapping(approval_evidence="   \n\t ")
    )
    assert any("approval_evidence" in issue for issue in issues)


def test_c4_t06_non_string_approval_evidence_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path, _synthetic_approved_source(), approved=_approved_mapping(approval_evidence={"a": 1})
    )
    assert any("approval_evidence" in issue for issue in issues)


def test_c4_t07_missing_selected_approved_source_is_rejected(tmp_path):
    mapping = _approved_mapping(candidate_source_ids=[SYNTHETIC_SOURCE_ID])
    del mapping["approved_source_id"]
    issues = _approval_issues(tmp_path, _synthetic_approved_source(), approved=mapping)
    assert any("approved_source_id" in issue for issue in issues)


def test_c4_t08_approved_source_not_among_candidates_is_rejected(tmp_path):
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(candidate_source_ids=["some-other-candidate"]),
    )
    assert any("not among candidate_source_ids" in issue for issue in issues)


def test_c4_t09_reused_review_evidence_is_rejected(tmp_path):
    same = "One generic string reused for every stage"
    source = _synthetic_approved_source(
        content_review_evidence=same,
        mapping_review_evidence=same,
        legal_content_review_evidence=same,
        approval_evidence=same,
    )
    issues = _approval_issues(tmp_path, source)
    assert any("not distinct across review stages" in issue for issue in issues)


# --- structural / defensive checks -------------------------------------------


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


def test_invalid_legal_review_status_is_rejected(tmp_path):
    issues = _issues(tmp_path, [_valid_source(legal_or_copyright_review_status="MAYBE")], _all_mappings())
    assert any("invalid legal_or_copyright_review_status" in issue for issue in issues)


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
    mappings = [m for m in _all_mappings()
                if not (m["case_type"] == "divorce" and m["document_type"] == "evidence_list")]
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
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(
            approved_by_or_review_role="",
            approval_evidence="",
        ),
    )
    assert any("approval claimed without documented" in issue for issue in issues)


def test_invalid_date_is_rejected(tmp_path):
    issues = _issues(tmp_path, [_valid_source(publication_date="2025-13-45")], _all_mappings())
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


def test_validator_does_not_crash_on_malformed_approval_metadata(tmp_path):
    """Defensive: malformed values must be reported, not raise."""
    issues = _approval_issues(
        tmp_path,
        _synthetic_approved_source(),
        approved=_approved_mapping(
            approved_source_id=["not", "a", "string"],
            approved_by_or_review_role=42,
            approval_date=20261010,
            approval_evidence=None,
        ),
    )
    assert issues, "malformed approval metadata must be reported"
