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
    # Every confirmation is tri-state and starts unconfirmed.
    flags = {name: None for name in schema.FLAG_FIELDS[case_type]}
    return {
        "schema_version": schema.SCHEMA_VERSION,
        "case_type": case_type,
        "fields": {spec.key: "" for spec in schema.TEXT_FIELDS[case_type]},
        "parties": {"plaintiffs": [], "defendants": []},
        "factual_flags": flags,
        "evidence": {"state": "NOT_INITIALIZED", "rows": []},
        "resume_page": "welcome",
        "agent": None,
    }


def _loan_payload(**overrides):
    payload = _blank_payload("loan")
    payload["fields"]["loan_date"] = "2023年1月1日"
    payload["factual_flags"]["has_iou"] = True
    payload.update(overrides)
    return payload


def _strip_v5_fields(payload):
    """Remove the optional supplement fields so a payload matches pre-v5 shape."""
    case_type = payload.get("case_type")
    for spec in schema.TEXT_FIELDS.get(case_type, ()):
        if spec.widget in ("extra_claims", "extra_facts"):
            payload["fields"].pop(spec.key, None)
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


def test_every_declared_flag_is_tri_state_or_classification():
    declared = {name for names in schema.FLAG_FIELDS.values() for name in names}
    assert declared == set(schema.TRI_STATE_FLAGS) | set(schema.STRING_FLAGS)
    assert not (set(schema.TRI_STATE_FLAGS) & set(schema.STRING_FLAGS))


def test_string_classifications_accept_only_known_vocabulary():
    from utils.labor_security import LABOR_PROCEDURES, LABOR_REFUSAL_GROUNDS, LABOR_ROLES

    assert schema.STRING_FLAG_VALUES["labor_procedure"] == LABOR_PROCEDURES
    assert schema.STRING_FLAG_VALUES["labor_refusal_ground"] == LABOR_REFUSAL_GROUNDS
    assert schema.STRING_FLAG_VALUES["labor_role"] == LABOR_ROLES


def test_string_classification_rejects_an_unknown_value():
    payload = _blank_payload("labor")
    payload["factual_flags"]["labor_procedure"] = "already_sued"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


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
            "gender": "",
            "birth_date": "",
            "ethnicity": "",
            "ethnicity_other": "",
            "occupation": "",
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
    payload = _loan_payload(schema_version=schema.SCHEMA_VERSION + 1)
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


def test_labor_flags_accept_the_unconfirmed_state():
    payload = _blank_payload("labor")
    document = schema.validate_document(payload)
    assert document.factual_flags == {
        "labor_procedure": None,
        "labor_refusal_ground": None,
        "labor_role": None,
        "labor_delay_exception": None,
        "is_no_contract": None,
    }


def test_string_classifications_survive_as_stored():
    from utils.labor_security import (
        GROUND_OTHER_OR_UNSTATED,
        PROCEDURE_NOT_ACCEPTED,
        ROLE_EMPLOYEE,
    )

    payload = _blank_payload("labor")
    payload["factual_flags"]["labor_procedure"] = PROCEDURE_NOT_ACCEPTED
    payload["factual_flags"]["labor_refusal_ground"] = GROUND_OTHER_OR_UNSTATED
    payload["factual_flags"]["labor_role"] = ROLE_EMPLOYEE
    payload["factual_flags"]["labor_delay_exception"] = False
    document = schema.validate_document(payload)
    assert document.factual_flags["labor_procedure"] == PROCEDURE_NOT_ACCEPTED
    assert document.factual_flags["labor_refusal_ground"] == GROUND_OTHER_OR_UNSTATED
    assert document.factual_flags["labor_role"] == ROLE_EMPLOYEE
    assert document.factual_flags["labor_delay_exception"] is False


