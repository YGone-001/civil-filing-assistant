# File: drafts/schema.py
# Purpose: Versioned, strictly validated draft document (no Qt, no widgets).
# Encoding: UTF-8
"""The validated draft document contract.

A draft is *not* an export model. ``presenters.model_builder.build_case_model``
produces an export-oriented object whose job is to render documents; a draft
must instead preserve exactly what the user typed - including incomplete
parties, blank optional fields, unresolved confirmations and a deliberately
emptied evidence list - so the wizard can be rebuilt pixel-for-pixel on the
next launch.

The document is therefore a flat, explicit, versioned record:

* ``fields``        - the case-specific text inputs, keyed by their existing
                      wizard field identifiers (never renamed here), including
                      the optional user-supplied claims/facts additions;
* ``parties``       - ordered plaintiff/defendant records, blank cards included;
* ``factual_flags`` - tri-state confirmations where ``None`` means "unconfirmed";
* ``evidence``      - the row list plus the page's own state label;
* ``resume_page``   - a stable *page name*, never a numeric Qt page id;
* ``agent``         - the optional litigation agent record, ``None`` while the
                      party page's agent section stays closed.

Deliberately excluded: generated DOCX content, rendered claims/facts, derived
calculation results, the contract calculator provenance, temporary paths,
runtime object identities and any application secret. Excluding the
provenance is a security decision, not an omission: a restored amount has not
been recomputed, so it must fall back to the neutral "manual amount" wording
(see :mod:`views.draft_io`).

Validation is strict. Unknown keys, missing keys, unknown case types,
unknown schema versions and out-of-range collections are all rejected; nothing
is coerced or defaulted. The single exception is the explicit, versioned
migration of an older schema (see :func:`_migrate`), which runs before the
strict validation of the current version.
"""

import json
from dataclasses import dataclass
from typing import Optional

from drafts.errors import DraftFileTooLargeError, DraftValidationError
from drafts.storage import MAX_PLAINTEXT_BYTES
from models.case_model import (
    AGENT_TYPES,
    RENTAL_LEASE_STATUSES,
    RENTAL_PAYMENT_STATUSES,
    SERVICE_ADDRESS_SOURCES,
)
from utils.labor_security import (
    LABOR_PROCEDURES,
    LABOR_REFUSAL_GROUNDS,
    LABOR_ROLES,
)

#: Version of the *inner* JSON document (independent of the envelope version).
SCHEMA_VERSION = 8

#: Older inner-document versions that :func:`_migrate` can upgrade.
MIGRATABLE_VERSIONS = (1, 2, 3, 4, 5, 6, 7)

#: Case categories this build can restore. Mirrors
#: ``presenters.model_builder.SUPPORTED_CASE_TYPES`` and is asserted equal there.
CASE_TYPES = ("loan", "contract", "property", "labor", "divorce", "rental")

#: Stable page names used by ``resume_page`` (never numeric Qt ids).
RESUME_PAGES = (
    "welcome",
    "case_selection",
    "party",
    "loan_claim",
    "contract_claim",
    "property_claim",
    "labor_claim",
    "divorce_claim",
    "rental_claim",
    "evidence",
    "export",
)

#: The evidence page's four states, duplicated here so the storage contract
#: stays Qt-free. ``views.pages.evidence`` owns the same names; a test asserts
#: the two definitions cannot drift.
EVIDENCE_STATES = (
    "NOT_INITIALIZED",
    "INITIALIZED_WITH_SUGGESTIONS",
    "USER_MODIFIED",
    "USER_EXPLICITLY_CLEARED",
)

#: States that may not carry any row, enforced on both save and load.
EMPTY_EVIDENCE_STATES = ("NOT_INITIALIZED", "USER_EXPLICITLY_CLEARED")

#: Bounds. Generous enough for real free-text input, small enough to keep a
#: hostile file from turning into a memory or UI problem.
TEXT_LIMIT = 2000
LONG_TEXT_LIMIT = 8000
NUMERIC_LIMIT = 40
MAX_PARTIES_PER_SIDE = 20
MAX_EVIDENCE_ROWS = 50
MAX_DOCUMENT_BYTES = MAX_PLAINTEXT_BYTES

