# File: presenters/model_builder.py
# Purpose: Build a case model from wizard field values (shared by export and preview)
# Encoding: UTF-8
"""Collect wizard input into a case model.

``build_case_model`` is the single place that maps wizard fields onto a
:class:`~models.case_model.CaseTemplate`. Both the on-screen preview and the
finally exported document are derived from this same source, so they cannot
drift apart.
"""

from models.case_model import (
    AgentInfo,
    ContractCaseModel,
    DivorceCaseModel,
    EvidenceItem,
    LaborCaseModel,
    LoanCaseModel,
    PartyInfo,
    PropertyCaseModel,
    RentalCaseModel,
)

_MODEL_BY_CASE_TYPE = {
    "loan": LoanCaseModel,
    "contract": ContractCaseModel,
    "property": PropertyCaseModel,
    "labor": LaborCaseModel,
    "divorce": DivorceCaseModel,
    "rental": RentalCaseModel,
}

# Single supported-case registry shared by model building, wizard routing and
# presenter validation. Unknown identifiers must fail closed everywhere: they
# may never silently become a loan case.
SUPPORTED_CASE_TYPES = frozenset(_MODEL_BY_CASE_TYPE)


def is_supported_case_type(case_type):
    """Return ``True`` only for the supported case-type identifiers; never raises.

    This is the one validation contract shared by model construction, wizard
    routing, preview and Finish/export. Malformed strings, unsupported
    strings, missing values, non-string values and unhashable values (which
    would raise ``TypeError`` on a frozenset membership test) are all rejected
    without raising, and nothing is coerced into a valid identifier.
    """
    return isinstance(case_type, str) and case_type in _MODEL_BY_CASE_TYPE


class UnsupportedCaseTypeError(ValueError):
    """Raised when the wizard reports a case type outside the supported registry."""


def _model_for(case_type):
    """Return the model instance for a supported case type; fail closed otherwise."""
    if not is_supported_case_type(case_type):
        raise UnsupportedCaseTypeError(f"不支持的案由类型：{case_type!r}")
    return _MODEL_BY_CASE_TYPE[case_type]()


def _text(value):
    return (value or "").strip()


def _resolve_ethnicity(p_data):
    """Resolve the raw combo choice plus free-text companion into the final value.

    The party page stores ``ethnicity`` verbatim (it may literally be "其他")
    so a draft can restore the combo state; only here does "其他" become the
    user's typed name.
    """
    ethnicity = _text(p_data.get("ethnicity"))
    if ethnicity == "其他":
        return _text(p_data.get("ethnicity_other"))
    return ethnicity


def _add_parties(model, party_data):
    for party_type, key in ((0, "plaintiffs"), (1, "defendants")):
        for p_data in party_data.get(key, []):
            if not _text(p_data.get("name")):
                # Incomplete parties are skipped here, but the presenter blocks
                # export entirely when a required party is missing.
                continue
            # Keyword arguments: PartyInfo's parameter list keeps growing with
            # the document conventions, and positional order is a trap.
            model.party_manager.add_party(party_type, PartyInfo(
                name=p_data["name"],
                id_number=p_data.get("id_number", ""),
                address=p_data.get("address", ""),
                phone=p_data.get("phone", ""),
                is_company=p_data.get("is_company", False),
                legal_representative=p_data.get("legal_representative", ""),
                credit_code=p_data.get("credit_code", ""),
                gender=p_data.get("gender", ""),
                birth_date=p_data.get("birth_date", ""),
                ethnicity=_resolve_ethnicity(p_data),
                occupation=p_data.get("occupation", ""),
                service_address_source=p_data.get(
                    "service_address_source", "unconfirmed"
                ),
            ))


