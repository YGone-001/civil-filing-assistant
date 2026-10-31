# File: views/draft_io.py
# Purpose: The only Qt-aware adapter between wizard widgets and draft documents.
# Encoding: UTF-8
"""Capture a wizard's user input into a draft payload, and restore one.

This module is deliberately the *single* place that touches widgets for the
draft feature. ``drafts.schema`` validates the payload without Qt, and
``drafts.storage`` only moves bytes, so the widget knowledge stays here.

Two rules drive the implementation:

1. **Preserve user intent, not derived results.** Only text the user can edit,
   the party card list, the tri-state confirmations and the evidence rows are
   captured. Rendered claims, calculated totals and the contract calculator
   provenance are recomputed (or deliberately dropped) on restore.
2. **Restore without re-initialising.** ``PartyPage.initializePage()`` and
   ``EvidencePage.initializePage()`` rebuild their content when the page is
   first shown. A restored page is therefore marked as already initialised for
   the restored case type, so a later visit does not wipe the restored cards or
   resurrect evidence suggestions the user had deliberately deleted.
"""

from dataclasses import dataclass

from drafts.schema import (
    CLAIM_PAGE_NAMES_BY_CASE,
    FLAG_FIELDS,
    SCHEMA_VERSION,
    TEXT_FIELDS,
)
from presenters.model_builder import is_supported_case_type

#: Draft page name -> wizard attribute holding the numeric Qt page id.
PAGE_ATTR_BY_NAME = {
    "welcome": "PAGE_WELCOME",
    "case_selection": "PAGE_CASE_SELECTION",
    "party": "PAGE_PARTY",
    "loan_claim": "PAGE_LOAN_CLAIM",
    "contract_claim": "PAGE_CONTRACT_CLAIM",
    "property_claim": "PAGE_PROPERTY_CLAIM",
    "labor_claim": "PAGE_LABOR_CLAIM",
    "divorce_claim": "PAGE_DIVORCE_CLAIM",
    "evidence": "PAGE_EVIDENCE",
    "export": "PAGE_EXPORT",
}

#: Case type -> wizard attribute holding the matching claim page.
CLAIM_PAGE_ATTR_BY_CASE = {
    "loan": "loan_claim_page",
    "contract": "contract_claim_page",
    "property": "property_claim_page",
    "labor": "labor_claim_page",
    "divorce": "divorce_claim_page",
}

#: Registered text inputs whose widget starts *non-empty*. Everything else in
#: ``drafts.schema.TEXT_FIELDS`` starts blank, so "text differs from this
#: table" is exactly "the user edited it". Kept narrow (two calculator
#: parameters) and pinned to the real page constructors by tests.
INITIAL_FIELD_VALUES = {
    "c_lpr_value": "3.45",
    "c_lpr_multiple": "4",
}

#: Initial state of every persisted confirmation. ``None`` is the tri-state
#: "未确认" default; the labour control is binary and starts unchecked, which is
#: why ``False`` is only meaningful for the fields whose default is ``None``.
INITIAL_FLAG_VALUES = {
    "has_iou": None,
    "is_delivered": None,
    "is_signed": None,
    "is_no_contract": False,
}

#: Party-card widget keys that hold user-editable text. ``is_company`` is the
#: seventh user-editable attribute and is checked separately because it is a
#: checkbox, not a text field.
PARTY_TEXT_WIDGET_KEYS = ("name", "id", "addr", "phone", "credit_code", "legal_rep")

#: Cards the wizard creates per side when the party page is first shown. An
#: additional card is a user-created entry even while it is still blank.
PRISTINE_PARTY_CARDS = 1

#: Pages that only make sense once both sides have a named party. Resuming
#: directly onto one of them with an incomplete party list would drop the user
#: into a page whose prerequisites are unmet, so the restore falls back.
_PARTY_DEPENDENT_PAGES = frozenset(
    {"evidence", "export", *CLAIM_PAGE_NAMES_BY_CASE.values()}
)

#: Pages that also require the case-fact page to be complete. Without this a
#: restored draft could land on the export page with blank required fields and
#: an enabled Finish button, producing a document full of empty placeholders.
_CLAIM_DEPENDENT_PAGES = frozenset({"evidence", "export"})