def _version_two_labor_payload(has_arbitrated, receipt_date="2024-06-01"):
    """A structurally complete v2 labour payload (pre-classification shape)."""
    fields = {
        spec.key: ""
        for spec in schema.TEXT_FIELDS["labor"]
        if spec.key not in ("l_arb_application_date", "l_arb_acceptance_date")
        and spec.widget not in ("extra_claims", "extra_facts")
    }
    fields["l_arb_commission"] = "示例劳动人事争议仲裁委员会"
    fields["l_arb_receipt_date"] = receipt_date
    return {
        "schema_version": 2,
        "case_type": "labor",
        "fields": fields,
        "parties": {"plaintiffs": [], "defendants": []},
        "factual_flags": {"has_arbitrated": has_arbitrated, "is_no_contract": None},
        "evidence": {"state": "NOT_INITIALIZED", "rows": []},
        "resume_page": "party",
    }


def test_version_two_confirmed_arbitration_never_becomes_a_verified_award():
    """A legacy ``True`` never recorded WHICH document was received, so it must
    land in the review-required state instead of an award/mediation class."""
    document = schema.validate_document(_version_two_labor_payload(True))
    assert document.schema_version == schema.SCHEMA_VERSION
    assert document.factual_flags["labor_procedure"] == "other_or_uncertain"
    assert document.factual_flags["labor_role"] is None
    assert document.factual_flags["labor_refusal_ground"] is None
    assert document.factual_flags["labor_delay_exception"] is None
    # The legacy receipt date survives verbatim; nothing is fabricated.
    assert document.fields["l_arb_receipt_date"] == "2024-06-01"
    assert document.fields["l_arb_application_date"] == ""
    assert document.fields["l_arb_acceptance_date"] == ""
    from utils.labor_security import evaluate_labor_eligibility

    eligibility = evaluate_labor_eligibility(
        document.factual_flags["labor_procedure"],
        commission=document.fields["l_arb_commission"],
        receipt_date=document.fields["l_arb_receipt_date"],
    )
    assert not eligibility.eligible


def test_version_two_not_yet_applied_maps_to_not_applied():
    document = schema.validate_document(_version_two_labor_payload(False))
    assert document.factual_flags["labor_procedure"] == "not_applied"


def test_version_two_unconfirmed_stays_unconfirmed():
    document = schema.validate_document(_version_two_labor_payload(None))
    assert document.factual_flags["labor_procedure"] is None


def test_version_two_document_already_carrying_classification_is_rejected():
    payload = _version_two_labor_payload(True)
    payload["factual_flags"]["labor_procedure"] = "non_final_award"
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_version_two_labor_payload_missing_the_posture_flag_is_rejected():
    payload = _version_two_labor_payload(True)
    del payload["factual_flags"]["has_arbitrated"]
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def _version_one_labor_payload(is_no_contract):
    payload = _blank_payload("labor")
    payload["schema_version"] = 1
    # A true legacy document predates the v4 agent key; carrying it would be
    # structural drift and must be rejected (pinned by its own test).
    del payload["agent"]
    for key in (
        "l_arb_commission",
        "l_arb_case_no",
        "l_arb_receipt_date",
        "l_arb_application_date",
        "l_arb_acceptance_date",
    ):
        del payload["fields"][key]
    payload["factual_flags"] = {"is_no_contract": is_no_contract}
    payload["fields"]["l_job_title"] = "示例岗位"
    _strip_v5_fields(payload)
    return payload


def test_version_one_labor_draft_is_migrated():
    document = schema.validate_document(_version_one_labor_payload(True))
    assert document.schema_version == schema.SCHEMA_VERSION
    assert document.fields["l_job_title"] == "示例岗位"
    assert document.fields["l_arb_commission"] == ""
    assert document.fields["l_arb_application_date"] == ""
    assert document.factual_flags["labor_procedure"] is None
    assert document.factual_flags["labor_role"] is None
    assert document.factual_flags["is_no_contract"] is True


def test_version_one_binary_default_becomes_unconfirmed():
    """A v1 ``False`` was the binary control's untouched default, not a choice."""
    document = schema.validate_document(_version_one_labor_payload(False))
    assert document.factual_flags["is_no_contract"] is None