def _add_agent(model, view):
    """Attach the optional agent; the section stays case-level, plaintiff-side."""
    agent_data = view.party_page.get_agent_data()
    if not agent_data:
        return
    if not _text(agent_data.get("name")):
        # An opened-but-nameless section is a UI state, not an agent: the
        # document paragraph needs a name to attach the remaining details to.
        return
    model.agent = AgentInfo(
        name=_text(agent_data.get("name")),
        type=_text(agent_data.get("type")),
        org=_text(agent_data.get("org")),
        phone=_text(agent_data.get("phone")),
    )


def _fill_loan(view, model):
    model.loan_date = view.field("loan_date")
    model.loan_reason = view.field("loan_reason")
    model.principal_amount = view.field("principal")
    model.interest_rate = view.field("rate")
    model.interest_start_date = view.field("start_date")
    model.payment_method = view.field("payment_method")
    model.has_iou = view.loan_claim_page.get_has_iou()
    model.has_repayment = view.loan_claim_page.get_has_repayment()
    model.demand_date = view.field("demand_date")
    model.demand_method = view.field("demand_method")
    model.court_name = view.field("court_name")


def _penalty_calc_standard_for(method, lpr_value, lpr_multiple):
    """Map a verified calculator method to the standard it actually used.

    Explicit method-to-standard contract: a daily 万五 calculation is
    described by its own convention, never by the LPR parameters, and an LPR
    calculation is described only by the parameters in effect. Any unknown
    method (or missing LPR parameters for the LPR method) yields an empty
    standard so the claim falls back to the neutral manual-amount wording.
    """
    if method == "daily_5_per_10k":
        return "日万分之五"
    if method == "lpr_multiple" and lpr_value and lpr_multiple:
        return f"{lpr_value}%×{lpr_multiple}"
    return ""


def _fill_contract(view, model):
    model.contract_date = view.field("c_contract_date")
    model.contract_name = view.field("c_contract_name")
    model.product_name = view.field("c_product_name")
    model.total_amount = view.field("c_total_amount")
    model.delivery_date = view.field("c_delivery_date")
    model.unpaid_amount = view.field("c_unpaid_amount")
    model.penalty_amount = view.field("c_penalty_amount")
    model.penalty_start_date = view.field("c_overdue_start")
    model.penalty_cutoff_date = view.field("c_overdue_end")

    lpr_value = _text(view.field("c_lpr_value"))
    lpr_multiple = _text(view.field("c_lpr_multiple"))

    # The calculation description is derived from the verified provenance
    # (which calculator actually produced the amount) and only from the
    # parameters that calculator uses; a manually typed amount carries no
    # calculation description at all.
    basis = view.contract_claim_page.get_penalty_calc_basis()
    standard = _penalty_calc_standard_for(
        basis["method"] if basis else None, lpr_value, lpr_multiple
    )
    if basis is not None and standard:
        model.penalty_calc_method = basis["method"]
        model.penalty_calc_cutoff = basis["cutoff"]
        model.penalty_calc_standard = standard
    else:
        # No valid provenance: fail closed to the neutral description instead
        # of risking a mismatched calculation standard.
        model.penalty_calc_method = ""
        model.penalty_calc_cutoff = ""
        model.penalty_calc_standard = ""

    model.court_name = view.field("c_court_name")

    flags = view.contract_claim_page.get_flags()
    model.is_delivered = flags["is_delivered"]
    model.is_signed = flags["is_signed"]


def _fill_property(view, model):
    model.property_addr = view.field("p_property_addr")
    model.house_area = view.field("p_house_area")
    model.fee_rate = view.field("p_fee_rate")
    model.period_start = view.field("p_period_start")
    model.period_end = view.field("p_period_end")
    model.late_fee_logic = view.field("p_late_fee_logic")
    model.demand_record = view.field("p_demand_record")
    model.total_principal = view.field("p_total_input")
    model.court_name = view.field("p_court_name")