__all__ = [
    "CLAIM_PAGE_ATTR_BY_CASE",
    "INITIAL_FIELD_VALUES",
    "INITIAL_FLAG_VALUES",
    "PAGE_ATTR_BY_NAME",
    "PARTY_TEXT_WIDGET_KEYS",
    "PRISTINE_PARTY_CARDS",
    "RestoreResult",
    "apply_draft",
    "capture_draft",
    "claim_page",
    "has_meaningful_session",
    "page_id",
    "page_name",
    "resolve_resume_page",
]


@dataclass(frozen=True)
class RestoreResult:
    """Where the restored wizard was left, and why it may differ from the draft."""

    resume_page: str
    resume_page_id: int
    note: str = ""


# --------------------------------------------------------------------------- #
# Small widget helpers
# --------------------------------------------------------------------------- #


def _read_text(widget):
    """Read the current text of a line edit or a multi-line edit."""
    if hasattr(widget, "toPlainText"):
        return widget.toPlainText()
    return widget.text()


def _write_text(widget, value):
    """Write *value* into a line edit or a multi-line edit."""
    if hasattr(widget, "setPlainText"):
        widget.setPlainText(value)
    else:
        widget.setText(value)


def _side_widgets(page, kind):
    return page.plaintiff_widgets if kind == 0 else page.defendant_widgets


def claim_page(wizard, case_type):
    """Return the claim page that owns *case_type*'s inputs."""
    return getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])


def page_id(wizard, name):
    """Return the numeric Qt page id for a draft page name."""
    return getattr(wizard, PAGE_ATTR_BY_NAME[name])


def page_name(wizard):
    """Return the draft page name of the wizard's current page."""
    current = wizard.currentId()
    for name, attribute in PAGE_ATTR_BY_NAME.items():
        if getattr(wizard, attribute) == current:
            return name
    # ``currentId()`` is -1 before the wizard has started; treat that as the
    # landing page instead of inventing a page id.
    return "welcome"


# --------------------------------------------------------------------------- #
# Meaningful-session detection
# --------------------------------------------------------------------------- #


def _has_party_input(page):
    """Return whether any party card holds user input or a user-added card.

    A party counts even when its name is blank: an identity number, an address
    or a phone number typed into an unnamed card is exactly the data the
    replacement guard used to lose. A card the wizard created itself stays
    blank, so the pristine page (one blank card per side) reports nothing.
    """
    for kind in (0, 1):
        cards = _side_widgets(page, kind)
        if len(cards) > PRISTINE_PARTY_CARDS:
            # The user added a card; it is their entry even before it is typed.
            return True
        for card in cards:
            if card["is_company"].isChecked():
                return True
            if any(_read_text(card[key]).strip() for key in PARTY_TEXT_WIDGET_KEYS):
                return True
    return False


def _has_edited_fields(page, case_type):
    """Return whether any registered text input differs from its initial text."""
    for spec in TEXT_FIELDS[case_type]:
        value = _read_text(getattr(page, spec.widget))
        if value != INITIAL_FIELD_VALUES.get(spec.key, ""):
            return True
    return False


def _has_edited_flags(page, case_type):
    """Return whether any confirmation differs from its initial state.

    The comparison keeps ``None`` distinct from ``False``: for the tri-state
    controls ``None`` is "未确认", so a confirmed "否" is a real user decision,
    while the labour control's own default really is ``False``.
    """
    for name, value in _capture_flags(page, case_type).items():
        if value != INITIAL_FLAG_VALUES[name]:
            return True
    return False


