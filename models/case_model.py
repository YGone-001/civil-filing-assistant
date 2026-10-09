# File: models/case_model.py
# Purpose: Data models for the lawsuit
# Encoding: UTF-8

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

    def render_claims(self):
        claims = []
        claims.append(f"判令被告向原告偿还借款本金人民币 {self.principal_amount} 元；")
        if self.interest_rate and self.interest_start_date:
            try:
                import datetime
                import re

                # Try to parse start date
                start_str = re.sub(r'[^\d]', '-', self.interest_start_date).strip('-')
                parts = start_str.split('-')
                if len(parts) >= 3:
                    d1 = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    d1 = None

                if d1:
                    d2 = datetime.date.today()
                    days = (d2 - d1).days
                    if days > 0:
                        p = float(self.principal_amount)
                        r = float(self.interest_rate) / 100.0
                        interest = p * r * (days / 365.0)
                        interest_str = f"{interest:.2f}"
                        claims.append(f"判令被告向原告支付逾期利息（以 {self.principal_amount} 元为基数，自 {self.interest_start_date} 起按年利率 {self.interest_rate}%（但最高不超过合同成立时一年期 LPR 的 4 倍）计算至实际清偿之日止，暂计至起诉之日为 {interest_str} 元）；")
                    else:
                        raise ValueError("Days <= 0")
                else:
                    raise ValueError("Invalid date format")
            except Exception:
                # Fallback to normal text if calculation fails
                claims.append(f"判令被告向原告支付利息（以 {self.principal_amount} 元为基数，自 {self.interest_start_date} 起至实际清偿之日止，按年利率 {self.interest_rate}%（但最高不超过合同成立时一年期 LPR 的 4 倍）计算）；")
        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        iou_text = "出具了借条" if self.has_iou else "未出具借条"

        fact_str = (
            f"原告与被告系朋友关系。{self.loan_date}，被告因{self.loan_reason}需要向原告借款，"
            f"原告通过{self.payment_method}向被告交付借款本金 {self.principal_amount} 元，被告{iou_text}。"
        )

        if self.interest_rate:
            fact_str += f"双方约定借款年利率为 {self.interest_rate}%。"

        fact_str += (
            f"此后，原告于{self.demand_date}通过{self.demand_method}多次催讨，"
            f"被告至今未能偿还借款。为维护原告合法权益，特诉至贵院，请依法支持原告的诉讼请求。"
        )
        return fact_str

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
                claims.append(f"判令被告向原告支付逾期付款违约金（以 {self.unpaid_amount} 元为基数，自 {self.penalty_start_date} 起按 {self.penalty_calc_standard} 计算至实际清偿之日止，暂计至起诉之日为 {self.penalty_amount} 元）；")
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
                fact_str += "但被告无理拒绝签收。"
        else:
            fact_str += "目前尚未完成交货。"

        fact_str += (
            f"经原告多次催告，被告至今尚欠货款 {self.unpaid_amount} 元未付。为维护原告合法权益，特诉至贵院。"
        )
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

    def _parse_date(self, text):
        import datetime
        import re
        s = (text or "").strip()
        if not s:
            return None
        s2 = re.sub(r"[^\d]", "-", s).strip("-")
        parts = s2.split("-")
        if len(parts) < 3:
            return None
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))

    def _calc_months(self):
        d1 = self._parse_date(self.period_start)
        d2 = self._parse_date(self.period_end)
        if not d1 or not d2:
            return 0
        if d2 < d1:
            return 0
        return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1

    def _calc_total(self):
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
        try:
            area = Decimal(str(self.house_area).strip())
            rate = Decimal(str(self.fee_rate).strip())
            months = Decimal(str(self.months))
            total = (area * rate * months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return total
        except (InvalidOperation, ValueError):
            return None

    def render_claims(self):
        self.months = self._calc_months()
        total = self._calc_total()
        total_str = self.total_principal
        if total is not None:
            total_str = f"{total}"
            self.total_principal = total_str

        claims = []
        claims.append(f"判令被告向原告支付自 {self.period_start} 起至 {self.period_end} 止的物业费共计 {total_str} 元；")
        if self.late_fee_logic:
            claims.append(f"判令被告支付违约金（滞纳金）：{self.late_fee_logic}；")
        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        self.months = self._calc_months()
        total = self._calc_total()
        total_str = self.total_principal
        if total is not None:
            total_str = f"{total}"
            self.total_principal = total_str

        plaintiff_name = self.party_manager.plaintiffs[0].name if self.party_manager.plaintiffs else ""
        defendant_name = self.party_manager.defendants[0].name if self.party_manager.defendants else ""

        fact_str = (
            f"{plaintiff_name}系涉案小区的物业服务企业。原告与相关主体签署了《物业服务合同》，约定由原告为该小区提供物业管理服务。"
            f"被告{defendant_name}系该小区{self.property_addr}的业主。该房屋登记建筑面积为{self.house_area}平方米。"
            f"根据合同约定，被告应按{self.fee_rate}元/平方米/月的标准向原告缴纳物业管理费。"
            f"自{self.period_start}起至{self.period_end}止，被告已连续{self.months}个月未缴纳物业管理费，共计欠费{total_str}元。"
        )

        if self.demand_record:
            fact_str += f"原告曾通过{self.demand_record}多次向被告履行催告义务，但被告至今仍无故拖欠，其行为已构成违约。"
        else:
            fact_str += "原告曾多次向被告履行催告义务，但被告至今仍无故拖欠，其行为已构成违约。"

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
        self.asset_description = ""

    def render_claims(self):
        claims = []

        if self.custody_preference:
            claims.append(f"判令婚生子/女{self.child_name}由原告{self.custody_preference}抚养；")

        if self.support_monthly:
            claims.append(f"判令被告按月支付抚养费人民币{self.support_monthly}元，至子女年满18周岁止；")

        if self.asset_description:
            claims.append(f"判令依法分割夫妻共同财产：{self.asset_description}；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        plaintiff_name = self.party_manager.plaintiffs[0].name if self.party_manager.plaintiffs else ""
        defendant_name = self.party_manager.defendants[0].name if self.party_manager.defendants else ""

        fact_str = (
            f"原告与被告于{self.marriage_date}在[登记机关]登记结婚。"
            f"婚后于{self.child_birthday}生育一子/女，取名{self.child_name}。"
            f"婚后初期双方感情尚可，但由于{self.divorce_reason}，导致夫妻感情日益淡漠。"
            f"原告认为，双方感情确已破裂，已无和好可能。"
        )

        if self.custody_preference:
            fact_str += f"关于子女抚养：原告认为由{self.custody_preference}抚养更有利于子女健康成长，被告应按月支付抚养费{self.support_monthly}元。"

        if self.support_monthly:
            fact_str += f"关于财产分割：双方共有财产包括{self.asset_description}。"

        fact_str += "综上，为维护原告及子女合法权益，特提起诉讼。"
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
        import datetime
        import re
        s = (text or "").strip()
        if not s:
            return None
        s2 = re.sub(r"[^\d]", "-", s).strip("-")
        parts = s2.split("-")
        if len(parts) < 3:
            return None
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))

    def _calc_unpaid_amount(self):
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
        try:
            salary = Decimal(str(self.monthly_salary).strip())
            months = Decimal(str(self._calc_unpaid_months()))
            total = (salary * months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return total
        except (InvalidOperation, ValueError):
            return None

    def _calc_unpaid_months(self):
        try:
            import re
            s = (self.unpaid_months or "").strip()
            if not s:
                return 0
            parts = re.findall(r'\d+', s)
            return len(parts)
        except Exception:
            return 0

    def render_claims(self):
        claims = []
        total_unpaid = self._calc_unpaid_amount()
        if total_unpaid is not None:
            self.total_unpaid_amount = f"{total_unpaid}"
            claims.append(f"判令被告向原告支付欠付工资共计人民币 {self.total_unpaid_amount} 元；")
        else:
            claims.append(f"判令被告向原告支付欠付工资共计人民币 {self.monthly_salary} 元；")

        if self.overtime_pay:
            claims.append(f"判令被告向原告支付加班费人民币 {self.overtime_pay} 元；")

        if self.is_no_contract:
            claims.append("判令被告向原告支付未签订书面劳动合同的二倍工资差额；")

        claims.append("本案诉讼费由被告承担。")
        return claims

    def render_facts(self):
        total_unpaid = self._calc_unpaid_amount()
        if total_unpaid is not None:
            self.total_unpaid_amount = f"{total_unpaid}"

        plaintiff_name = self.party_manager.plaintiffs[0].name if self.party_manager.plaintiffs else ""
        defendant_name = self.party_manager.defendants[0].name if self.party_manager.defendants else ""

        fact_str = (
            f"原告于{self.emp_join_date}入职被告单位，岗位为{self.job_title}，"
            f"双方约定月工资标准为{self.monthly_salary}元。原告在职期间兢兢业业，履行了岗位职责。"
            f"然而，被告自{self.unpaid_months}起，开始出现拖欠工资的行为。"
            f"截止{self.emp_term_date}，被告共计欠付原告基本工资{self.total_unpaid_amount}元。"
        )

        if self.overtime_pay and self.overtime_hours:
            fact_str += f"此外，原告在职期间存在{self.overtime_hours}小时的加班，被告亦未支付加班费{self.overtime_pay}元。"

        if self.is_no_contract:
            fact_str += "另查，入职以来被告从未与原告签订书面劳动合同，根据《劳动合同法》第82条规定，被告应当向原告每月支付二倍的工资。"

        fact_str += "综上，被告的行为严重侵害了劳动者的合法权益。现原告根据《劳动法》及《劳动合同法》之规定，请求法院判令被告支付欠薪及相关补偿。"
        return fact_str
