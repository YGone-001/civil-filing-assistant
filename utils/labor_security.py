# File: utils/labor_security.py
# Purpose: Safety checks for labor dispute procedures
# Encoding: UTF-8

class LaborProcedureGuard:
    def __init__(self):
        self.LABOR_CASE_ID = 4

    def check_arbitration_precondition(self, case_type_id):
        """
        Triggers a warning if user selects labor dispute.
        Must be called before rendering the first data entry step.
        """
        if case_type_id == self.LABOR_CASE_ID:
            return True
        return False

    def get_warning_text(self):
        """
        Returns Chinese warning text in UTF-8.
        Note: ASCII code only, Chinese in strings for UI rendering.
        """
        msg = (
            "【法律程序风险提示】\n\n"
            "1. 先裁后审原则：根据《劳动争议调解仲裁法》，劳动争议案件必须先向劳动争议仲裁委员会申请仲裁。"
            "未经仲裁直接向法院提起诉讼的，法院通常不予受理。\n\n"
            "2. 特例情况：若被告（用人单位）已向原告出具明确的工资欠条/债务凭证，且原告仅以该欠条为证据主张权利，"
            "可尝试直接按普通民间借贷或合同纠纷起诉。\n\n"
            "3. 建议操作：若您尚未经过仲裁程序，建议先咨询当地劳动监察大队或申请劳动仲裁。"
        )
        return msg

    def get_special_case_text(self):
        """
        Returns text for special case exception.
        """
        msg = (
            "【特例说明】\n\n"
            "若被告已出具工资欠条/债务凭证，且您仅以该欠条为证据主张权利，"
            "可尝试直接按普通民间借贷或合同纠纷起诉，不受先裁后审原则限制。"
        )
        return msg

    def get_arbitration_guide_text(self):
        """
        Returns brief guide on how to apply for labor arbitration.
        """
        msg = (
            "【劳动仲裁申请指引】\n\n"
            "1. 准备材料：劳动合同、工资条/银行流水、考勤记录、解除劳动关系证明等。\n"
            "2. 申请途径：前往当地劳动人事争议仲裁委员会或劳动监察大队。\n"
            "3. 办理流程：提交申请 → 等待受理 → 仲裁开庭 → 等待裁决。\n"
            "4. 获得裁决后：如对裁决不服，可在收到裁决书之日起15日内向人民法院提起诉讼。"
        )
        return msg