def has_meaningful_session(wizard):
    """Return whether the current wizard holds state a replacement would lose.

    This is the contract behind "ask before opening another draft". It is
    deliberately observational - it never initialises a page, creates or
    renumbers a party card, or loads evidence - so calling it cannot itself
    change the session.

    A session is meaningful when any of the following is true:

    * a party card holds any user-editable value, or the user added a card;
    * *any* of the five case pages holds a registered input that differs from
      the value its page starts with (blank, except the contract LPR reference
      and multiplier), or a factual confirmation that differs from its initial
      state;
    * evidence was edited or explicitly cleared in *any* category, including
      one the user has since switched away from.

    Every claim page is inspected, not only the selected case's page. Switching
    the case category leaves the previous page's widgets untouched (the page's
    ``cleanupPage()`` deliberately preserves them), so data entered under an
    earlier category stays in memory even though it is no longer visible. That
    retained state is still the user's work and must not be replaced silently.

    Selecting a case category without entering anything is not treated as
    meaningful: nothing typed is lost, and prompting there would be a false
    positive on a brand-new wizard. The registered default values
    (``INITIAL_FIELD_VALUES`` / ``INITIAL_FLAG_VALUES``) are likewise not
    treated as user input.
    """
    if _has_party_input(wizard.party_page):
        return True

    for case_type in CLAIM_PAGE_ATTR_BY_CASE:
        page = claim_page(wizard, case_type)
        if _has_edited_fields(page, case_type):
            return True
        if _has_edited_flags(page, case_type):
            return True

    return wizard.evidence_page.has_user_evidence()


# --------------------------------------------------------------------------- #
# Capture
# --------------------------------------------------------------------------- #


def _capture_flags(page, case_type):
    """Return the confirmation states for *case_type*, preserving ``None``."""
    names = FLAG_FIELDS[case_type]
    if not names:
        return {}
    if case_type == "loan":
        return {"has_iou": page.get_has_iou()}
    if case_type == "contract":
        flags = page.get_flags()
        return {"is_delivered": flags["is_delivered"], "is_signed": flags["is_signed"]}
    if case_type == "labor":
        return {"is_no_contract": bool(page.get_has_no_contract())}
    raise AssertionError(f"未登记的事实确认项：{case_type}")


def capture_draft(wizard, resume_page=None):
    """Build a draft payload from the wizard's current, possibly incomplete state.

    Nothing is validated against the export gate: blank required fields, empty
    party cards, unresolved confirmations and an untouched evidence page are
    all legitimate draft content.
    """
    case_type = wizard.field("case_type")
    if not is_supported_case_type(case_type):
        raise ValueError("当前案由无法保存为草稿，请先选择受支持的案件类型。")

    page = claim_page(wizard, case_type)
    fields = {
        spec.key: _read_text(getattr(page, spec.widget))
        for spec in TEXT_FIELDS[case_type]
    }

    parties = wizard.party_page.get_party_data()
    evidence = wizard.evidence_page.snapshot_evidence(case_type)

    return {
        "schema_version": SCHEMA_VERSION,
        "case_type": case_type,
        "fields": fields,
        "parties": {
            "plaintiffs": parties["plaintiffs"],
            "defendants": parties["defendants"],
        },
        "factual_flags": _capture_flags(page, case_type),
        "evidence": evidence,
        "resume_page": resume_page or page_name(wizard),
    }


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #


def _apply_case_type(wizard, case_type):
    combo = wizard.case_selection_page.case_combo
    index = combo.findData(case_type)
    if index < 0:
        raise ValueError("草稿中的案件类型不在当前支持范围内。")
    combo.setCurrentIndex(index)


def _fill_party_card(widget, record):
    widget["name"].setText(record["name"])
    widget["id"].setText(record["id_number"])
    widget["addr"].setText(record["address"])
    widget["phone"].setText(record["phone"])
    widget["credit_code"].setText(record["credit_code"])
    widget["legal_rep"].setText(record["legal_representative"])
    # Checked last: toggling swaps the visible identity fields, and the values
    # above must already be in place when that happens.
    widget["is_company"].setChecked(bool(record["is_company"]))


def _restore_side(page, kind, records):
    """Rebuild one side's cards so the restored list matches *records*.

    The wizard never presents an empty party page, so a draft that recorded no
    cards for a side is restored as one blank card - the same state a fresh
    wizard starts in. Every recorded card, including a deliberately blank one,
    is restored verbatim and in order.
    """
    target = max(1, len(records))
    while len(_side_widgets(page, kind)) < target:
        page.add_party_ui(kind)
    while len(_side_widgets(page, kind)) > target:
        page.remove_party_ui(kind, len(_side_widgets(page, kind)) - 1)
    for record, widget in zip(records, _side_widgets(page, kind)):
        _fill_party_card(widget, record)


