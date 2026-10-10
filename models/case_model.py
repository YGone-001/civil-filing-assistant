# File: models/case_model.py
# Purpose: Data models for the lawsuit
# Encoding: UTF-8

import datetime
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class CalculationError(ValueError):
    """Raised when an input cannot be parsed or a calculation is not applicable.

    Callers must treat this as "the value shown to the user is not authoritative"
    and fall back to an explicit, editable placeholder rather than inventing a
    number or silently returning zero.
    """


def _to_decimal(value, field_name):
    """Parse *value* into a finite :class:`~decimal.Decimal` or return ``None``.

    Empty input yields ``None``. Invalid input raises :class:`CalculationError`.
    """
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError):
        raise CalculationError(f"{field_name}不是有效数字：{text!r}")
    if not result.is_finite():
        raise CalculationError(f"{field_name}不是有限数字：{text!r}")
    return result


def _format_money(value):
    """Quantize a Decimal to two places and render it deterministically."""
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


_MONTH_TOKEN = re.compile(r"(\d{4})?\s*[年/\-.]?\s*(\d{1,2})")
_RANGE_SEPARATOR = re.compile(r"[至到~—–～]|\s-\s")


def parse_month_range(text):
    """Parse a month range into an inclusive month count.

    Returns a ``(months, is_partial)`` tuple. Supported inputs include::

        2023年12月至2024年2月   -> (3, False)
        2023-12 至 2024-02      -> (3, False)
        2023年12月              -> (1, False)
        2023年12月至2月         -> (3, True)   # end year inferred

    ``is_partial`` is ``True`` when the range depends on an inferred year or
    contains explicit day components, i.e. it may not be a whole number of
    fully specified monthly periods.

    Invalid or reversed ranges raise :class:`CalculationError`. Empty input also
    raises so that callers never treat "unknown" as zero.
    """
    raw = "" if text is None else str(text).strip()
    if not raw:
        raise CalculationError("未填写欠薪月份或时间段")

    # Detect explicit day components (three numeric groups in one segment).
    has_day = bool(re.search(r"\d{4}\s*[年/\-.]\s*\d{1,2}\s*[月/\-.]\s*\d{1,2}", raw))

    normalised = raw
    for ch in "年月日":
        normalised = normalised.replace(ch, "-")
    segments = [s for s in _RANGE_SEPARATOR.split(normalised) if s.strip()]
    if not segments:
        raise CalculationError(f"无法解析欠薪月份：{raw!r}")

    def parse_segment(seg):
        match = re.search(r"(\d{4})\D*(\d{1,2})", seg)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"(\d{1,2})", seg)
        if match:
            return None, int(match.group(1))
        return None, None

    start_year, start_month = parse_segment(segments[0])
    if start_month is None or not (1 <= start_month <= 12):
        raise CalculationError(f"无法解析起始月份：{raw!r}")

    if len(segments) == 1:
        if has_day:
            return 1, True
        return 1, False

    end_year, end_month = parse_segment(segments[1])
    if end_month is None or not (1 <= end_month <= 12):
        raise CalculationError(f"无法解析结束月份：{raw!r}")

    partial = has_day
    if end_year is None:
        # The end month omits its year; assume the same year, rolling over when
        # the end month precedes the start month. This is flagged as partial.
        partial = True
        end_year = start_year
        if end_month < start_month:
            end_year += 1

    if start_year is None or not (1900 <= start_year <= 2100) or not (1900 <= end_year <= 2100):
        raise CalculationError(f"年份超出合理范围：{raw!r}")

    start_index = start_year * 12 + start_month
    end_index = end_year * 12 + end_month
    if end_index < start_index:
        raise CalculationError(f"结束月份早于起始月份：{raw!r}")

    return end_index - start_index + 1, partial


class PartyInfo:
    def __init__(self, name="", id_number="", address="", phone="", is_company=False, legal_representative="", credit_code=""):
        self.name = name
        self.id_number = id_number
        self.address = address
        self.phone = phone
        self.is_company = is_company
        self.legal_representative = legal_representative
        self.credit_code = credit_code

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
    def __init__(self):
        self.case_type_name = "未命名案由"
        self.party_manager = PartyManager()
        self.court_name = ""
        self.evidences = [] # List of EvidenceItem

    def generate_loan_claim(self):
        return self.render_claims()

    def generate_sales_contract(self):
        return self.render_claims()

    def generate_property_claim(self):
        return self.render_claims()

    def render_claims(self):
        """Return a list of string claims."""
        return []

    def render_facts(self):
        """Return a formatted string of facts and reasons."""
        return ""

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
        self.has_iou = False
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
        iou_text = "出具了借条" if self.has_iou else "未出具借条"

        # The opening is drawn only from supplied facts; no party relationship
        # (such as "friends") is asserted.
        fact_str = (
            f"{self.loan_date}，被告因{self.loan_reason}向原告借款，"
            f"原告通过{self.payment_method}向被告支付借款本金 {self.principal_amount} 元，被告{iou_text}。"
        )

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
        s = (text or "").strip()
        if not s:
            return None
        s2 = re.sub(r"[^\d]", "-", s).strip("-")
        parts = s2.split("-")
        if len(parts) < 3:
            return None
        try:
            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None