def _fill_labor(view, model):
    model.emp_join_date = view.field("l_emp_join_date")
    model.job_title = view.field("l_job_title")
    model.monthly_salary = view.field("l_monthly_salary")
    model.unpaid_months = view.field("l_unpaid_months")
    model.emp_term_date = view.field("l_emp_term_date")
    model.overtime_hours = view.field("l_overtime_hours")
    model.overtime_pay = view.field("l_overtime_pay")
    model.is_no_contract = view.labor_claim_page.get_has_no_contract()
    model.social_sec_info = view.field("l_social_sec_info")
    model.court_name = view.field("l_court_name")
    model.labor_procedure = view.labor_claim_page.get_labor_procedure()
    model.labor_refusal_ground = view.labor_claim_page.get_refusal_ground()
    model.labor_role = view.labor_claim_page.get_labor_role()
    model.labor_delay_exception = view.labor_claim_page.get_delay_exception()
    model.arb_commission = view.field("l_arb_commission")
    model.arb_case_no = view.field("l_arb_case_no")
    model.arb_receipt_date = view.field("l_arb_receipt_date")
    model.arb_application_date = view.field("l_arb_application_date")
    model.arb_acceptance_date = view.field("l_arb_acceptance_date")


def _fill_rental(view, model):
    model.property_address = view.field("r_property_address")
    model.contract_date = view.field("r_contract_date")
    model.lease_start = view.field("r_lease_start")
    model.lease_end = view.field("r_lease_end")
    model.monthly_rent = view.field("r_monthly_rent")
    model.payment_cycle = view.field("r_payment_cycle")
    model.arrears_start = view.field("r_arrears_start")
    model.arrears_end = view.field("r_arrears_end")
    model.arrears_amount = view.field("r_arrears_amount")
    model.late_fee = view.field("r_late_fee")
    model.demand_record = view.field("r_demand_record")
    model.payment_status = view.rental_claim_page.get_payment_status()
    model.defendant_obligations = view.field("r_defendant_obligations")
    model.termination_date = view.field("r_termination_date")
    model.court_name = view.field("r_court_name")
    model.lease_status = view.rental_claim_page.get_lease_status()
    model.property_returned = view.rental_claim_page.get_property_returned()


def _fill_divorce(view, model):
    model.marriage_date = view.field("d_marriage_date")
    model.child_name = view.field("d_child_name")
    model.child_birthday = view.field("d_child_birthday")
    model.custody_preference = view.field("d_custody_preference")
    model.support_monthly = view.field("d_support_monthly")
    model.divorce_reason = view.field("d_divorce_reason")
    # This field is registered by the wizard page; make sure it reaches the model.
    model.separation_start_date = view.field("d_separation_start_date")
    model.asset_description = view.field("d_asset_description")
    model.court_name = view.field("d_court_name")


_FILLERS = {
    "loan": _fill_loan,
    "contract": _fill_contract,
    "property": _fill_property,
    "labor": _fill_labor,
    "divorce": _fill_divorce,
    "rental": _fill_rental,
}

#: Registered field prefix used by each claim page's supplement section.
_EXTRA_FIELD_PREFIX = {
    "loan": "loan",
    "contract": "c",
    "property": "p",
    "labor": "l",
    "divorce": "d",
    "rental": "r",
}


def _fill_extras(view, model, case_type):
    """Copy the optional user-supplied claims/facts onto the model."""
    prefix = _EXTRA_FIELD_PREFIX[case_type]
    claims_text = view.field(f"{prefix}_extra_claims") or ""
    facts_text = view.field(f"{prefix}_extra_facts") or ""
    model.extra_claims = [
        line.strip() for line in str(claims_text).splitlines() if line.strip()
    ]
    model.extra_facts = str(facts_text).strip()


def build_case_model(view):
    """Return a populated case model for the wizard's current selection."""
    case_type = view.field("case_type")
    model = _model_for(case_type)

    _add_parties(model, view.party_page.get_party_data())

    _add_agent(model, view)

    _FILLERS[case_type](view, model)
    _fill_extras(view, model, case_type)

    for name, target in view.evidence_page.get_exportable_evidence_items():
        model.evidences.append(EvidenceItem(name, target))

    return model