def _apply_parties(wizard, document):
    page = wizard.party_page
    _restore_side(page, 0, document.plaintiffs)
    _restore_side(page, 1, document.defendants)

    # Mark the page as initialised for this case type: the next
    # ``initializePage()`` must not delete the restored cards.
    page.current_case_type = document.case_type
    page.is_initialized = True
    page._touched = False
    page._renumber_parties()
    page._rebuild_party_tab_order()
    page._refresh_validation_message()


def _apply_fields(page, document):
    for spec in TEXT_FIELDS[document.case_type]:
        _write_text(getattr(page, spec.widget), document.fields[spec.key])


def _set_tri_state(yes_button, no_button, unknown_button, value):
    """Select the button matching *value*; ``None`` selects "未确认"."""
    if value is True:
        yes_button.setChecked(True)
    elif value is False:
        no_button.setChecked(True)
    else:
        unknown_button.setChecked(True)


def _apply_flags(page, document):
    case_type = document.case_type
    flags = document.factual_flags

    if case_type == "loan":
        _set_tri_state(page.iou_yes, page.iou_no, page.iou_unknown, flags["has_iou"])
    elif case_type == "contract":
        _set_tri_state(page.del_yes, page.del_no, page.del_unknown, flags["is_delivered"])
        _set_tri_state(page.sign_yes, page.sign_no, page.sign_unknown, flags["is_signed"])
    elif case_type == "labor":
        # Binary control: there is no "unknown" option, so the stored boolean is
        # applied directly and never inferred from a missing value.
        is_no_contract = bool(flags["is_no_contract"])
        page.no_contract_yes.setChecked(is_no_contract)
        page.no_contract_no.setChecked(not is_no_contract)

    # Re-evaluate the page's conditional requirement for the restored state so
    # the on-screen hint and the Next button tell the truth immediately.
    refresh = getattr(page, "_refresh_conditional", None)
    if callable(refresh):
        refresh()


def resolve_resume_page(wizard, document):
    """Return ``(page_name, note)`` for the page the restored wizard opens on.

    A draft stores a page *name*, never a numeric id, and the page is only
    honoured when the restored state can actually stand on it. Otherwise the
    wizard opens on the earliest page that makes sense and the caller explains
    the downgrade - it never pretends an incomplete case has been validated.
    """
    name = document.resume_page

    expected_claim_page = CLAIM_PAGE_NAMES_BY_CASE[document.case_type]
    if name in CLAIM_PAGE_NAMES_BY_CASE.values() and name != expected_claim_page:
        return "party", "草稿记录的步骤与案由不一致，已从“当事人”步骤开始。"

    if name in _PARTY_DEPENDENT_PAGES and not wizard.party_page.isComplete():
        return "party", "草稿中的当事人信息尚未填写完整，已从“当事人”步骤开始。"

    if name in _CLAIM_DEPENDENT_PAGES and not claim_page(wizard, document.case_type).isComplete():
        return (
            expected_claim_page,
            "草稿中的案情与请求尚未填写完整，已从该步骤开始，请补齐后再继续。",
        )

    return name, ""


def apply_draft(wizard, document):
    """Restore *document* into a freshly created wizard and return the outcome.

    The wizard passed in must be a new instance: restoring onto a live session
    would mix two cases if any later step failed. Callers construct the
    replacement first and only swap it in once this function returns.
    """
    _apply_case_type(wizard, document.case_type)
    _apply_parties(wizard, document)

    page = claim_page(wizard, document.case_type)
    _apply_fields(page, document)
    _apply_flags(page, document)

    wizard.evidence_page.restore_evidence(
        document.case_type, document.evidence_state, document.evidence_rows
    )

    resume_page, note = resolve_resume_page(wizard, document)
    target_id = page_id(wizard, resume_page)
    wizard.setCurrentId(target_id)
    return RestoreResult(resume_page=resume_page, resume_page_id=target_id, note=note)
