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
    ContractCaseModel,
    DivorceCaseModel,
    EvidenceItem,
    LaborCaseModel,
    LoanCaseModel,
    PartyInfo,
    PropertyCaseModel,
)

_MODEL_BY_CASE_TYPE = {
    "contract": ContractCaseModel,
    "property": PropertyCaseModel,
    "labor": LaborCaseModel,
    "divorce": DivorceCaseModel,
}


def _model_for(case_type):
    return _MODEL_BY_CASE_TYPE.get(case_type, LoanCaseModel)()


def _text(value):
    return (value or "").strip()


def _add_parties(model, party_data):
    for party_type, key in ((0, "plaintiffs"), (1, "defendants")):
        for p_data in party_data.get(key, []):
            if not _text(p_data.get("name")):
                # Incomplete parties are skipped here, but the presenter blocks
                # export entirely when a required party is missing.
                continue
            model.party_manager.add_party(party_type, PartyInfo(
                p_data["name"],
                p_data["id_number"],
                p_data["address"],
                p_data["phone"],
                p_data["is_company"],
                p_data["legal_representative"],
                p_data["credit_code"],
            ))


def _fill_loan(view, model):
    model.loan_date = view.field("loan_date")
    model.loan_reason = view.field("loan_reason")
    model.principal_amount = view.field("principal")
    model.interest_rate = view.field("rate")
    model.interest_start_date = view.field("start_date")
    model.payment_method = view.field("payment_method")
    model.has_iou = view.loan_claim_page.get_has_iou()
    model.demand_date = view.field("demand_date")
    model.demand_method = view.field("demand_method")
    model.court_name = view.field("court_name")


def _fill_contract(view, model):
    model.contract_date = view.field("c_contract_date")
    model.contract_name = view.field("c_contract_name")
    model.product_name = view.field("c_product_name")
    model.total_amount = view.field("c_total_amount")
    model.delivery_date = view.field("c_delivery_date")
    model.unpaid_amount = view.field("c_unpaid_amount")
    model.penalty_amount = view.field("c_penalty_amount")
    model.penalty_start_date = view.field("c_overdue_start")

    lpr_value = _text(view.field("c_lpr_value"))
    lpr_multiple = _text(view.field("c_lpr_multiple"))
    # Only describe a calculation standard when the user actually supplied both
    # parameters; otherwise leave it empty so no misleading "%%×" text is drawn.
    if lpr_value and lpr_multiple:
        model.penalty_calc_standard = f"{lpr_value}%×{lpr_multiple}"
    else:
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
    "contract": _fill_contract,
    "property": _fill_property,
    "labor": _fill_labor,
    "divorce": _fill_divorce,
}


def build_case_model(view):
    """Return a populated case model for the wizard's current selection."""
    case_type = view.field("case_type")
    model = _model_for(case_type)

    _add_parties(model, view.party_page.get_party_data())

    filler = _FILLERS.get(case_type, _fill_loan)
    filler(view, model)

    for name, target in view.evidence_page.get_evidence_items():
        model.evidences.append(EvidenceItem(name, target))

    return model