def test_version_one_migration_does_not_mutate_the_input():
    payload = _version_one_labor_payload(True)
    snapshot = json.dumps(payload, sort_keys=True)
    schema.validate_document(payload)
    assert json.dumps(payload, sort_keys=True) == snapshot


def test_version_one_document_already_carrying_new_keys_is_rejected():
    payload = _version_one_labor_payload(True)
    payload["factual_flags"]["has_arbitrated"] = True
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_version_one_non_labor_draft_is_migrated_unchanged():
    payload = _loan_payload(schema_version=1)
    del payload["agent"]  # legacy documents predate the v4 agent key
    _strip_v5_fields(payload)
    document = schema.validate_document(payload)
    assert document.schema_version == schema.SCHEMA_VERSION
    assert document.fields["loan_date"] == "2023年1月1日"
    assert document.factual_flags == {"has_iou": True}


# --------------------------------------------------------------------------- #
# Version 3 -> 4: party detail keys and the optional agent record
# --------------------------------------------------------------------------- #


def test_version_three_draft_gains_party_details_and_blank_agent():
    """A v3 draft migrates: every party record fills the detail keys blank and
    the agent record starts as ``None`` (section closed). No value is guessed."""
    payload = _blank_payload("loan")
    payload["schema_version"] = 3
    del payload["agent"]
    _strip_v5_fields(payload)
    payload["parties"]["plaintiffs"] = [
        {
            "name": "张三（测试）",
            "id_number": "",
            "address": "",
            "phone": "",
            "credit_code": "",
            "legal_representative": "",
            "is_company": False,
        }
    ]
    document = schema.validate_document(payload)
    assert document.schema_version == schema.SCHEMA_VERSION
    record = document.plaintiffs[0]
    for key in ("gender", "birth_date", "ethnicity", "ethnicity_other", "occupation"):
        assert record[key] == ""
    assert document.agent is None
    # The legacy record's own content is untouched.
    assert record["name"] == "张三（测试）"
    assert record["is_company"] is False


def test_version_three_document_already_carrying_agent_is_rejected():
    payload = _blank_payload("loan")
    payload["schema_version"] = 3
    del payload["agent"]
    payload["agent"] = None
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


# --------------------------------------------------------------------------- #
# Version 4 -> 5: optional user-supplied claim/fact fields
# --------------------------------------------------------------------------- #


def test_version_four_draft_gains_blank_supplement_fields():
    payload = _loan_payload()
    payload["schema_version"] = 4
    _strip_v5_fields(payload)
    document = schema.validate_document(payload)
    assert document.schema_version == schema.SCHEMA_VERSION
    assert document.fields["loan_extra_claims"] == ""
    assert document.fields["loan_extra_facts"] == ""


def test_version_four_draft_already_carrying_supplement_fields_is_rejected():
    payload = _loan_payload()
    payload["schema_version"] = 4
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_agent_record_survives_validation_and_round_trip():
    payload = _loan_payload()
    payload["agent"] = {"name": "王五（测试）", "type": "律师", "org": "示例律所", "phone": ""}
    document = schema.validate_document(payload)
    assert document.agent == {"name": "王五（测试）", "type": "律师", "org": "示例律所", "phone": ""}
    restored = schema.from_json_bytes(schema.to_json_bytes(document))
    assert restored.agent == document.agent


def test_agent_without_a_stated_role_is_valid():
    payload = _loan_payload()
    payload["agent"] = {"name": "王五（测试）", "type": "", "org": "", "phone": ""}
    document = schema.validate_document(payload)
    assert document.agent["type"] == ""


def test_agent_with_unknown_role_is_rejected():
    payload = _loan_payload()
    payload["agent"] = {"name": "王五（测试）", "type": "顾问", "org": "", "phone": ""}
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_agent_with_extra_key_is_rejected():
    payload = _loan_payload()
    payload["agent"] = {"name": "", "type": "", "org": "", "phone": "", "id": ""}
    with pytest.raises(DraftValidationError):
        schema.validate_document(payload)


def test_current_document_missing_agent_is_rejected():
    payload = _loan_payload()
    del payload["agent"]
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
