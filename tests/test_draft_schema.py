# File: tests/test_draft_schema.py
# Purpose: Draft schema registry, strict validation and JSON codec contract.
# Encoding: UTF-8
"""The draft document is the only thing storage ever encrypts, so its
validation is the security boundary for everything below it.

These tests pin three properties:

* the field registry describes *every* supported case type and points at real
  wizard widgets and real registered field identifiers (no invented names);
* every structural deviation - unknown version, unknown case type, unknown or
  missing key, wrong type, out-of-range collection, contradictory evidence
  state - is rejected instead of coerced;
* error messages never echo user content, so they can be shown or logged.
"""

import json

import pytest

from drafts import schema
from drafts.errors import DraftFileTooLargeError, DraftValidationError
from helpers import make_wizard, select_case
from presenters.model_builder import SUPPORTED_CASE_TYPES
from views.draft_io import CLAIM_PAGE_ATTR_BY_CASE, capture_draft


def _blank_payload(case_type):
    """A minimal but structurally complete payload for *case_type*."""
    flags = {}
    for name in schema.FLAG_FIELDS[case_type]:
        # Binary confirmations have no "unknown" option in the UI, so their
        # neutral value is False; tri-state ones start unconfirmed.
        flags[name] = False if name in schema.BINARY_FLAGS else None
    return {
        "schema_version": schema.SCHEMA_VERSION,
        "case_type": case_type,
        "fields": {spec.key: "" for spec in schema.TEXT_FIELDS[case_type]},
        "parties": {"plaintiffs": [], "defendants": []},
        "factual_flags": flags,
        "evidence": {"state": "NOT_INITIALIZED", "rows": []},
        "resume_page": "welcome",
    }


def _loan_payload(**overrides):
    payload = _blank_payload("loan")
    payload["fields"]["loan_date"] = "2023年1月1日"
    payload["factual_flags"]["has_iou"] = True
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------- #
# Registry integrity
# --------------------------------------------------------------------------- #


def test_registry_covers_every_supported_case_type():
    assert set(schema.TEXT_FIELDS) == set(schema.CASE_TYPES)
    assert set(schema.FLAG_FIELDS) == set(schema.CASE_TYPES)
    assert set(schema.CASE_TYPES) == set(SUPPORTED_CASE_TYPES)


def test_evidence_state_names_match_the_evidence_page(qapp):
    """The Qt-free schema must not drift from the page's own state machine."""
    wizard, _ = make_wizard()
    page = wizard.evidence_page
    page_states = (
        page.NOT_INITIALIZED,
        page.INITIALIZED_WITH_SUGGESTIONS,
        page.USER_MODIFIED,
        page.USER_EXPLICITLY_CLEARED,
    )
    assert set(page_states) == set(schema.EVIDENCE_STATES)


@pytest.mark.parametrize("case_type", schema.CASE_TYPES)
def test_every_field_key_is_a_registered_wizard_field(qapp, case_type):
    """A draft key must be an existing registration identifier, never a new one."""
    wizard, _ = make_wizard()
    for spec in schema.TEXT_FIELDS[case_type]:
        assert wizard.field(spec.key) is not None, spec.key


@pytest.mark.parametrize("case_type", schema.CASE_TYPES)
def test_every_widget_attribute_exists_on_the_owning_page(qapp, case_type):
    wizard, _ = make_wizard()
    page = getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])
    for spec in schema.TEXT_FIELDS[case_type]:
        assert hasattr(page, spec.widget), (case_type, spec.widget)


@pytest.mark.parametrize("case_type", schema.CASE_TYPES)
def test_captured_flags_match_the_declared_registry(qapp, case_type):
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    payload = capture_draft(wizard)
    assert payload["case_type"] == case_type
    assert set(payload["factual_flags"]) == set(schema.FLAG_FIELDS[case_type])


def test_tri_state_and_binary_flags_are_disjoint():
    assert set(schema.TRI_STATE_FLAGS).isdisjoint(schema.BINARY_FLAGS)
    declared = {name for names in schema.FLAG_FIELDS.values() for name in names}
    assert declared == set(schema.TRI_STATE_FLAGS) | set(schema.BINARY_FLAGS)


def test_resume_pages_match_the_wizard_page_names():
    from views.draft_io import PAGE_ATTR_BY_NAME

    assert set(schema.RESUME_PAGES) == set(PAGE_ATTR_BY_NAME)
    assert set(schema.CLAIM_PAGE_NAMES_BY_CASE.values()) <= set(schema.RESUME_PAGES)