PARTY_TEXT_LIMITS = {
    "name": 200,
    "id_number": 100,
    "address": 500,
    "phone": 50,
    "credit_code": 100,
    "legal_representative": 100,
    # Natural-person detail fields added in schema version 4. The party page
    # keeps the raw combo selection (``ethnicity`` may literally be "其他")
    # and the free-text companion; the presenter resolves the pair into the
    # model's final ethnicity, so the draft must store both verbatim.
    "gender": 10,
    "birth_date": 20,
    "ethnicity": 30,
    "ethnicity_other": 30,
    "occupation": 100,
    "service_address_source": 40,
}
PARTY_KEYS = tuple(PARTY_TEXT_LIMITS) + ("is_company",)

#: Party record keys that schema version 4 introduced; migration fills them
#: blank instead of guessing any value.
_PARTY_KEYS_ADDED_IN_V4 = ("gender", "birth_date", "ethnicity", "ethnicity_other", "occupation")

#: Party record key introduced in version 7; old drafts never asked for it and
#: are migrated to the safe "unconfirmed" source.
_PARTY_KEY_ADDED_IN_V7 = "service_address_source"

EVIDENCE_TEXT_LIMITS = {"name": 500, "target": 1000}

#: Top-level keys up to version 3. Version 4 appended ``agent``; the strict
#: top-level key check must run against the document's own version so legacy
#: drafts reach :func:`_migrate` instead of being rejected up front.
_DOCUMENT_KEYS_V3 = (
    "schema_version",
    "case_type",
    "fields",
    "parties",
    "factual_flags",
    "evidence",
    "resume_page",
)

_DOCUMENT_KEYS = _DOCUMENT_KEYS_V3 + ("agent",)

#: Agent record contract: ``None`` (section never opened) or a complete
#: four-key record. An empty string for ``type`` means "no role stated".
_AGENT_KEYS = ("name", "type", "org", "phone")
_AGENT_TEXT_LIMITS = {"name": 100, "type": 20, "org": 200, "phone": 50}

_PARTY_GROUP_KEYS = ("plaintiffs", "defendants")
_EVIDENCE_KEYS = ("state", "rows")

#: Confirmations whose third state (``None`` = 未确认) is meaningful.
TRI_STATE_FLAGS = (
    "has_iou",
    "has_repayment",
    "is_delivered",
    "is_signed",
    "labor_delay_exception",
    "is_no_contract",
    "property_returned",
)

#: Classification fields stored as ``None`` (unconfirmed) or one of the
#: vocabulary strings owned by :mod:`utils.labor_security` (imported, so the
#: two can never drift).
STRING_FLAGS = (
    "labor_procedure",
    "labor_refusal_ground",
    "labor_role",
    "lease_status",
    "payment_status",
)

#: Allowed values per string classification flag.
STRING_FLAG_VALUES = {
    "labor_procedure": LABOR_PROCEDURES,
    "labor_refusal_ground": LABOR_REFUSAL_GROUNDS,
    "labor_role": LABOR_ROLES,
    "lease_status": RENTAL_LEASE_STATUSES,
    "payment_status": RENTAL_PAYMENT_STATUSES,
}

#: Case type -> the page name that owns its claim inputs.
CLAIM_PAGE_NAMES_BY_CASE = {
    "loan": "loan_claim",
    "contract": "contract_claim",
    "property": "property_claim",
    "labor": "labor_claim",
    "divorce": "divorce_claim",
    "rental": "rental_claim",
}

__all__ = [
    "CASE_TYPES",
    "CLAIM_PAGE_NAMES_BY_CASE",
    "DraftDocument",
    "EVIDENCE_STATES",
    "FLAG_FIELDS",
    "FieldSpec",
    "MAX_DOCUMENT_BYTES",
    "PARTY_KEYS",
    "RESUME_PAGES",
    "SCHEMA_VERSION",
    "TEXT_FIELDS",
    "factual_flag_names",
    "from_json_bytes",
    "to_json_bytes",
    "validate_document",
]


@dataclass(frozen=True)
class FieldSpec:
    """One case-specific text input of the draft.

    ``key`` is the wizard field identifier already registered by the page, so
    the draft never invents a second naming scheme; ``widget`` is the page
    attribute that owns the value, which is what the UI adapter reads and
    writes.
    """

    key: str
    widget: str
    limit: int = TEXT_LIMIT
    numeric: bool = False


def _specs(entries):
    return tuple(
        FieldSpec(key, widget, limit, numeric) for key, widget, limit, numeric in entries
    )


