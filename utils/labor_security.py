# File: utils/labor_security.py
# Purpose: Procedural notices for labor dispute cases
# Encoding: UTF-8

# Last review time of the arbitration-precondition wording against the cited
# regulation. Shown in the UI so the notice never reads as a universally
# current conclusion without a basis time.
ARBITRATION_NOTICE_BASIS = (
    "依据：《劳动争议调解仲裁法》关于“先裁后审”的规定；"
    "整理时间：2026-11，请以最新法律及当地仲裁/法院实践为准。"
)


class LaborProcedureGuard:
    def get_warning_text(self):
        """Full procedural notice shown on the case-selection page."""
        return (
            "【法律程序风险提示】\n\n"
            "1. 先裁后审：劳动争议一般须先向劳动人事争议仲裁委员会申请仲裁，对仲裁裁决不服的，"
            "方可在收到裁决书之日起 15 日内向人民法院起诉；未经仲裁直接起诉的，法院通常不予受理。\n\n"
            "2. 例外情形：劳动者仅以用人单位出具的工资欠条为证据直接起诉，且诉讼请求不涉及劳动关系"
            "其他争议的，法院可按普通民事纠纷受理（参见最高人民法院劳动争议司法解释（一）第十五条）。\n\n"
            "3. 本工具当前只生成仲裁之后向法院起诉所用的起诉状；尚未申请仲裁的，"
            "请先向当地劳动人事争议仲裁委员会申请仲裁。"
        )

    def get_persistent_notice(self):
        """Concise arbitration-precondition notice with an explicit basis time.

        Intended for the labour claim page's always-visible reminder; the full
        :meth:`get_warning_text` remains on the case-selection page.
        """
        return (
            "【仲裁前置程序提示】劳动争议一般须先向劳动人事争议仲裁委员会申请仲裁，"
            "对仲裁裁决不服方可向法院起诉；未经仲裁直接起诉的，法院通常不予受理。\n"
            + ARBITRATION_NOTICE_BASIS
        )

    def get_not_arbitrated_text(self):
        """Blocking guidance shown when the user has not applied for arbitration."""
        return (
            "您选择了“尚未申请劳动仲裁”。本工具当前只能生成仲裁之后向法院起诉所用的起诉状，"
            "不能为本阶段生成文书。请先向用人单位所在地或劳动合同履行地的劳动人事争议仲裁委员会"
            "申请仲裁；劳动仲裁申请书的生成将在后续版本提供。"
        )