# --------------------------------------------------------------------------- #
# Accepted documents
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case_type", schema.CASE_TYPES)
def test_minimal_payload_for_every_case_type_is_accepted(case_type):
    document = schema.validate_document(_blank_payload(case_type))
    assert document.case_type == case_type
    assert document.party_count() == 0
    assert document.evidence_rows == ()


def test_validation_preserves_insertion_order_and_values():
    document = schema.validate_document(_loan_payload())
    assert list(document.fields) == [spec.key for spec in schema.TEXT_FIELDS["loan"]]
    assert document.fields["loan_date"] == "2023年1月1日"
    assert document.factual_flags["has_iou"] is True


def test_empty_strings_and_blank_parties_are_valid_content():
    payload = _blank_payload("divorce")
    payload["parties"]["plaintiffs"] = [
        {
            "name": "",
            "id_number": "",
            "address": "",
            "phone": "",
            "is_company": False,
            "credit_code": "",
            "legal_representative": "",
        }
    ]
    document = schema.validate_document(payload)
    assert document.plaintiffs[0]["name"] == ""


# --------------------------------------------------------------------------- #
# Structural rejections
# --------------------------------------------------------------------------- #


def test_unknown_case_type_is_rejected():
    payload = _loan_payload(case_type="traffic")
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_unknown_schema_version_is_rejected():
    payload = _loan_payload(schema_version=2)
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_boolean_schema_version_is_not_an_integer_version():
    payload = _loan_payload(schema_version=True)
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_missing_top_level_key_is_rejected():
    payload = _loan_payload()
    payload.pop("resume_page")
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_extra_top_level_key_is_rejected():
    payload = _loan_payload()
    payload["notes"] = "x"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_missing_case_field_is_rejected():
    payload = _loan_payload()
    payload["fields"].pop("court_name")
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_unknown_case_field_is_rejected():
    payload = _loan_payload()
    payload["fields"]["c_contract_date"] = "2023-01-01"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_non_string_field_value_is_rejected():
    payload = _loan_payload()
    payload["fields"]["principal"] = 50000
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_over_long_field_value_is_rejected():
    payload = _loan_payload()
    payload["fields"]["loan_reason"] = "长" * (schema.TEXT_LIMIT + 1)
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_control_characters_in_a_field_are_rejected():
    payload = _loan_payload()
    payload["fields"]["loan_reason"] = "资金\x00周转"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_lone_surrogate_in_a_field_is_rejected():
    payload = _loan_payload()
    payload["fields"]["loan_reason"] = "\ud800"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_numeric_field_rejects_non_numeric_text():
    payload = _loan_payload()
    payload["fields"]["principal"] = "五万元"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_numeric_field_accepts_decimal_text_and_empty():
    payload = _loan_payload()
    payload["fields"]["principal"] = "50000.50"
    assert schema.validate_document(payload).fields["principal"] == "50000.50"
    payload["fields"]["principal"] = ""
    assert schema.validate_document(payload).fields["principal"] == ""


def test_too_many_parties_are_rejected():
    payload = _blank_payload("loan")
    payload["parties"]["plaintiffs"] = [
        {
            "name": "原告",
            "id_number": "",
            "address": "",
            "phone": "",
            "is_company": False,
            "credit_code": "",
            "legal_representative": "",
        }
        for _ in range(schema.MAX_PARTIES_PER_SIDE + 1)
    ]
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_party_record_requires_the_exact_key_set():
    payload = _blank_payload("loan")
    payload["parties"]["plaintiffs"] = [{"name": "原告甲"}]
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_party_is_company_must_be_boolean():
    payload = _blank_payload("loan")
    payload["parties"]["plaintiffs"] = [
        {
            "name": "原告甲",
            "id_number": "",
            "address": "",
            "phone": "",
            "is_company": "yes",
            "credit_code": "",
            "legal_representative": "",
        }
    ]
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_tri_state_flag_accepts_true_false_and_null():
    for value in (True, False, None):
        payload = _loan_payload()
        payload["factual_flags"]["has_iou"] = value
        assert schema.validate_document(payload).factual_flags["has_iou"] is value


