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
                      wizard field identifiers (never renamed here);
* ``parties``       - ordered plaintiff/defendant records, blank cards included;
* ``factual_flags`` - tri-state confirmations where ``None`` means "unconfirmed";
* ``evidence``      - the row list plus the page's own state label;
* ``resume_page``   - a stable *page name*, never a numeric Qt page id.

Deliberately excluded: generated DOCX content, rendered claims/facts, derived
calculation results, the contract calculator provenance, temporary paths,
runtime object identities and any application secret. Excluding the
provenance is a security decision, not an omission: a restored amount has not
been recomputed, so it must fall back to the neutral "manual amount" wording
(see :mod:`views.draft_io`).

Validation is strict and one-way. Unknown keys, missing keys, unknown case
types, unknown schema versions and out-of-range collections are all rejected;
nothing is coerced, defaulted or migrated.
"""

import json
from dataclasses import dataclass

from drafts.errors import DraftFileTooLargeError, DraftValidationError
from drafts.storage import MAX_PLAINTEXT_BYTES

#: Version of the *inner* JSON document (independent of the envelope version).
SCHEMA_VERSION = 1

#: Case categories this build can restore. Mirrors
#: ``presenters.model_builder.SUPPORTED_CASE_TYPES`` and is asserted equal there.
CASE_TYPES = ("loan", "contract", "property", "labor", "divorce")

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
}
PARTY_KEYS = tuple(PARTY_TEXT_LIMITS) + ("is_company",)

EVIDENCE_TEXT_LIMITS = {"name": 500, "target": 1000}

_DOCUMENT_KEYS = (
    "schema_version",
    "case_type",
    "fields",
    "parties",
    "factual_flags",
    "evidence",
    "resume_page",
)

_PARTY_GROUP_KEYS = ("plaintiffs", "defendants")
_EVIDENCE_KEYS = ("state", "rows")

#: Confirmations whose third state (``None`` = 未确认) is meaningful.
TRI_STATE_FLAGS = ("has_iou", "is_delivered", "is_signed")

#: Confirmations that are genuinely binary in the current UI (no unknown
#: option exists), so a null value is structurally invalid for them.
BINARY_FLAGS = ("is_no_contract",)

#: Case type -> the page name that owns its claim inputs.
CLAIM_PAGE_NAMES_BY_CASE = {
    "loan": "loan_claim",
    "contract": "contract_claim",
    "property": "property_claim",
    "labor": "labor_claim",
    "divorce": "divorce_claim",
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
        ("d_court_name", "court_name", TEXT_LIMIT, False),
    )),
}

#: Confirmations stored per case type, in a fixed order.
FLAG_FIELDS = {
    "loan": ("has_iou",),
    "contract": ("is_delivered", "is_signed"),
    "property": (),
    "labor": ("is_no_contract",),
    "divorce": (),
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


def _validate_flags(case_type, value):
    mapping = _require_mapping(value, "factual_flags")
    names = FLAG_FIELDS[case_type]
    _require_exact_keys(mapping, names, "factual_flags")
    validated = {}
    for name in names:
        raw = mapping[name]
        if name in BINARY_FLAGS:
            if not isinstance(raw, bool):
                raise DraftValidationError(f"factual_flags.{name} 必须是布尔值。")
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


def validate_document(payload):
    """Validate *payload* and return a :class:`DraftDocument`.

    Raises :class:`DraftValidationError` for every structural problem. The
    function never mutates the input and never returns a partially valid
    document.
    """
    mapping = _require_mapping(payload, "草稿文档")
    _require_exact_keys(mapping, _DOCUMENT_KEYS, "草稿文档")

    version = mapping["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise DraftValidationError("schema_version 必须是整数。")
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

    return DraftDocument(
        case_type=case_type,
        fields=fields,
        plaintiffs=parties["plaintiffs"],
        defendants=parties["defendants"],
        factual_flags=flags,
        evidence_state=state,
        evidence_rows=rows,
        resume_page=resume_page,
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
