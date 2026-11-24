# File: models/case_model.py
# Purpose: Data models for the lawsuit
# Encoding: UTF-8
"""Case models for the five supported categories.

Numeric parsing, money formatting and the reusable calculations live in
:mod:`models.calculations`; full-date parsing and the structured validation
contract live in :mod:`models.validation`. The historical module-level names
(``CalculationError``, ``_to_decimal``, ``_format_money``, ``parse_month_range``)
are re-exported here so existing callers keep working unchanged.
"""

import datetime
import re
from decimal import Decimal, InvalidOperation

from models.calculations import (  # noqa: F401  (compatibility re-exports)
    CalculationError,
    calculate_property_fee,
    format_money as _format_money,
    inclusive_month_count,
    is_whole_month_span,
    parse_decimal as _to_decimal,
    parse_month_range,  # noqa: F401  (compatibility re-export)
    quantize_money,
    validate_month_range_text,
)
from models.validation import DateStatus, parse_full_date


class PartyInfo:
    def __init__(self, name="", id_number="", address="", phone="", is_company=False,
                 legal_representative="", credit_code="", gender="", birth_date="",
                 ethnicity="", occupation=""):
        self.name = name
        self.id_number = id_number
        self.address = address
        self.phone = phone
        self.is_company = is_company
        self.legal_representative = legal_representative
        self.credit_code = credit_code
        # Natural-person detail fields. ``ethnicity`` holds the resolved value
        # (the "其他" free-text choice is resolved upstream by the presenter);
        # the raw combo selection lives only in the UI and the draft payload.
        self.gender = gender
        self.birth_date = birth_date
        self.ethnicity = ethnicity
        self.occupation = occupation

#: Agent role vocabulary shared by the party page combo and the draft schema
#: validation, so the two can never drift apart.
AGENT_TYPES = ("律师", "法律工作者", "近亲属", "工作人员", "公民代理")

#: Rental-contract status vocabulary shared by the claim page, the model and
#: the draft schema; ``None`` means the user has not classified it yet.
RENTAL_LEASE_STATUSES = ("active", "terminated", "request_termination")
RENTAL_LEASE_LABELS = {
    "active": "继续履行",
    "terminated": "已解除",
    "request_termination": "请求解除",
}

class AgentInfo:
    """Case-level optional litigation agent standing on the plaintiff's side."""

    def __init__(self, name="", type="", org="", phone=""):
        self.name = name
        self.type = type
        self.org = org
        self.phone = phone

class PartyManager:
    def __init__(self):
        self.plaintiffs = [] # List of PartyInfo
        self.defendants = [] # List of PartyInfo

    def add_party(self, party_type, data):
        """
        party_type: 0 for Plaintiff, 1 for Defendant
        data: PartyInfo instance
        """
        if party_type == 0:
            self.plaintiffs.append(data)
        else:
            self.defendants.append(data)

class EvidenceItem:
    def __init__(self, name="", target=""):
        self.name = name
        self.target = target

class CaseTemplate:
    """Base class for all case types."""
    #: The final claim shared by every current case model. User-supplied
    #: claims are inserted before it so it stays last, as court templates
    #: conventionally place the litigation-cost request at the end.
    LITIGATION_COST_CLAIM = "本案诉讼费由被告承担。"

    def __init__(self):
        self.case_type_name = "未命名案由"
        self.party_manager = PartyManager()
        self.agent = None # Optional[AgentInfo]
        self.court_name = ""
        self.evidences = [] # List of EvidenceItem
        # User-supplied additions. They never replace the generated content;
        # the document writers append them with an explicit label.
        self.extra_claims = []
        self.extra_facts = ""

    def render_claims(self):
        """Return a list of string claims."""
        return []

    def render_facts(self):
        """Return a formatted string of facts and reasons."""
        return ""

    def _normalized_extra_claims(self):
        raw_claims = self.extra_claims
        if isinstance(raw_claims, str):
            raw_claims = raw_claims.splitlines()
        normalized = []
        for raw in raw_claims or []:
            text = str(raw or "").strip().rstrip("；;。")
            if text:
                normalized.append(f"{text}；")
        return normalized

    def all_claims(self):
        """Return generated claims with user-supplied additions.

        Additions are inserted before the final litigation-cost claim; an
        empty addition list leaves the generated claims untouched.
        """
        claims = list(self.render_claims())
        extras = self._normalized_extra_claims()
        if not extras:
            return claims
        if claims and claims[-1] == self.LITIGATION_COST_CLAIM:
            return claims[:-1] + extras + [claims[-1]]
        return claims + extras

    def all_facts(self):
        """Return generated facts plus the optional user-supplied note."""
        facts = (self.render_facts() or "").strip()
        extra = (self.extra_facts or "").strip()
        if not extra:
            return facts
        if not facts:
            return f"补充说明：{extra}"
        return f"{facts}\n\n补充说明：{extra}"

class LoanCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "民间借贷纠纷"

        # Structured fact fields
        self.loan_date = ""
        self.loan_reason = ""
        self.principal_amount = ""
        self.payment_method = ""
        self.interest_rate = ""
        self.interest_start_date = ""
        self.has_iou = None
        self.demand_date = ""
        self.demand_method = ""

    def _interest_cutoff_date(self):
        """Cutoff used when temporarily estimating interest until filing."""
        return datetime.date.today()

    def render_claims(self):
        claims = []
        claims.append(f"判令被告向原告偿还借款本金人民币 {self.principal_amount} 元；")
        if self.interest_rate and self.interest_start_date:
            try:
                start = self._parse_date(self.interest_start_date)
                if start is None:
                    raise CalculationError("利息起算日格式无法识别")
                cutoff = self._interest_cutoff_date()
                days = (cutoff - start).days
                if days <= 0:
                    raise CalculationError("利息起算日晚于或等于暂计截止日")
                principal = _to_decimal(self.principal_amount, "借款本金")
                rate = _to_decimal(self.interest_rate, "年利率")
                if principal is None or rate is None:
                    raise CalculationError("借款本金或年利率为空")
                if principal < 0 or rate < 0:
                    raise CalculationError("借款本金或年利率为负数")
                interest = principal * (rate / Decimal("100")) * (Decimal(days) / Decimal("365"))
                interest_str = _format_money(interest)
                claims.append(
                    f"判令被告向原告支付利息（以 {self.principal_amount} 元为基数，"
                    f"自 {self.interest_start_date} 起至实际清偿之日止，按年利率 {self.interest_rate}% 计算，"
                    f"暂计至 {cutoff.isoformat()} 为 {interest_str} 元；上述金额为按前述方式测算的参考值，"
                    f"实际金额以清偿日结算为准，利率适用性请人工核对）；"
                )
            except (CalculationError, InvalidOperation, ValueError):
                # Keep the claim neutral and editable instead of asserting a
                # legal ceiling or inventing an amount.
                claims.append(
                    f"判令被告向原告支付利息（以 {self.principal_amount} 元为基数，"
                    f"自 {self.interest_start_date} 起至实际清偿之日止，按年利率 {self.interest_rate}% 计算，"
                    f"具体金额以实际清偿日结算为准，利率适用性请人工核对）；"
                )
        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        # The opening is drawn only from supplied facts; no party relationship
        # (such as "friends") is asserted.
        fact_str = (
            f"{self.loan_date}，被告因{self.loan_reason}向原告借款，"
            f"原告通过{self.payment_method}向被告支付借款本金 {self.principal_amount} 元。"
        )

        # The IOU statement is emitted only when the user explicitly confirmed
        # the state; an unconfirmed (``None``) status asserts neither outcome.
        if self.has_iou is True:
            fact_str += "被告出具了借条。"
        elif self.has_iou is False:
            fact_str += "被告未出具借条。"

        if self.interest_rate:
            fact_str += f"双方约定借款年利率为 {self.interest_rate}%。"

        # Only assert a demand when the demand fields are supplied; no demand
        # frequency ("多次") or repayment deadline is fabricated.
        if self.demand_date and self.demand_method:
            fact_str += f"原告于{self.demand_date}通过{self.demand_method}向被告催讨，被告未偿还借款。"
        else:
            fact_str += "被告未偿还借款。"

        fact_str += "为维护原告合法权益，特诉至贵院，请依法支持原告的诉讼请求。"
        return fact_str

    @staticmethod
    def _parse_date(text):
        """Delegate to the shared full-date validation (never raises)."""
        result = parse_full_date(text)
        return result.value if result.status == DateStatus.VALID else None

class ContractCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "买卖合同纠纷"

        self.contract_date = ""
        self.contract_name = ""
        self.product_name = ""
        self.total_amount = ""
        self.delivery_date = ""
        # Tri-state: None = not confirmed, True = delivered, False = not delivered.
        self.is_delivered = None
        self.is_signed = None
        self.unpaid_amount = ""
        self.penalty_amount = ""
        self.penalty_start_date = ""
        # Explicit user-entered cutoff for the penalty calculation. Kept on the
        # model so the calculation basis cannot drift between UI and document.
        self.penalty_cutoff_date = ""
        # Provenance of penalty_amount: set only while it is the untouched
        # result of an auxiliary calculator run ("daily_5_per_10k" or
        # "lpr_multiple") with unchanged inputs; a manually typed amount
        # carries no calculation basis and no cutoff may be claimed for it.
        self.penalty_calc_method = ""
        self.penalty_calc_cutoff = ""
        self.penalty_calc_standard = ""
        # Legacy placeholder kept for compatibility; never populated or read.
        self.liquidated_damages_formula = ""

    def render_claims(self):
        claims = []
        claims.append(f"判令被告向原告支付货款本金人民币 {self.unpaid_amount} 元；")
        if self.penalty_amount:
            if (self.penalty_calc_method and self.penalty_calc_cutoff
                    and self.penalty_start_date and self.penalty_calc_standard):
                # The description must match the calculator that actually
                # produced the amount: the daily 万五 convention is the tool's
                # own auxiliary standard, while the LPR standard comes from
                # user-entered parameters.
                if self.penalty_calc_method == "daily_5_per_10k":
                    basis_note = "该折算口径为本工具的辅助约定，具体适用请结合合同约定与法律规定人工核对"
                else:
                    basis_note = "上述计算标准由当事人填写，具体适用请结合合同约定与法律规定人工核对"
                claims.append(
                    f"判令被告向原告支付逾期付款违约金（以 {self.unpaid_amount} 元为基数，"
                    f"自 {self.penalty_start_date} 起按 {self.penalty_calc_standard} 计算至实际清偿之日止，"
                    f"暂计至 {self.penalty_calc_cutoff} 为 {self.penalty_amount} 元；{basis_note}）；"
                )
            else:
                # No verified calculation basis: no cutoff date may be asserted.
                claims.append(f"判令被告向原告支付违约金（或逾期付款利息）人民币 {self.penalty_amount} 元；")
        claims.append("本案诉讼费由被告承担。")
        return claims

    def delivery_receipt_conflict(self):
        """True when the explicit delivery/receipt states contradict each other."""
        return self.is_delivered is False and self.is_signed is True

    def render_facts(self):
        fact_str = (
            f"原告与被告于{self.contract_date}签订了《{self.contract_name}》，"
            f"约定被告向原告采购{self.product_name}，总金额为 {self.total_amount} 元。"
        )

        # Delivery is tri-state: assert only what the user explicitly confirmed.
        if self.is_delivered is True:
            fact_str += f"原告已于{self.delivery_date}完成交货。"
        elif self.is_delivered is False:
            fact_str += "原告尚未完成交货。"
        else:
            fact_str += "关于货物是否已经交付，现有材料尚未确认，需人工核对后补充。"

        # Receipt is tri-state as well. A contradiction between the two states is
        # flagged for review instead of silently producing a self-contradictory
        # narrative.
        if self.delivery_receipt_conflict():
            fact_str += "（提示：交货状态与签收状态相互矛盾，请人工核对并修正后再行提交。）"
        elif self.is_signed is True:
            fact_str += "被告已签收。"
        elif self.is_signed is False:
            # Failure to sign is stated without asserting a reason for it.
            fact_str += "被告尚未签收。"
        # None → the receipt assertion is omitted entirely.

        # The complaint must not assert a payment demand (single or repeated)
        # that the user never supplied: the sales-contract inputs establish the
        # contract, delivery, signing status and the outstanding balance only.
        # The unpaid amount is therefore stated on its own, without inventing a
        # demand action.
        amount = (self.unpaid_amount or "").strip()
        if amount:
            fact_str += f"被告至今尚欠货款 {amount} 元未付。"
        else:
            fact_str += "被告尚欠原告货款，具体金额以双方核对及相关证据为准。"
        fact_str += "为维护原告合法权益，特诉至贵院。"
        return fact_str

class RentalCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "租赁合同纠纷"

        self.property_address = ""
        self.contract_date = ""
        self.lease_start = ""
        self.lease_end = ""
        self.monthly_rent = ""
        self.payment_cycle = ""
        self.arrears_start = ""
        self.arrears_end = ""
        self.arrears_amount = ""
        self.late_fee = ""
        self.demand_record = ""
        # ``None`` means the user has not classified the contract status.
        self.lease_status = None
        self.termination_date = ""
        self.property_returned = None

    def _return_claim_allowed(self):
        return (
            self.lease_status in ("terminated", "request_termination")
            and self.property_returned is False
        )

    def render_claims(self):
        claims = []
        if self.lease_status == "request_termination":
            claims.append(
                f"判令解除原告与被告之间关于{self.property_address}的房屋租赁合同；"
            )

        period = ""
        if self.arrears_start and self.arrears_end:
            period = f"（欠租期间自 {self.arrears_start} 起至 {self.arrears_end} 止）"
        elif self.arrears_start:
            period = f"（自 {self.arrears_start} 起）"
        claims.append(
            f"判令被告向原告支付欠付租金人民币 {self.arrears_amount} 元{period}；"
        )

        if self.late_fee:
            claims.append(f"判令被告支付违约金（滞纳金）人民币 {self.late_fee} 元；")

        if self._return_claim_allowed():
            claims.append(f"判令被告腾退并返还位于{self.property_address}的房屋；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        fact_str = (
            f"原告与被告于{self.contract_date}签订《房屋租赁合同》，"
            f"约定原告将位于{self.property_address}的房屋出租给被告，"
            f"租赁期限自{self.lease_start}至{self.lease_end}，"
            f"月租金{self.monthly_rent}元，租金支付方式为{self.payment_cycle}。"
        )

        if self.arrears_start:
            period = f"自{self.arrears_start}起"
            if self.arrears_end:
                period += f"至{self.arrears_end}"
            fact_str += f"被告{period}未按约支付租金，尚欠租金{self.arrears_amount}元。"
        else:
            fact_str += f"被告尚欠原告租金{self.arrears_amount}元。"

        demand = (self.demand_record or "").strip()
        if demand:
            if demand[-1] not in "。！？.!?":
                demand += "。"
            fact_str += f"原告曾向被告催缴，催缴情况如下：{demand}但被告至今未支付。"

        if self.lease_status == "request_termination":
            fact_str += "原告因被告欠付租金，请求解除双方租赁合同。"
        elif self.lease_status == "terminated":
            if self.termination_date:
                fact_str += f"双方租赁合同已于{self.termination_date}解除。"
            else:
                fact_str += "双方租赁合同已经解除，解除日期尚需人工核对。"
        elif self.lease_status == "active":
            fact_str += "双方租赁合同仍在履行中。"

        if self.lease_status in ("terminated", "request_termination"):
            if self.property_returned is True:
                fact_str += "被告已腾退并返还房屋。"
            elif self.property_returned is False:
                fact_str += "被告尚未腾退返还房屋。"

        fact_str += "为维护原告合法权益，特诉至贵院。"
        return fact_str


class PropertyCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "物业服务合同纠纷"

        self.property_addr = ""
        self.house_area = ""
        self.fee_rate = ""
        self.period_start = ""
        self.period_end = ""
        self.late_fee_logic = ""
        self.demand_record = ""
        self.total_principal = ""
        self.months = 0
        self.is_partial_billing = False

    def _calc_months_detail(self):
        """Return ``(months, is_partial)`` for the billing period.

        ``is_partial`` is ``True`` when the period does not start on the first
        day and end on the last day of a month, i.e. the whole-calendar-month
        assumption may not hold. Reversed or unparseable periods return
        ``(0, False)``. Dates are parsed by the shared full-date validation in
        :mod:`models.validation`; the month arithmetic comes from the shared
        helpers in :mod:`models.calculations`.
        """
        start_result = parse_full_date(self.period_start)
        end_result = parse_full_date(self.period_end)
        if start_result.status != DateStatus.VALID or end_result.status != DateStatus.VALID:
            return 0, False
        start, end = start_result.value, end_result.value
        if end < start:
            return 0, False
        return inclusive_month_count(start, end), not is_whole_month_span(start, end)

    def _calc_months(self):
        return self._calc_months_detail()[0]

    def _calc_total(self):
        """Delegate to the single authoritative property-fee calculation."""
        return calculate_property_fee(
            self.house_area, self.fee_rate, self.period_start, self.period_end
        ).total

    def _resolved_principal(self):
        """Return the principal string to print without discarding user input."""
        months, partial = self._calc_months_detail()
        self.months = months
        self.is_partial_billing = partial
        computed = self._calc_total() if months else None
        user_total = (self.total_principal or "").strip()
        if user_total:
            # Never silently overwrite a user-entered total.
            return user_total
        if computed is not None:
            self.total_principal = f"{computed}"
            return self.total_principal
        return self.total_principal

    def render_claims(self):
        total_str = self._resolved_principal()

        claims = []
        claims.append(f"判令被告向原告支付自 {self.period_start} 起至 {self.period_end} 止的物业费共计 {total_str} 元；")
        if self.late_fee_logic:
            claims.append(f"判令被告支付违约金（滞纳金）：{self.late_fee_logic}；")
        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        total_str = self._resolved_principal()

        plaintiff_name = self.party_manager.plaintiffs[0].name if self.party_manager.plaintiffs else ""
        defendant_name = self.party_manager.defendants[0].name if self.party_manager.defendants else ""

        # The current inputs do not establish the existence, signature or
        # content of a property-service contract, nor the defendant's ownership
        # of the unit. These are therefore framed as the plaintiff's claim, and
        # the contract details are explicitly flagged as requiring manual
        # confirmation rather than being asserted as accomplished facts.
        fact_str = (
            f"{plaintiff_name}主张其为涉案小区提供物业服务。原告主张被告{defendant_name}与"
            f"{self.property_addr}（登记建筑面积{self.house_area}平方米）的物业费负担存在相关权利义务关系，"
            f"被告的具体身份（业主、使用人或其他）及相应责任依据需结合物业服务合同、产权资料及其他证据人工核对。"
            f"原告主张，依据物业服务合同，被告应按{self.fee_rate}元/平方米/月的标准缴纳物业管理费"
            f"（合同主体、签订时间、服务期限及具体约定以双方提供的书面合同为准，需人工核对）。"
            f"自{self.period_start}起至{self.period_end}止，原告主张被告欠付物业管理费共计{total_str}元"
            f"（欠费事实、欠费月份及金额以双方核对及缴费记录为准）。"
        )

        if self.is_partial_billing:
            fact_str += "（上述金额按整月计费估算，欠费期间存在不足整月或分段计费的情形，具体金额以双方核对及缴费记录为准。）"

        demand = (self.demand_record or "").strip()
        if demand:
            if demand[-1] not in "。！？.!?":
                demand += "。"
            fact_str += f"原告曾向被告催缴，催缴情况如下：{demand}但被告至今未缴纳。"
        # When no demand record is supplied, no demand frequency ("多次"),
        # bad-faith ("无故") or legal-conclusion ("已构成违约") assertion is
        # fabricated; the demand statement is simply omitted.

        fact_str += "综上，为维护原告合法权益，特提起诉讼，请依法支持原告的诉讼请求。"
        return fact_str

class DivorceCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "离婚析产/抚养费纠纷"

        self.marriage_date = ""
        self.child_name = ""
        self.child_birthday = ""
        self.custody_preference = ""
        self.support_monthly = ""
        self.divorce_reason = ""
        self.separation_start_date = ""
        self.asset_description = ""

    def _custody_phrase(self):
        """Return the custodian wording without a leading "由" or trailing "抚养"."""
        phrase = (self.custody_preference or "").strip().rstrip("。；;，,")
        if phrase.startswith("由"):
            phrase = phrase[1:]
        for suffix in ("直接抚养", "抚养"):
            if phrase.endswith(suffix):
                phrase = phrase[: -len(suffix)]
                break
        return phrase.strip()

    def _custodian(self):
        """Return "原告" / "被告" when the custodian is unambiguous, else ``""``."""
        phrase = self._custody_phrase()
        for role in ("原告", "被告"):
            if phrase == role:
                return role
        return ""

    def render_claims(self):
        claims = []

        # The core divorce request must always be present in an actual
        # divorce complaint.
        claims.append("判令原告与被告离婚；")

        child = self.child_name.strip()
        support = self.support_monthly.strip()
        has_custody = bool(child and self._custody_phrase())

        # When the defendant raises the child, the support amount is what the
        # plaintiff offers to pay; it must never be claimed against the
        # defendant who would be raising the child.
        if has_custody and self._custodian() == "被告" and support:
            claims.append(
                f"判令婚生子女{child}由被告抚养，原告按月支付抚养费人民币{support}元，"
                f"至子女年满18周岁止；"
            )
        else:
            if has_custody:
                claims.append(f"判令婚生子女{child}由{self._custody_phrase()}抚养；")

            # A child-support claim requires an identified child: an amount
            # entered without a child identity is not a supportable claim and
            # must not be turned into one.
            if support and child:
                claims.append(f"判令被告按月支付抚养费人民币{support}元，至子女年满18周岁止；")

        if self.asset_description.strip():
            claims.append(f"判令依法分割夫妻共同财产：{self.asset_description}；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        fact_str = f"原告与被告于{self.marriage_date}登记结婚。"

        if self.child_name.strip():
            birthday = f"于{self.child_birthday}" if self.child_birthday.strip() else ""
            fact_str += f"婚后{birthday}生育子女，取名{self.child_name}。"

        if self.separation_start_date.strip():
            fact_str += f"双方自{self.separation_start_date}起分居至今。"

        if self.divorce_reason.strip():
            fact_str += f"原告主张的离婚原因：{self.divorce_reason.strip().rstrip('。')}。"

        # When no divorce reason is supplied, no marital-dissension fact (such
        # as "生活琐事产生矛盾") is invented; the reason is simply omitted and
        # the appellant's legal conclusion is stated separately below.

        fact_str += "原告认为，双方感情确已破裂，已无和好可能。"

        child = self.child_name.strip()
        support = self.support_monthly.strip()
        if child and self._custody_phrase():
            custody = self._custody_phrase()
            fact_str += f"关于子女抚养：原告认为由{custody}抚养更有利于子女健康成长。"
            if support:
                if self._custodian() == "被告":
                    fact_str += f"原告愿按月支付抚养费{support}元。"
                else:
                    fact_str += f"被告应按月支付抚养费{support}元。"
        elif child and support:
            fact_str += f"关于子女抚养：被告应按月支付抚养费{support}元。"
        # A support amount without an identified child produces no child-support
        # assertion (the wizard blocks that incomplete combination).

        # Property-division facts depend on the property input, not on support.
        if self.asset_description.strip():
            fact_str += f"关于夫妻共同财产：双方共有财产包括{self.asset_description}，请求依法分割。"

        if self.child_name.strip():
            fact_str += "综上，为维护原告及子女合法权益，特提起诉讼。"
        else:
            fact_str += "综上，为维护原告合法权益，特提起诉讼。"
        return fact_str

class LaborCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "劳动争议"

        self.emp_join_date = ""
        self.emp_term_date = ""
        self.job_title = ""
        self.monthly_salary = ""
        self.unpaid_months = ""
        self.overtime_pay = ""
        # Tri-state: None = 未确认, True = 未签订书面劳动合同, False = 已签订.
        self.is_no_contract = None
        self.social_sec_info = ""
        self.total_unpaid_amount = ""
        self.overtime_hours = ""
        # Procedural classification (vocabulary and eligibility rules live in
        # utils.labor_security; the export gate runs the same evaluator). All
        # classification fields start unconfirmed and are never inferred.
        self.labor_procedure = None
        self.labor_refusal_ground = None
        self.labor_role = None
        self.labor_delay_exception = None
        self.arb_commission = ""
        self.arb_case_no = ""
        self.arb_receipt_date = ""
        self.arb_application_date = ""
        self.arb_acceptance_date = ""

    def resolve_unpaid_month_count(self):
        """Return ``(months, is_partial)`` for the unpaid-salary period.

        Raises :class:`CalculationError` for empty, malformed or reversed input
        instead of returning a misleading zero.
        """
        return parse_month_range(self.unpaid_months)

    def _unpaid_period_result(self):
        """Structured validation of the unpaid-period input (shared contract).

        Consumed by :meth:`_ensure_unpaid_total` so the model's neutral
        fallback branches on the same validation contract the rest of the
        application uses.
        """
        return validate_month_range_text(self.unpaid_months, field="l_unpaid_months")

    def _calc_unpaid_amount(self):
        """Return the unpaid total as a Decimal, or raise ``CalculationError``."""
        salary = _to_decimal(self.monthly_salary, "月工资标准")
        if salary is None:
            raise CalculationError("未填写月工资标准")
        if salary < 0:
            raise CalculationError("月工资标准为负数")
        months, is_partial = self.resolve_unpaid_month_count()
        total = quantize_money(salary * Decimal(months))
        return total, months, is_partial
    def _ensure_unpaid_total(self):
        """Populate ``total_unpaid_amount`` when the inputs are fully specified."""
        if not self._unpaid_period_result().is_valid:
            return None
        try:
            total, months, is_partial = self._calc_unpaid_amount()
        except CalculationError:
            return None
        self.total_unpaid_amount = f"{total}"
        return months, is_partial

    def render_claims(self):
        claims = []
        summary = self._ensure_unpaid_total()
        if summary is not None:
            months, is_partial = summary
            suffix = "（该区间含不完整或推断月份，具体金额请人工核对）" if is_partial else ""
            claims.append(
                f"判令被告向原告支付欠付工资共计人民币 {self.total_unpaid_amount} 元{suffix}；"
            )
        else:
            # Do not guess an entitlement amount; keep an explicit placeholder.
            claims.append("判令被告向原告支付欠付工资（具体欠薪月份及金额请依据工资条、银行流水等证据人工确认后填写）；")

        if self.overtime_pay:
            claims.append(f"判令被告向原告支付加班费人民币 {self.overtime_pay} 元；")

        if self.is_no_contract is True:
            claims.append("判令被告向原告支付未签订书面劳动合同的二倍工资差额；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def _arbitration_sentence(self):
        """State the prior arbitration exactly as the user classified it.

        Each supported procedural state produces one sentence asserting only
        the facts the user entered — the actual document type and dates — and
        never the old combined “仲裁裁决书（或不予受理通知书）” wording.
        Anything not classified as eligible by the shared evaluator produces
        no arbitration sentence at all (the export gate blocks earlier with
        the evaluator's own explanation).
        """
        from utils.labor_security import (
            PROCEDURE_ACCEPTANCE_OVERDUE,
            PROCEDURE_AWARD_OVERDUE,
            PROCEDURE_FINAL_AWARD,
            PROCEDURE_NON_FINAL_AWARD,
            PROCEDURE_NOT_ACCEPTED,
            evaluate_labor_eligibility,
        )

        eligibility = evaluate_labor_eligibility(
            self.labor_procedure,
            refusal_ground=self.labor_refusal_ground,
            role=self.labor_role,
            delay_exception=self.labor_delay_exception,
            commission=self.arb_commission,
            application_date=self.arb_application_date,
            acceptance_date=self.arb_acceptance_date,
            receipt_date=self.arb_receipt_date,
        )
        if not eligibility.eligible:
            return ""

        commission = (self.arb_commission or "").strip()
        case_no = (self.arb_case_no or "").strip()
        suffix = f"（案号：{case_no}）" if case_no else ""
        receipt = (self.arb_receipt_date or "").strip()

        if self.labor_procedure == PROCEDURE_NOT_ACCEPTED:
            return (
                f"原告曾就上述争议向{commission}申请劳动仲裁{suffix}，"
                f"并于{receipt}收到该委员会作出的不予受理书面决定（通知书）。"
                "原告不服，现依法向人民法院提起诉讼。"
            )
        if self.labor_procedure == PROCEDURE_ACCEPTANCE_OVERDUE:
            application = (self.arb_application_date or "").strip()
            return (
                f"原告于{application}就上述争议向{commission}申请劳动仲裁{suffix}，"
                "该委员会至今未作出是否受理的决定。"
                "依据《中华人民共和国劳动争议调解仲裁法》第二十九条，"
                "原告就该劳动争议事项向人民法院提起诉讼。"
            )
        if self.labor_procedure == PROCEDURE_AWARD_OVERDUE:
            acceptance = (self.arb_acceptance_date or "").strip()
            return (
                f"原告曾就上述争议向{commission}申请劳动仲裁{suffix}，"
                f"该委员会于{acceptance}受理。受理后至今，该委员会未作出仲裁裁决。"
                "依据《中华人民共和国劳动争议调解仲裁法》第四十三条第二款，"
                "原告就该劳动争议事项向人民法院提起诉讼。"
            )
        if self.labor_procedure == PROCEDURE_NON_FINAL_AWARD:
            return (
                f"原告曾就上述争议向{commission}申请劳动仲裁{suffix}，"
                f"并于{receipt}收到该委员会作出的非终局仲裁裁决书。"
                "原告对该裁决不服，现依法向人民法院提起诉讼。"
            )
        if self.labor_procedure == PROCEDURE_FINAL_AWARD:
            return (
                f"原告曾就上述争议向{commission}申请劳动仲裁{suffix}，"
                f"并于{receipt}收到该委员会作出的终局裁决。"
                "原告对该裁决不服，现依法向人民法院提起诉讼。"
            )
        # Unreachable while the evaluator and the state set agree.
        return ""

    def render_facts(self):
        summary = self._ensure_unpaid_total()
        if summary is not None:
            amount_text = f"共计欠付原告工资{self.total_unpaid_amount}元"
        else:
            amount_text = "存在欠付工资情形，具体金额以工资条、银行流水等证据为准"

        fact_str = (
            f"原告于{self.emp_join_date}入职被告处，岗位为{self.job_title}，"
            f"双方约定月工资标准为{self.monthly_salary}元。"
            f"被告未按时足额支付原告{self.unpaid_months}期间的工资。"
        )
        term = (self.emp_term_date or "").strip()
        if term:
            fact_str += f"截至{term}，被告{amount_text}。"
        else:
            fact_str += f"被告{amount_text}。"

        if self.overtime_pay and self.overtime_hours:
            fact_str += f"此外，原告在职期间存在{self.overtime_hours}小时的加班，被告亦未支付加班费{self.overtime_pay}元。"

        if self.is_no_contract is True:
            fact_str += (
                "原告入职后，被告未与原告订立书面劳动合同。原告依据《中华人民共和国劳动合同法》"
                "第八十二条的规定，主张被告支付未订立书面劳动合同的二倍工资差额。"
            )

        fact_str += self._arbitration_sentence()
        fact_str += "为维护原告合法权益，特诉至贵院，请依法支持原告的诉讼请求。"
        return fact_str