def test_tri_state_flag_rejects_a_non_boolean_value():
    payload = _loan_payload()
    payload["factual_flags"]["has_iou"] = "unknown"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_binary_flag_rejects_null():
    payload = _blank_payload("labor")
    payload["factual_flags"]["is_no_contract"] = None
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_unknown_resume_page_is_rejected():
    payload = _loan_payload(resume_page="PAGE_LOAN_CLAIM")
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_unknown_evidence_state_is_rejected():
    payload = _loan_payload()
    payload["evidence"]["state"] = "MAYBE"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_too_many_evidence_rows_are_rejected():
    payload = _loan_payload()
    payload["evidence"] = {
        "state": "USER_MODIFIED",
        "rows": [
            {"name": "证据", "target": "", "suggested": False}
            for _ in range(schema.MAX_EVIDENCE_ROWS + 1)
        ],
    }
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_evidence_row_requires_the_exact_key_set():
    payload = _loan_payload()
    payload["evidence"] = {"state": "USER_MODIFIED", "rows": [{"name": "证据"}]}
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_evidence_row_suggested_must_be_boolean():
    payload = _loan_payload()
    payload["evidence"] = {
        "state": "USER_MODIFIED",
        "rows": [{"name": "证据", "target": "", "suggested": 1}],
    }
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


@pytest.mark.parametrize("state", schema.EMPTY_EVIDENCE_STATES)
def test_empty_evidence_states_may_not_carry_rows(state):
    payload = _loan_payload()
    payload["evidence"] = {
        "state": state,
        "rows": [{"name": "证据", "target": "", "suggested": False}],
    }
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_validation_errors_do_not_echo_user_content():
    secret = "机密姓名测试甲"
    payload = _blank_payload("loan")
    payload["parties"]["plaintiffs"] = [
        {
            "name": secret,
            "id_number": "示例证件号",
            "address": "",
            "phone": "",
            "is_company": False,
            "credit_code": "",
            "legal_representative": "",
        }
    ]
    payload["fields"]["principal"] = secret
    with pytest.raises(DraftValidationError) as excinfo:
        schema.validate_document(payload)
    message = str(excinfo.value)
    assert secret not in message
    assert "示例证件号" not in message


# --------------------------------------------------------------------------- #
# JSON codec
# --------------------------------------------------------------------------- #


def test_json_codec_round_trip_preserves_the_document():
    document = schema.validate_document(_loan_payload())
    restored = schema.from_json_bytes(schema.to_json_bytes(document))
    assert restored == document


def test_json_serialization_is_deterministic():
    document = schema.validate_document(_loan_payload())
    assert schema.to_json_bytes(document) == schema.to_json_bytes(document)


def test_json_serialization_keeps_chinese_text_readable():
    document = schema.validate_document(_loan_payload())
    raw = schema.to_json_bytes(document)
    assert "2023年1月1日".encode("utf-8") in raw
    assert b"\\u" not in raw


def test_json_rejects_duplicate_keys():
    raw = (
        b'{"schema_version":1,"schema_version":1,"case_type":"loan","fields":{},'
        b'"parties":{"plaintiffs":[],"defendants":[]},"factual_flags":{},'
        b'"evidence":{"state":"NOT_INITIALIZED","rows":[]},"resume_page":"welcome"}'
    )
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(raw)


def test_json_rejects_nan_and_infinity():
    payload = json.dumps(_loan_payload(), ensure_ascii=False)
    payload = payload.replace('"loan_date": "2023年1月1日"', '"loan_date": NaN')
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(payload.encode("utf-8"))


def test_json_rejects_invalid_utf8():
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(b"\xff\xfe{}")


def test_json_rejects_a_byte_order_mark():
    raw = b"\xef\xbb\xbf" + schema.to_json_bytes(schema.validate_document(_loan_payload()))
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(raw)


def test_json_rejects_malformed_text():
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(b"not json at all")


def test_json_rejects_empty_input():
    with pytest.raises(DraftValidationError):
        schema.from_json_bytes(b"")


def test_oversized_json_document_is_rejected():
    oversized = b"{" + b" " * (schema.MAX_DOCUMENT_BYTES + 1) + b"}"
    with pytest.raises(DraftFileTooLargeError):
        schema.from_json_bytes(oversized)


def test_only_validated_documents_can_be_serialized():
    with pytest.raises(DraftValidationError):
        schema.to_json_bytes({"case_type": "loan"})