#: Case-specific text inputs, in a fixed order. ``widget`` strips the page's
#: two-character registration prefix (``c_``, ``p_``, ``l_``, ``d_``).
TEXT_FIELDS = {
    "loan": _specs((
        ("loan_date", "loan_date", TEXT_LIMIT, False),
        ("loan_reason", "loan_reason", TEXT_LIMIT, False),
        ("principal", "principal", NUMERIC_LIMIT, True),
        ("payment_method", "payment_method", TEXT_LIMIT, False),
        ("rate", "rate", NUMERIC_LIMIT, True),
        ("start_date", "start_date", TEXT_LIMIT, False),
        ("demand_date", "demand_date", TEXT_LIMIT, False),
        ("demand_method", "demand_method", TEXT_LIMIT, False),
        ("loan_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("loan_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
        ("court_name", "court_name", TEXT_LIMIT, False),
    )),
    "contract": _specs((
        ("c_contract_date", "contract_date", TEXT_LIMIT, False),
        ("c_contract_name", "contract_name", TEXT_LIMIT, False),
        ("c_product_name", "product_name", TEXT_LIMIT, False),
        ("c_total_amount", "total_amount", NUMERIC_LIMIT, True),
        ("c_delivery_date", "delivery_date", TEXT_LIMIT, False),
        ("c_unpaid_amount", "unpaid_amount", NUMERIC_LIMIT, True),
        ("c_penalty_amount", "penalty_amount", NUMERIC_LIMIT, True),
        ("c_court_name", "court_name", TEXT_LIMIT, False),
        ("c_overdue_start", "overdue_start", TEXT_LIMIT, False),
        ("c_overdue_end", "overdue_end", TEXT_LIMIT, False),
        ("c_lpr_value", "lpr_value", NUMERIC_LIMIT, True),
        ("c_lpr_multiple", "lpr_multiple", NUMERIC_LIMIT, True),
        ("c_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("c_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
    )),
    "property": _specs((
        ("p_property_addr", "property_addr", TEXT_LIMIT, False),
        ("p_house_area", "house_area", NUMERIC_LIMIT, True),
        ("p_fee_rate", "fee_rate", NUMERIC_LIMIT, True),
        ("p_period_start", "period_start", TEXT_LIMIT, False),
        ("p_period_end", "period_end", TEXT_LIMIT, False),
        ("p_late_fee_logic", "late_fee_logic", TEXT_LIMIT, False),
        ("p_demand_record", "demand_record", LONG_TEXT_LIMIT, False),
        ("p_total_input", "total_input", NUMERIC_LIMIT, True),
        ("p_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("p_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
        ("p_court_name", "court_name", TEXT_LIMIT, False),
    )),
    "labor": _specs((
        ("l_emp_join_date", "emp_join_date", TEXT_LIMIT, False),
        ("l_job_title", "job_title", TEXT_LIMIT, False),
        ("l_monthly_salary", "monthly_salary", NUMERIC_LIMIT, True),
        ("l_unpaid_months", "unpaid_months", TEXT_LIMIT, False),
        ("l_emp_term_date", "emp_term_date", TEXT_LIMIT, False),
        ("l_overtime_hours", "overtime_hours", NUMERIC_LIMIT, True),
        ("l_overtime_pay", "overtime_pay", NUMERIC_LIMIT, True),
        ("l_social_sec_info", "social_sec_info", TEXT_LIMIT, False),
        ("l_court_name", "court_name", TEXT_LIMIT, False),
        ("l_arb_commission", "arb_commission", TEXT_LIMIT, False),
        ("l_arb_case_no", "arb_case_no", TEXT_LIMIT, False),
        ("l_arb_receipt_date", "arb_receipt_date", TEXT_LIMIT, False),
        ("l_arb_application_date", "arb_application_date", TEXT_LIMIT, False),
        ("l_arb_acceptance_date", "arb_acceptance_date", TEXT_LIMIT, False),
        ("l_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("l_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
    )),
    "divorce": _specs((
        ("d_marriage_date", "marriage_date", TEXT_LIMIT, False),
        ("d_child_name", "child_name", TEXT_LIMIT, False),
        ("d_child_birthday", "child_birthday", TEXT_LIMIT, False),
        ("d_custody_preference", "custody_preference", TEXT_LIMIT, False),
        ("d_support_monthly", "support_monthly", NUMERIC_LIMIT, True),
        ("d_divorce_reason", "divorce_reason", TEXT_LIMIT, False),
        ("d_separation_start_date", "separation_start_date", TEXT_LIMIT, False),
        ("d_asset_description", "asset_description", TEXT_LIMIT, False),
        ("d_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("d_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
        ("d_court_name", "court_name", TEXT_LIMIT, False),
    )),
    "rental": _specs((
        ("r_property_address", "property_address", TEXT_LIMIT, False),
        ("r_contract_date", "contract_date", TEXT_LIMIT, False),
        ("r_lease_start", "lease_start", TEXT_LIMIT, False),
        ("r_lease_end", "lease_end", TEXT_LIMIT, False),
        ("r_monthly_rent", "monthly_rent", NUMERIC_LIMIT, True),
        ("r_payment_cycle", "payment_cycle", TEXT_LIMIT, False),
        ("r_arrears_start", "arrears_start", TEXT_LIMIT, False),
        ("r_arrears_end", "arrears_end", TEXT_LIMIT, False),
        ("r_arrears_amount", "arrears_amount", NUMERIC_LIMIT, True),
        ("r_late_fee", "late_fee", NUMERIC_LIMIT, True),
        ("r_demand_record", "demand_record", LONG_TEXT_LIMIT, False),
        ("r_defendant_obligations", "defendant_obligations", LONG_TEXT_LIMIT, False),
        ("r_termination_date", "termination_date", TEXT_LIMIT, False),
        ("r_extra_claims", "extra_claims", LONG_TEXT_LIMIT, False),
        ("r_extra_facts", "extra_facts", LONG_TEXT_LIMIT, False),
        ("r_court_name", "court_name", TEXT_LIMIT, False),
    )),
}

#: Confirmations stored per case type, in a fixed order. Labour drafts carry
#: the procedural classification (state, refusal ground, party role, delay
#: exception) alongside the ordinary no-contract confirmation.
FLAG_FIELDS = {
    "loan": ("has_iou", "has_repayment"),
    "contract": ("is_delivered", "is_signed"),
    "property": (),
    "labor": (
        "labor_procedure",
        "labor_refusal_ground",
        "labor_role",
        "labor_delay_exception",
        "is_no_contract",
    ),
    "divorce": (),
    "rental": ("lease_status", "property_returned", "payment_status"),
}


def factual_flag_names(case_type):
    """Return the confirmation names stored for *case_type*."""
    return FLAG_FIELDS[case_type]


@dataclass(frozen=True)
class DraftDocument:
    """A fully validated, immutable-in-practice draft document."""

    case_type: str
    fields: dict
    plaintiffs: tuple
    defendants: tuple
    factual_flags: dict
    evidence_state: str
    evidence_rows: tuple
    resume_page: str
    agent: Optional[dict] = None
    schema_version: int = SCHEMA_VERSION

    def to_payload(self):
        """Return the wire representation (insertion ordered, no extra keys)."""
        return {
            "schema_version": self.schema_version,
            "case_type": self.case_type,
            "fields": dict(self.fields),
            "parties": {
                "plaintiffs": [dict(record) for record in self.plaintiffs],
                "defendants": [dict(record) for record in self.defendants],
            },
            "factual_flags": dict(self.factual_flags),
            "evidence": {
                "state": self.evidence_state,
                "rows": [dict(row) for row in self.evidence_rows],
            },
            "resume_page": self.resume_page,
            "agent": dict(self.agent) if self.agent is not None else None,
        }

    def party_count(self):
        return len(self.plaintiffs) + len(self.defendants)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise DraftValidationError(f"{label} 必须是对象。")
    return value


def _require_exact_keys(mapping, expected, label):
    """Reject any structural drift without echoing attacker-controlled keys."""
    if set(mapping) != set(expected):
        raise DraftValidationError(f"{label} 的字段集合不符合草稿格式。")


def _require_text(value, label, limit):
    if not isinstance(value, str):
        raise DraftValidationError(f"{label} 必须是字符串。")
    if len(value) > limit:
        raise DraftValidationError(f"{label} 超出允许的长度上限。")
    for char in value:
        code = ord(char)
        if code < 0x20 and char not in "\n\t":
            raise DraftValidationError(f"{label} 含有不支持的控制字符。")
        if 0xD800 <= code <= 0xDFFF:
            raise DraftValidationError(f"{label} 含有无效的 Unicode 代理字符。")
    return value


def _require_numeric(value, label):
    """Reject non-numeric text in a monetary/rate field.

    The UI validators already block such input; this check exists so a
    tampered file cannot inject arbitrary text into a numeric field. The
    authoritative parser is reused rather than re-implemented.
    """
    from models.calculations import CalculationError, parse_decimal

    try:
        parse_decimal(value, label)
    except CalculationError:
        raise DraftValidationError(f"{label} 不是有效数字。")


def _validate_fields(case_type, value):
    mapping = _require_mapping(value, "fields")
    specs = TEXT_FIELDS[case_type]
    _require_exact_keys(mapping, [spec.key for spec in specs], "fields")
    validated = {}
    for spec in specs:
        text = _require_text(mapping[spec.key], f"字段 {spec.key}", spec.limit)
        if spec.numeric:
            _require_numeric(text, f"字段 {spec.key}")
        validated[spec.key] = text
    return validated


def _validate_party_record(record, label):
    mapping = _require_mapping(record, label)
    _require_exact_keys(mapping, PARTY_KEYS, label)
    validated = {}
    for key, limit in PARTY_TEXT_LIMITS.items():
        validated[key] = _require_text(mapping[key], f"{label}.{key}", limit)
    source = validated["service_address_source"]
    if source not in SERVICE_ADDRESS_SOURCES:
        raise DraftValidationError(
            f"{label}.service_address_source 不是受支持的取值。"
        )
    is_company = mapping["is_company"]
    if not isinstance(is_company, bool):
        raise DraftValidationError(f"{label}.is_company 必须是布尔值。")
    validated["is_company"] = is_company
    return validated


def _validate_party_group(value, label):
    mapping = _require_mapping(value, "parties")
    _require_exact_keys(mapping, _PARTY_GROUP_KEYS, "parties")
    groups = {}
    for key in _PARTY_GROUP_KEYS:
        rows = mapping[key]
        if not isinstance(rows, list):
            raise DraftValidationError(f"{label}.{key} 必须是数组。")
        if len(rows) > MAX_PARTIES_PER_SIDE:
            raise DraftValidationError(f"{label}.{key} 的当事人数量超出上限。")
        groups[key] = tuple(
            _validate_party_record(record, f"{label}.{key}[{index}]")
            for index, record in enumerate(rows)
        )
    return groups


def _validate_agent(value):
    """Validate the optional agent record; ``None`` means "section closed".

    Every field stays optional text (an opened-but-blank section is a real
    user state), but a stated role must come from the shared vocabulary the
    party page's combo offers.
    """
    if value is None:
        return None
    mapping = _require_mapping(value, "agent")
    _require_exact_keys(mapping, _AGENT_KEYS, "agent")
    validated = {}
    for key, limit in _AGENT_TEXT_LIMITS.items():
        validated[key] = _require_text(mapping[key], f"agent.{key}", limit)
    if validated["type"] and validated["type"] not in AGENT_TYPES:
        raise DraftValidationError("agent.type 不是受支持的取值。")
    return validated


def _validate_flags(case_type, value):
    mapping = _require_mapping(value, "factual_flags")
    names = FLAG_FIELDS[case_type]
    _require_exact_keys(mapping, names, "factual_flags")
    validated = {}
    for name in names:
        raw = mapping[name]
        if name in STRING_FLAG_VALUES:
            # Classification flags are ``None`` (未确认) or a known vocabulary
            # string; anything else is rejected instead of coerced.
            if raw is not None and raw not in STRING_FLAG_VALUES[name]:
                raise DraftValidationError(
                    f"factual_flags.{name} 不是受支持的取值。"
                )
        elif raw is not None and not isinstance(raw, bool):
            # ``None`` is the "unconfirmed" state and must survive as such; a
            # missing or malformed value is never interpreted as a negative.
            raise DraftValidationError(
                f"factual_flags.{name} 必须是 true、false 或 null。"
            )
        validated[name] = raw
    return validated


def _validate_evidence(value):
    mapping = _require_mapping(value, "evidence")
    _require_exact_keys(mapping, _EVIDENCE_KEYS, "evidence")

    state = mapping["state"]
    if state not in EVIDENCE_STATES:
        raise DraftValidationError("evidence.state 不是受支持的证据状态。")

    rows = mapping["rows"]
    if not isinstance(rows, list):
        raise DraftValidationError("evidence.rows 必须是数组。")
    if len(rows) > MAX_EVIDENCE_ROWS:
        raise DraftValidationError("evidence.rows 的行数超出上限。")

    validated_rows = []
    for index, row in enumerate(rows):
        label = f"evidence.rows[{index}]"
        record = _require_mapping(row, label)
        _require_exact_keys(record, ("name", "target", "suggested"), label)
        name = _require_text(record["name"], f"{label}.name", EVIDENCE_TEXT_LIMITS["name"])
        target = _require_text(
            record["target"], f"{label}.target", EVIDENCE_TEXT_LIMITS["target"]
        )
        suggested = record["suggested"]
        if not isinstance(suggested, bool):
            raise DraftValidationError(f"{label}.suggested 必须是布尔值。")
        validated_rows.append({"name": name, "target": target, "suggested": suggested})

    if state in EMPTY_EVIDENCE_STATES and validated_rows:
        raise DraftValidationError("evidence.state 与证据行内容相互矛盾。")

    return state, tuple(validated_rows)


def _migrate(mapping):
    """Return a current-version copy of an older document; never mutates input.

    Version 1 -> 2: the labour case gained the arbitration posture
    (``has_arbitrated`` and three text fields) and its no-contract flag became
    tri-state. A version-1 ``False`` was the binary control's untouched
    default, so it is migrated to ``None`` ("未确认") rather than to a
    confirmed "否"; ``True`` was always an explicit choice and is kept.

    Version 2 -> 3: the labour arbitration posture became an explicit
    procedural classification. ``has_arbitrated`` maps onto ``labor_procedure``
    without inventing any fact: ``None`` stays ``None`` (未确认), ``False``
    becomes ``not_applied`` (the old control's own wording was "尚未申请劳动
    仲裁"), and ``True`` — which never recorded WHICH document the user
    received — becomes ``other_or_uncertain`` so a legacy draft can never
    silently enter the complaint path as a verified award or mediation. The
    refusal ground, party role and delay exception start unconfirmed, and the
    two new date fields start blank; the legacy receipt date is preserved
    verbatim. Non-labour drafts only move to the new version number.

    Version 3 -> 4: every party record gained the natural-person detail keys
    (gender, birth date, ethnicity and its free-text companion, occupation),
    filled blank because the legacy draft simply did not ask for them, and
    the document gained the optional ``agent`` record as ``None``.

    Version 4 -> 5: every case gained the optional user-supplied claim/fact
    fields, filled blank because a v4 draft never asked for them.

    Version 5 -> 6: rental drafts gained the payment-status classification
    (``None`` = unconfirmed) and the multi-defendant obligation description
    (blank), because a v5 draft never asked for either.

    Version 6 -> 7: every party record gained the service-address source,
    filled ``unconfirmed`` because a v6 draft never asked for it.

    Version 7 -> 8: loan drafts gained a repayment confirmation. Earlier
    drafts did not record repayment, so the new flag starts unconfirmed.
    """
    upgraded = dict(mapping)
    if upgraded.get("schema_version") == 1:
        upgraded = _migrate_v1_to_v2(upgraded)
    if upgraded.get("schema_version") == 2:
        upgraded = _migrate_v2_to_v3(upgraded)
    if upgraded.get("schema_version") == 3:
        upgraded = _migrate_v3_to_v4(upgraded)
    if upgraded.get("schema_version") == 4:
        upgraded = _migrate_v4_to_v5(upgraded)
    if upgraded.get("schema_version") == 5:
        upgraded = _migrate_v5_to_v6(upgraded)
    if upgraded.get("schema_version") == 6:
        upgraded = _migrate_v6_to_v7(upgraded)
    if upgraded.get("schema_version") == 7 and upgraded.get("case_type") == "loan":
        flags = upgraded.get("factual_flags")
        if isinstance(flags, dict):
            if "has_repayment" in flags:
                raise DraftValidationError("旧版借贷草稿不应包含还款情况。")
            upgraded["factual_flags"] = {**flags, "has_repayment": None}
    upgraded["schema_version"] = SCHEMA_VERSION
    return upgraded


def _migrate_v1_to_v2(mapping):
    """Version 1 -> 2 shape: arbitration posture fields appear on labour drafts."""
    upgraded = dict(mapping)
    if upgraded.get("case_type") == "labor":
        fields = upgraded.get("fields")
        if isinstance(fields, dict):
            fields = dict(fields)
            for key in ("l_arb_commission", "l_arb_case_no", "l_arb_receipt_date"):
                if key in fields:
                    raise DraftValidationError("fields 的字段集合不符合草稿格式。")
                fields[key] = ""
            upgraded["fields"] = fields
        flags = upgraded.get("factual_flags")
        if isinstance(flags, dict):
            if "has_arbitrated" in flags:
                raise DraftValidationError("factual_flags 的字段集合不符合草稿格式。")
            flags = dict(flags)
            if flags.get("is_no_contract") is False:
                flags["is_no_contract"] = None
            flags["has_arbitrated"] = None
            upgraded["factual_flags"] = flags
    upgraded["schema_version"] = 2
    return upgraded


def _migrate_v2_to_v3(mapping):
    """Version 2 -> 3 shape: labour posture becomes a procedural classification."""
    upgraded = dict(mapping)
    if upgraded.get("case_type") == "labor":
        fields = upgraded.get("fields")
        if isinstance(fields, dict):
            fields = dict(fields)
            for key in ("l_arb_application_date", "l_arb_acceptance_date"):
                if key in fields:
                    raise DraftValidationError("fields 的字段集合不符合草稿格式。")
                fields[key] = ""
            upgraded["fields"] = fields
        flags = upgraded.get("factual_flags")
        if isinstance(flags, dict):
            if "labor_procedure" in flags or "labor_role" in flags:
                raise DraftValidationError("factual_flags 的字段集合不符合草稿格式。")
            if "has_arbitrated" not in flags:
                raise DraftValidationError("factual_flags 的字段集合不符合草稿格式。")
            flags = dict(flags)
            legacy = flags.pop("has_arbitrated")
            if legacy is None:
                flags["labor_procedure"] = None
            elif legacy is False:
                flags["labor_procedure"] = "not_applied"
            else:
                # ``True`` only ever meant "some arbitration document was
                # received"; the type is unknown and must not be guessed.
                flags["labor_procedure"] = "other_or_uncertain"
            flags["labor_refusal_ground"] = None
            flags["labor_role"] = None
            flags["labor_delay_exception"] = None
            upgraded["factual_flags"] = flags
    upgraded["schema_version"] = 3
    return upgraded


def _migrate_v3_to_v4(mapping):
    """Version 3 -> 4 shape: party detail keys and the optional agent record."""
    upgraded = dict(mapping)
    parties = upgraded.get("parties")
    if isinstance(parties, dict):
        upgraded["parties"] = {
            group: [
                _complete_party_record_v4(record)
                if isinstance(record, dict) else record
                for record in rows
            ] if isinstance(rows, list) else rows
            for group, rows in parties.items()
        }
    if "agent" in upgraded:
        raise DraftValidationError("草稿文档的字段集合不符合草稿格式。")
    upgraded["agent"] = None
    upgraded["schema_version"] = 4
    return upgraded


def _complete_party_record_v4(record):
    """Return a copy of *record* with the v4 detail keys filled blank."""
    completed = dict(record)
    for key in _PARTY_KEYS_ADDED_IN_V4:
        if key in completed:
            raise DraftValidationError("parties 的当事人记录不符合草稿格式。")
        completed[key] = ""
    return completed


def _extra_field_keys(case_type):
    """Return the optional supplement keys registered for *case_type*."""
    return tuple(
        spec.key
        for spec in TEXT_FIELDS.get(case_type, ())
        if spec.widget in ("extra_claims", "extra_facts")
    )


def _migrate_v4_to_v5(mapping):
    """Version 4 -> 5 shape: optional user-supplied claims/facts fields."""
    upgraded = dict(mapping)
    case_type = upgraded.get("case_type")
    fields = upgraded.get("fields")
    if isinstance(fields, dict) and case_type in TEXT_FIELDS:
        fields = dict(fields)
        for key in _extra_field_keys(case_type):
            if key in fields:
                raise DraftValidationError("fields 的字段集合不符合草稿格式。")
            fields[key] = ""
        upgraded["fields"] = fields
    upgraded["schema_version"] = 5
    return upgraded


def _migrate_v5_to_v6(mapping):
    """Version 5 -> 6 shape: rental payment status and multi-defendant notes."""
    upgraded = dict(mapping)
    if upgraded.get("case_type") == "rental":
        fields = upgraded.get("fields")
        if isinstance(fields, dict):
            fields = dict(fields)
            if "r_defendant_obligations" in fields:
                raise DraftValidationError("fields 的字段集合不符合草稿格式。")
            fields["r_defendant_obligations"] = ""
            upgraded["fields"] = fields
        flags = upgraded.get("factual_flags")
        if isinstance(flags, dict):
            if "payment_status" in flags:
                raise DraftValidationError("factual_flags 的字段集合不符合草稿格式。")
            flags = dict(flags)
            flags["payment_status"] = None
            upgraded["factual_flags"] = flags
    upgraded["schema_version"] = 6
    return upgraded


def _migrate_v6_to_v7(mapping):
    """Version 6 -> 7 shape: every party gains its service-address source."""
    upgraded = dict(mapping)
    parties = upgraded.get("parties")
    if isinstance(parties, dict):
        upgraded["parties"] = {
            group: [
                _complete_party_record_v7(record)
                if isinstance(record, dict) else record
                for record in rows
            ] if isinstance(rows, list) else rows
            for group, rows in parties.items()
        }
    upgraded["schema_version"] = 7
    return upgraded


def _complete_party_record_v7(record):
    """Return a copy of *record* with the v7 source filled safely."""
    completed = dict(record)
    if _PARTY_KEY_ADDED_IN_V7 in completed:
        raise DraftValidationError("parties 的当事人记录不符合草稿格式。")
    completed[_PARTY_KEY_ADDED_IN_V7] = "unconfirmed"
    return completed


def validate_document(payload):
    """Validate *payload* and return a :class:`DraftDocument`.

    Raises :class:`DraftValidationError` for every structural problem. The
    function never mutates the input and never returns a partially valid
    document. A supported older version is migrated first and then validated
    exactly like a current document.
    """
    mapping = _require_mapping(payload, "草稿文档")

    version = mapping.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise DraftValidationError("schema_version 必须是整数。")
    if version in MIGRATABLE_VERSIONS:
        # v1-v3 documents predate ``agent``; v4 and later carry it. The strict check
        # runs against the document's own version so legacy drafts reach
        # migration instead of being rejected for the wrong key set.
        expected_keys = _DOCUMENT_KEYS_V3 if version <= 3 else _DOCUMENT_KEYS
        _require_exact_keys(mapping, expected_keys, "草稿文档")
        mapping = _migrate(mapping)
        version = SCHEMA_VERSION
    _require_exact_keys(mapping, _DOCUMENT_KEYS, "草稿文档")
    if version != SCHEMA_VERSION:
        raise DraftValidationError(
            f"草稿文档版本不受支持（文档版本 {version}，当前支持 {SCHEMA_VERSION}）。"
        )

    case_type = mapping["case_type"]
    if not isinstance(case_type, str) or case_type not in CASE_TYPES:
        raise DraftValidationError("case_type 不是受支持的案件类型。")

    resume_page = mapping["resume_page"]
    if not isinstance(resume_page, str) or resume_page not in RESUME_PAGES:
        raise DraftValidationError("resume_page 不是受支持的向导页面。")

    fields = _validate_fields(case_type, mapping["fields"])
    parties = _validate_party_group(mapping["parties"], "parties")
    flags = _validate_flags(case_type, mapping["factual_flags"])
    state, rows = _validate_evidence(mapping["evidence"])
    agent = _validate_agent(mapping["agent"])

    return DraftDocument(
        case_type=case_type,
        fields=fields,
        plaintiffs=parties["plaintiffs"],
        defendants=parties["defendants"],
        factual_flags=flags,
        evidence_state=state,
        evidence_rows=rows,
        resume_page=resume_page,
        agent=agent,
        schema_version=version,
    )


# --------------------------------------------------------------------------- #
# JSON codec
# --------------------------------------------------------------------------- #


def _reject_duplicate_keys(pairs):
    """``object_pairs_hook`` that refuses a document with repeated keys.

    ``json`` silently keeps the last value, which would let two different
    readers disagree about the same draft; the format forbids that.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise DraftValidationError("草稿文档包含重复的字段名。")
        result[key] = value
    return result


def _reject_constant(name):
    raise DraftValidationError("草稿文档包含不支持的数值常量。")


def to_json_bytes(document):
    """Serialize *document* deterministically to UTF-8 JSON bytes.

    Keys are sorted, separators are fixed and non-ASCII text is stored as real
    UTF-8 (the bytes are encrypted anyway), so the same content always yields
    the same plaintext.
    """
    if not isinstance(document, DraftDocument):
        raise DraftValidationError("只能序列化已校验的草稿文档。")
    try:
        text = json.dumps(
            document.to_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        raw = text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise DraftValidationError("草稿文档无法序列化为 UTF-8 JSON。")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise DraftFileTooLargeError("草稿文档超出支持的大小上限。")
    return raw


def from_json_bytes(raw):
    """Parse and validate UTF-8 JSON bytes into a :class:`DraftDocument`."""
    data = bytes(raw)
    if not data:
        raise DraftValidationError("草稿内容为空。")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DraftFileTooLargeError("草稿文档超出支持的大小上限。")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise DraftValidationError("草稿内容不是有效的 UTF-8 文本。")
    if text.startswith("\ufeff"):
        raise DraftValidationError("草稿内容不应包含字节序标记。")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except DraftValidationError:
        raise
    except (json.JSONDecodeError, ValueError):
        raise DraftValidationError("草稿内容不是有效的 JSON 文档。")
    return validate_document(payload)