class ContractCaseModel(CaseTemplate):
    def __init__(self):
        super().__init__()
        self.case_type_name = "买卖合同纠纷"

        self.contract_date = ""
        self.contract_name = ""
        self.product_name = ""
        self.total_amount = ""
        self.delivery_date = ""
        self.is_delivered = True
        self.is_signed = True
        self.unpaid_amount = ""
        self.penalty_amount = ""
        self.penalty_start_date = ""
        self.penalty_calc_standard = ""
        self.liquidated_damages_formula = ""

    def render_claims(self):
        claims = []
        claims.append(f"判令被告向原告支付货款本金人民币 {self.unpaid_amount} 元；")
        if self.penalty_amount:
            if self.penalty_start_date and self.penalty_calc_standard:
                claims.append(
                    f"判令被告向原告支付逾期付款违约金（以 {self.unpaid_amount} 元为基数，"
                    f"自 {self.penalty_start_date} 起按 {self.penalty_calc_standard} 计算至实际清偿之日止，"
                    f"暂计至起诉之日为 {self.penalty_amount} 元；上述计算标准由当事人填写，"
                    f"具体适用请结合合同约定与法律规定人工核对）；"
                )
            else:
                claims.append(f"判令被告向原告支付违约金（或逾期付款利息）人民币 {self.penalty_amount} 元；")
        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        fact_str = (
            f"原告与被告于{self.contract_date}签订了《{self.contract_name}》，"
            f"约定被告向原告采购{self.product_name}，总金额为 {self.total_amount} 元。"
        )

        if self.is_delivered:
            fact_str += f"原告已于{self.delivery_date}完成交货，"
            if self.is_signed:
                fact_str += "被告已签收。"
            else:
                # Failure to sign is stated without asserting a reason for it.
                fact_str += "被告尚未签收。"
        else:
            fact_str += "目前尚未完成交货。"

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

    def _parse_date(self, text):
        s = (text or "").strip()
        if not s:
            return None
        s2 = re.sub(r"[^\d]", "-", s).strip("-")
        parts = s2.split("-")
        if len(parts) < 3:
            return None
        try:
            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None

    def _calc_months_detail(self):
        """Return ``(months, is_partial)`` for the billing period.

        ``is_partial`` is ``True`` when the period does not start on the first
        day and end on the last day of a month, i.e. the whole-calendar-month
        assumption may not hold. Reversed or unparseable periods return
        ``(0, False)``.
        """
        d1 = self._parse_date(self.period_start)
        d2 = self._parse_date(self.period_end)
        if not d1 or not d2:
            return 0, False
        if d2 < d1:
            return 0, False
        months = (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1
        partial = not (d1.day == 1 and d2.day == self._last_day_of_month(d2))
        return months, partial

    @staticmethod
    def _last_day_of_month(day):
        if day.month == 12:
            nxt = datetime.date(day.year + 1, 1, 1)
        else:
            nxt = datetime.date(day.year, day.month + 1, 1)
        return (nxt - datetime.timedelta(days=1)).day

    def _calc_months(self):
        return self._calc_months_detail()[0]

    def _calc_total(self):
        try:
            area = _to_decimal(self.house_area, "房屋面积")
            rate = _to_decimal(self.fee_rate, "计费标准")
            months = Decimal(str(self.months))
            if area is None or rate is None:
                return None
            if area < 0 or rate < 0 or months < 0:
                return None
            total = (area * rate * months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return total
        except (CalculationError, InvalidOperation, ValueError):
            return None

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
            f"{plaintiff_name}主张其为涉案小区提供物业服务，被告{defendant_name}"
            f"系{self.property_addr}的业主或使用人，该房屋登记建筑面积为{self.house_area}平方米。"
            f"原告主张，依据物业服务合同，被告应按{self.fee_rate}元/平方米/月的标准缴纳物业管理费"
            f"（合同主体、签订时间、服务期限及具体约定以双方提供的书面合同为准，需人工核对）。"
            f"自{self.period_start}起至{self.period_end}止，原告主张被告欠付物业管理费共计{total_str}元"
            f"（欠费事实、欠费月份及金额以双方核对及缴费记录为准）。"
        )

        if self.is_partial_billing:
            fact_str += "（上述金额按整月计费估算，欠费期间存在不足整月或分段计费的情形，具体金额以双方核对及缴费记录为准。）"

        if self.demand_record:
            fact_str += f"原告曾通过{self.demand_record}向被告催缴，但被告至今未缴纳。"
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
        preference = (self.custody_preference or "").strip()
        if not preference:
            return ""
        return preference[1:] if preference.startswith("由") else preference

    def render_claims(self):
        claims = []

        # The core divorce request must always be present in an actual
        # divorce complaint.
        claims.append("判令原告与被告离婚；")

        if self.child_name.strip() and self.custody_preference.strip():
            claims.append(f"判令婚生子女{self.child_name}由{self._custody_phrase()}抚养；")

        if self.support_monthly.strip():
            claims.append(f"判令被告按月支付抚养费人民币{self.support_monthly}元，至子女年满18周岁止；")

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
            fact_str += f"婚后因{self.divorce_reason}，导致夫妻感情日益淡漠。"

        # When no divorce reason is supplied, no marital-dissension fact (such
        # as "生活琐事产生矛盾") is invented; the reason is simply omitted and
        # the appellant's legal conclusion is stated separately below.

        fact_str += "原告认为，双方感情确已破裂，已无和好可能。"

        if self.child_name.strip() and self.custody_preference.strip():
            fact_str += f"关于子女抚养：原告认为由{self._custody_phrase()}抚养更有利于子女健康成长。"
            if self.support_monthly.strip():
                fact_str += f"被告应按月支付抚养费{self.support_monthly}元。"
        elif self.support_monthly.strip():
            fact_str += f"关于子女抚养：被告应按月支付抚养费{self.support_monthly}元。"

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
        self.is_no_contract = False
        self.social_sec_info = ""
        self.total_unpaid_amount = ""
        self.overtime_hours = ""

    def _parse_date(self, text):
        s = (text or "").strip()
        if not s:
            return None
        s2 = re.sub(r"[^\d]", "-", s).strip("-")
        parts = s2.split("-")
        if len(parts) < 3:
            return None
        try:
            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None

    def resolve_unpaid_month_count(self):
        """Return ``(months, is_partial)`` for the unpaid-salary period.

        Raises :class:`CalculationError` for empty, malformed or reversed input
        instead of returning a misleading zero.
        """
        return parse_month_range(self.unpaid_months)

    def _calc_unpaid_amount(self):
        """Return the unpaid total as a Decimal, or raise ``CalculationError``."""
        salary = _to_decimal(self.monthly_salary, "月工资标准")
        if salary is None:
            raise CalculationError("未填写月工资标准")
        if salary < 0:
            raise CalculationError("月工资标准为负数")
        months, is_partial = self.resolve_unpaid_month_count()
        total = (salary * Decimal(months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return total, months, is_partial

    def _ensure_unpaid_total(self):
        """Populate ``total_unpaid_amount`` when the inputs are fully specified."""
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

        if self.is_no_contract:
            claims.append("判令被告向原告支付未签订书面劳动合同的二倍工资差额；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        summary = self._ensure_unpaid_total()
        if summary is not None:
            months, _is_partial = summary
            amount_text = f"共计欠付原告基本工资{self.total_unpaid_amount}元"
        else:
            amount_text = "存在欠付工资情形，具体金额以工资条、银行流水等证据为准"

        fact_str = (
            f"原告于{self.emp_join_date}入职被告单位，岗位为{self.job_title}，"
            f"双方约定月工资标准为{self.monthly_salary}元。"
            f"被告未按时足额支付原告{self.unpaid_months}期间的工资。"
            f"截止{self.emp_term_date}，被告{amount_text}。"
        )

        if self.overtime_pay and self.overtime_hours:
            fact_str += f"此外，原告在职期间存在{self.overtime_hours}小时的加班，被告亦未支付加班费{self.overtime_pay}元。"

        if self.is_no_contract:
            fact_str += "另查，入职以来被告从未与原告签订书面劳动合同，根据《劳动合同法》第82条规定，被告应当向原告每月支付二倍的工资。"

        fact_str += "综上，被告的行为严重侵害了劳动者的合法权益。现原告根据《劳动法》及《劳动合同法》之规定，请求法院判令被告支付欠薪及相关补偿。"
        return fact_str
