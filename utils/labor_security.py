# File: utils/labor_security.py
# Purpose: Labour-dispute procedural classification and complaint eligibility.
# Encoding: UTF-8
"""Fact-driven labour-procedure classification and fail-closed eligibility.

The previous single tri-state (``has_arbitrated``) could not distinguish the
procedurally different ways a labour dispute reaches (or fails to reach) court,
which both over-blocked lawful paths and allowed unsafe complaints. This module
owns the classification contract:

* the finite procedural states the user may select,
* the required factual inputs per state,
* the pure eligibility evaluator shared by the wizard page (immediate hint),
  the export gate (fail-closed) and the document sentence, so the three can
  never disagree,
* the Chinese guidance text for every blocked state.

Legal basis (reviewed 2026-11, official sources only; the application never
asserts a judicial determination — court admissibility is always the court's):

* 《劳动争议调解仲裁法》第2、5、27、29、42、43、47、48、49、50、51条；
* 《最高人民法院关于审理劳动争议案件适用法律问题的解释（一）》
  （法释〔2020〕26号，2021-01-01 施行）第2、5、6、7、12、15条；
* 《最高人民法院关于审理劳动争议案件适用法律问题的解释（二）》
  （法释〔2025〕12号，2025-09-01 施行）不改变上述程序结论。

Day-count thresholds use plain calendar-day arithmetic on user-supplied dates
and are deliberately conservative (generation is allowed only once the
statutory period has fully elapsed); holidays may extend a deadline by law, so
every eligible-with-delay path carries a non-authoritative reminder instead of
a computed filing deadline.
"""

import datetime
import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Classification vocabulary (stored verbatim in draft factual_flags)
# --------------------------------------------------------------------------- #

PROCEDURE_NOT_APPLIED = "not_applied"
PROCEDURE_APPLICATION_PENDING = "application_pending"
PROCEDURE_ACCEPTANCE_OVERDUE = "acceptance_overdue"
PROCEDURE_NOT_ACCEPTED = "not_accepted"
PROCEDURE_AWARD_OVERDUE = "award_overdue"
PROCEDURE_NON_FINAL_AWARD = "non_final_award"
PROCEDURE_FINAL_AWARD = "final_award"
PROCEDURE_MEDIATION_EFFECTIVE = "mediation_effective"
PROCEDURE_OTHER_OR_UNCERTAIN = "other_or_uncertain"

#: Finite procedural states, in the order the UI offers them. ``None`` (no
#: selection yet) is the page's initial state and means "未确认".
LABOR_PROCEDURES = (
    PROCEDURE_NOT_APPLIED,
    PROCEDURE_APPLICATION_PENDING,
    PROCEDURE_ACCEPTANCE_OVERDUE,
    PROCEDURE_NOT_ACCEPTED,
    PROCEDURE_AWARD_OVERDUE,
    PROCEDURE_NON_FINAL_AWARD,
    PROCEDURE_FINAL_AWARD,
    PROCEDURE_MEDIATION_EFFECTIVE,
    PROCEDURE_OTHER_OR_UNCERTAIN,
)

#: Short labels for the procedure selector.
PROCEDURE_LABELS = {
    PROCEDURE_NOT_APPLIED: "尚未申请劳动仲裁",
    PROCEDURE_APPLICATION_PENDING: "已申请仲裁，程序进行中",
    PROCEDURE_ACCEPTANCE_OVERDUE: "申请后逾期未作出是否受理的决定",
    PROCEDURE_NOT_ACCEPTED: "已收到不予受理的书面决定",
    PROCEDURE_AWARD_OVERDUE: "受理后逾期未作出仲裁裁决",
    PROCEDURE_NON_FINAL_AWARD: "已收到非终局仲裁裁决书",
    PROCEDURE_FINAL_AWARD: "已收到终局仲裁裁决书",
    PROCEDURE_MEDIATION_EFFECTIVE: "仲裁调解书已生效",
    PROCEDURE_OTHER_OR_UNCERTAIN: "其他情况／无法确认",
}

#: One-line description shown under the procedure selector.
PROCEDURE_DESCRIPTIONS = {
    PROCEDURE_NOT_APPLIED: "仲裁前置程序尚未启动；本工具不能生成起诉状。",
    PROCEDURE_APPLICATION_PENDING: "仲裁机构已受理但尚未结案；一般应等待仲裁程序。",
    PROCEDURE_ACCEPTANCE_OVERDUE: "申请后超过法定期限仍未作出受理或不予受理决定。",
    PROCEDURE_NOT_ACCEPTED: "已收到书面不予受理决定；按载明的理由分流处理。",
    PROCEDURE_AWARD_OVERDUE: "受理后超过法定期限（含准许延长）仍未收到裁决。",
    PROCEDURE_NON_FINAL_AWARD: "劳动者或用人单位均可在法定期限内起诉。",
    PROCEDURE_FINAL_AWARD: "劳动者可起诉；用人单位只能申请撤销裁决。",
    PROCEDURE_MEDIATION_EFFECTIVE: "生效调解书不能就同一争议再行起诉。",
    PROCEDURE_OTHER_OR_UNCERTAIN: "情况不明确；生成前需人工法律审查。",
}

#: Grounds a written non-acceptance decision may state (解释一 第5/6/7条).
GROUND_NOT_LABOR_DISPUTE = "not_labor_dispute"
GROUND_NO_JURISDICTION = "no_jurisdiction"
GROUND_PARTY_UNQUALIFIED = "party_unqualified"
GROUND_OTHER_OR_UNSTATED = "other_or_unstated"

LABOR_REFUSAL_GROUNDS = (
    GROUND_NOT_LABOR_DISPUTE,
    GROUND_NO_JURISDICTION,
    GROUND_PARTY_UNQUALIFIED,
    GROUND_OTHER_OR_UNSTATED,
)

REFUSAL_GROUND_LABELS = {
    GROUND_NOT_LABOR_DISPUTE: "以事项不属于劳动争议为由",
    GROUND_NO_JURISDICTION: "以无管辖权为由",
    GROUND_PARTY_UNQUALIFIED: "以主体不适格为由",
    GROUND_OTHER_OR_UNSTATED: "其他理由／决定未载明理由",
}

#: Party role inside a final-award scenario (第48/49条 diverge by role).
ROLE_EMPLOYEE = "employee"
ROLE_EMPLOYER = "employer"

LABOR_ROLES = (ROLE_EMPLOYEE, ROLE_EMPLOYER)

ROLE_LABELS = {ROLE_EMPLOYEE: "劳动者（员工一方）", ROLE_EMPLOYER: "用人单位（雇主一方）"}

#: Last review time of the procedural wording against the cited provisions.
ARBITRATION_NOTICE_BASIS = (
    "依据：《劳动争议调解仲裁法》关于“先裁后审”的规定；"
    "整理时间：2026-11，请以最新法律及当地仲裁/法院实践为准。"
)

#: Statutory day thresholds, counted from user-supplied dates (calendar days).
#: 第29条: 仲裁委收到仲裁申请之日起五日内决定是否受理。
ACCEPTANCE_DECISION_DAYS = 5
#: 第43条: 受理之日起四十五日结案，经批准延长的不得超过十五日。
AWARD_DECISION_DAYS = 45 + 15
#: 第48/50条: 收到裁决书之日起十五日内起诉。
AWARD_FILING_WINDOW_DAYS = 15


class LaborProcedureGuard:
    """Static procedural notices shared by the wizard pages."""

    def get_warning_text(self):
        """Full procedural notice shown on the case-selection page."""
        return (
            "【法律程序风险提示】\n\n"
            "1. 先裁后审：劳动争议一般须先向劳动人事争议仲裁委员会申请仲裁，对仲裁裁决不服的，"
            "方可在收到裁决书之日起 15 日内向人民法院起诉；未经仲裁直接起诉的，法院通常不予受理。\n\n"
            "2. 例外情形：劳动者仅以用人单位出具的工资欠条为证据直接起诉，且诉讼请求不涉及劳动关系"
            "其他争议的，法院可按普通民事纠纷受理（参见最高人民法院劳动争议司法解释（一）第十五条）；"
            "本工具不为此情形生成劳动争议起诉状。\n\n"
            "3. 本工具按您如实选择的仲裁程序状态分流：仅对符合法定起诉条件的情形生成起诉状，"
            "对程序尚不具备或法律上不宜起诉的情形会明确说明原因。"
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


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date_text(text):
    """Parse a strict ``YYYY-MM-DD`` string into a :class:`datetime.date`.

    Returns ``None`` for blank, malformed or impossible dates; the caller
    decides whether that means "incomplete" or "invalid".
    """
    if text is None:
        return None
    stripped = text.strip()
    if not _DATE_PATTERN.match(stripped):
        return None
    try:
        return datetime.date.fromisoformat(stripped)
    except ValueError:
        return None


def _elapsed_days(text, today):
    """Return whole days between *text* (inclusive-until-today) and *today*."""
    parsed = parse_date_text(text)
    if parsed is None:
        return None
    return (today - parsed).days


# --------------------------------------------------------------------------- #
# Eligibility (single source of truth for page hint, export gate, document)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LaborEligibility:
    """Outcome of the procedural classification for complaint generation.

    ``eligible`` gates both wizard continuation and document export. ``reason``
    is the Chinese explanation shown when blocked (page hint and export gate).
    ``warning`` is the non-authoritative reminder shown when allowed.
    """

    eligible: bool
    reason: str = ""
    warning: str = ""

    def __bool__(self):
        return self.eligible


#: The 第12条 exception circumstances that justify arbitration delay; while any
#: applies, the direct-suit shortcut of 第29条/第43条第2款 is not reliable.
_DELAY_EXCEPTION_TEXT = (
    "移送管辖、送达延误、等待另案诉讼结果或评残结论、等待开庭、"
    "启动鉴定程序或委托其他部门调查取证"
)


def _delay_exception_reason():
    return (
        f"您确认案件的迟延与{_DELAY_EXCEPTION_TEXT}有关。在这些情形下，"
        "仲裁程序并未真正停滞，以逾期为由直接起诉可能不被法院受理"
        "（劳动争议司法解释（一）第12条）。建议等待相应程序结束，"
        "或咨询法律专业人士后再决定。本次不生成起诉状。"
    )


def evaluate_labor_eligibility(
    procedure,
    *,
    refusal_ground=None,
    role=None,
    delay_exception=None,
    plaintiff_is_company=False,
    commission="",
    application_date="",
    acceptance_date="",
    receipt_date="",
    today=None,
):
    """Classify *procedure* and return the fail-closed :class:`LaborEligibility`.

    Every required fact must come from user input; nothing is inferred. The
    evaluation is pure (``today`` injectable) so the wizard page, the export
    gate and tests share one implementation. ``plaintiff_is_company`` reports
    whether any plaintiff card is marked as a company, so the employee-only
    wage template cannot be produced for a company-form plaintiff.
    """
    if today is None:
        today = datetime.date.today()

    if procedure not in LABOR_PROCEDURES:
        return LaborEligibility(
            False,
            "请先选择当前的劳动仲裁程序状态，再继续填写。",
        )

    if procedure == PROCEDURE_NOT_APPLIED:
        return LaborEligibility(
            False,
            "您选择了“尚未申请劳动仲裁”。本工具当前只能生成仲裁之后向法院起诉所用的起诉状，"
            "不能为本阶段生成文书。请先向用人单位所在地或劳动合同履行地的劳动人事争议仲裁委员会"
            "申请仲裁；劳动仲裁申请书的生成将在后续版本提供。"
            "（如您仅持有用人单位出具的工资欠条且不涉及其他劳动关系争议，"
            "可依据劳动争议司法解释（一）第十五条按普通民事纠纷直接起诉，"
            "请咨询法律专业人士选择合适的途径。）",
        )

    if procedure == PROCEDURE_APPLICATION_PENDING:
        return LaborEligibility(
            False,
            "您选择了“已申请仲裁，程序进行中”。仲裁程序尚未结束前，一般不能就同一争议向法院起诉"
            "（《劳动争议调解仲裁法》第五条）。如仲裁机构已超过法定期限仍未作出是否受理的决定"
            "或仍未作出裁决，请改选对应的逾期状态。",
        )

    if procedure == PROCEDURE_MEDIATION_EFFECTIVE:
        return LaborEligibility(
            False,
            "已生效的仲裁调解书对双方具有约束力，不能再就同一争议向法院起诉"
            "（《劳动争议调解仲裁法》第四十二条）；一方不履行的，另一方可以依法向人民法院申请执行"
            "（第五十一条）。如对调解书确有异议，建议咨询法律专业人士。"
            "本工具不能为此情形生成起诉状。",
        )

    if procedure == PROCEDURE_OTHER_OR_UNCERTAIN:
        return LaborEligibility(
            False,
            "所选情形无法确认具体的仲裁程序结果，本工具不能据此生成起诉状。"
            "建议携带仲裁文书等材料咨询法律专业人士，或改选最符合实际情况的程序状态。",
        )

    # Employee-plaintiff contract: every state that can otherwise reach the
    # labour complaint must first establish who is suing. The current document
    # model is an employee wage-recovery template; a legal right to sue does
    # not imply this template fits the plaintiff's side.
    if procedure in _ROLE_REQUIRED_STATES:
        role_block = _require_employee_role(role, procedure)
        if role_block is not None:
            return role_block
        company_block = _require_employee_plaintiff_form(plaintiff_is_company)
        if company_block is not None:
            return company_block

    if procedure == PROCEDURE_NOT_ACCEPTED:
        return _evaluate_not_accepted(
            refusal_ground, commission, receipt_date, today
        )

    if procedure == PROCEDURE_ACCEPTANCE_OVERDUE:
        return _evaluate_acceptance_overdue(
            delay_exception, commission, application_date, today
        )

    if procedure == PROCEDURE_AWARD_OVERDUE:
        return _evaluate_award_overdue(
            delay_exception, commission, acceptance_date, today
        )

    if procedure == PROCEDURE_NON_FINAL_AWARD:
        return _evaluate_award_received(commission, receipt_date, today)

    if procedure == PROCEDURE_FINAL_AWARD:
        return _evaluate_final_award(commission, receipt_date, today)

    # Unreachable while LABOR_PROCEDURES is exhaustive; kept fail-closed.
    return LaborEligibility(False, "程序状态无法识别，请重新选择。")


#: States that can otherwise reach the employee wage-recovery complaint and
#: therefore require the plaintiff role (and the plaintiff's natural-person
#: form) to be confirmed before anything else is evaluated.
_ROLE_REQUIRED_STATES = frozenset({
    PROCEDURE_ACCEPTANCE_OVERDUE,
    PROCEDURE_NOT_ACCEPTED,
    PROCEDURE_AWARD_OVERDUE,
    PROCEDURE_NON_FINAL_AWARD,
    PROCEDURE_FINAL_AWARD,
})


def _require_employee_role(role, procedure):
    """Gate the employee-only wage template on the confirmed plaintiff role.

    ``None`` blocks (never defaults to employee). An employer plaintiff is
    blocked as unsupported by the current template — phrased as a product
    boundary, not as a legal prohibition, except for final awards where
    Article 49 makes the cancellation application the employer's actual route.
    """
    if role not in LABOR_ROLES:
        return LaborEligibility(
            False,
            "请先确认您在本案中的身份（劳动者／员工一方，或用人单位／雇主一方）："
            "两者的程序后果不同，且本工具的劳动争议起诉状模板面向劳动者编写。",
        )
    if role == ROLE_EMPLOYER:
        if procedure == PROCEDURE_FINAL_AWARD:
            return LaborEligibility(
                False,
                "终局裁决对用人单位实行一裁终局：用人单位不得就同一争议向人民法院起诉，"
                "只能自收到裁决书之日起三十日内向劳动争议仲裁委员会所在地的中级人民法院"
                "申请撤销裁决（《劳动争议调解仲裁法》第四十七条、第四十九条）。"
                "本工具不生成撤销裁决申请书，建议咨询法律专业人士。本次不生成起诉状。",
            )
        return LaborEligibility(
            False,
            "您确认原告一方为用人单位（雇主）。本工具当前的劳动争议起诉状模板面向劳动者"
            "（员工一方）追索工资等请求编写；用人单位作为原告的情形，当前版本不支持生成起诉状。"
            "这并不否定用人单位依法可享有的起诉权利（例如对非终局裁决不服，用人单位同样可以"
            "自收到裁决书之日起十五日内向人民法院提起诉讼，《劳动争议调解仲裁法》第五十条）；"
            "建议另行准备相应法律文书或咨询法律专业人士。本次不生成起诉状。",
        )
    return None


def _require_employee_plaintiff_form(plaintiff_is_company):
    """Block the contradiction of a company-form plaintiff in the wage template."""
    if plaintiff_is_company:
        return LaborEligibility(
            False,
            "原告一方被标记为单位／公司，而当前劳动争议起诉状模板面向劳动者（员工一方）"
            "追索工资等请求，两者不一致。请核对原告身份后修改，或就单位一方的主张"
            "咨询法律专业人士并另行准备相应文书。本次不生成起诉状。",
        )
    return None


def _require_commission(commission):
    if not (commission or "").strip():
        return LaborEligibility(False, "请填写仲裁机构名称（见仲裁文书或受理通知）。")
    return None


def _require_date(value, label):
    parsed = parse_date_text(value)
    if parsed is None:
        return LaborEligibility(False, f"请填写有效的{label}（格式 YYYY-MM-DD）。")
    return None


def _require_past_date(value, label, today):
    """Validate a *received*-document date: well-formed and not in the future.

    A future date contradicts the selected state itself (the document cannot
    already have been received), so it must never become an asserted fact in a
    generated document. ``value == today`` is accepted; strictly-later dates
    are blocked.
    """
    blocker = _require_date(value, label)
    if blocker is not None:
        return blocker
    parsed = parse_date_text(value)
    if parsed > today:
        return LaborEligibility(
            False,
            f"{label}（{value.strip()}）晚于今天：尚未收到的文书不能作为已收到的"
            "既成事实填写，请核对日期，或改选正确的程序状态。",
        )
    return None


def _non_final_award_warning(receipt_date, today):
    """Non-authoritative reminder for the Article 50 non-final filing window."""
    elapsed = _elapsed_days(receipt_date, today)
    if elapsed is not None and elapsed > AWARD_FILING_WINDOW_DAYS:
        return (
            "提醒：按您填写的日期计算，距收到裁决书已超过十五日（节假日可能依法顺延）。"
            "期满不起诉的，裁决书发生法律效力（《劳动争议调解仲裁法》第五十条）；"
            "是否仍在期限内以法院认定为准，建议先向法院或法律专业人士确认后尽快办理。"
        )
    return (
        "提醒：对裁决不服的，可自收到裁决书之日起十五日内向人民法院提起诉讼；"
        "期满不起诉的，裁决书发生法律效力（《劳动争议调解仲裁法》第五十条）。"
        "期限计算以法院认定为准，建议尽快办理。"
    )


def _final_award_employee_warning(receipt_date, today):
    """Non-authoritative reminder for the Article 47/48 final-award window.

    Deliberately separate from the non-final warning: a final award becomes
    effective under its own statutory rule (Article 47: 裁决书自作出之日起发生
    法律效力), not upon expiry of the filing period, so Article 50 language
    must never appear here.
    """
    elapsed = _elapsed_days(receipt_date, today)
    if elapsed is not None and elapsed > AWARD_FILING_WINDOW_DAYS:
        return (
            "提醒：按您填写的日期计算，距收到裁决书已超过十五日（节假日可能依法顺延）。"
            "终局裁决自作出之日起发生法律效力（《劳动争议调解仲裁法》第四十七条）；"
            "劳动者不服的，可以自收到裁决书之日起十五日内向人民法院提起诉讼（第四十八条）。"
            "是否仍在期限内以法院认定为准，建议先向法院或法律专业人士确认后尽快办理。"
        )
    return (
        "提醒：该裁决为终局裁决，自作出之日起发生法律效力（《劳动争议调解仲裁法》第四十七条）；"
        "劳动者不服的，可以自收到裁决书之日起十五日内向人民法院提起诉讼（第四十八条）。"
        "期限计算以法院认定为准，建议尽快办理。"
    )


def _evaluate_not_accepted(refusal_ground, commission, receipt_date, today):
    if refusal_ground not in LABOR_REFUSAL_GROUNDS:
        return LaborEligibility(
            False,
            "请选择不予受理决定载明的理由；不同理由对应的法院处理方式不同。"
            "如决定未载明理由，请选择“其他理由／决定未载明理由”。",
        )
    if refusal_ground == GROUND_NO_JURISDICTION:
        return LaborEligibility(
            False,
            "仲裁机构以无管辖权为由不予受理的，人民法院一般会告知您向有管辖权的劳动争议仲裁机构"
            "申请仲裁；经审查该机构确有管辖权而其仍不受理的，才可就该事项起诉"
            "（劳动争议司法解释（一）第5条）。请先向有管辖权的仲裁机构重新申请仲裁；"
            "如该机构仍出具不予受理决定，再改选本状态并填写其理由。本次不生成起诉状。",
        )
    blocker = _require_commission(commission)
    if blocker is not None:
        return blocker
    blocker = _require_past_date(receipt_date, "收到不予受理通知书的日期", today)
    if blocker is not None:
        return blocker

    if refusal_ground == GROUND_NOT_LABOR_DISPUTE:
        warning = (
            "提醒：以事项不属于劳动争议为由不予受理的，法院认为属于劳动争议案件的应予受理；"
            "认为不属于劳动争议但属于人民法院主管的其他案件的，亦应依法受理"
            "（劳动争议司法解释（一）第6条）。是否受理由法院审查决定。"
        )
    elif refusal_ground == GROUND_PARTY_UNQUALIFIED:
        warning = (
            "提醒：法院将审查是否确属主体不适格；如确属，起诉可能不予受理或被驳回起诉"
            "（劳动争议司法解释（一）第7条），建议先咨询法律专业人士。"
        )
    else:
        warning = (
            "提醒：不予受理理由未载明或属于其他情形的，就该事项向法院起诉的权利来自"
            "《劳动争议调解仲裁法》第二十九条；是否受理由法院审查决定。"
        )
    return LaborEligibility(True, warning=warning)


def _evaluate_acceptance_overdue(delay_exception, commission, application_date, today):
    if delay_exception is None:
        return LaborEligibility(
            False,
            "请确认仲裁机构的迟延是否因"
            f"{_DELAY_EXCEPTION_TEXT}等情形造成（《劳动争议调解仲裁法》第二十九条、"
            "劳动争议司法解释（一）第12条）。",
        )
    if delay_exception is True:
        return LaborEligibility(False, _delay_exception_reason())
    blocker = _require_commission(commission)
    if blocker is not None:
        return blocker
    blocker = _require_date(application_date, "申请仲裁的日期")
    if blocker is not None:
        return blocker
    elapsed = _elapsed_days(application_date, today)
    if elapsed is not None and elapsed < 0:
        return LaborEligibility(
            False, "申请仲裁的日期晚于今天，请核对后重新填写。"
        )
    if elapsed is not None and elapsed <= ACCEPTANCE_DECISION_DAYS:
        return LaborEligibility(
            False,
            f"按您填写的申请日期（{application_date.strip()}）计算，仲裁机构作出是否受理决定的"
            "五日法定期限（《劳动争议调解仲裁法》第二十九条）尚未届满，一般应继续等待仲裁机构的通知。",
        )
    return LaborEligibility(
        True,
        warning=(
            "提醒：起诉时建议向法院提交仲裁申请回执或其他已提交申请的凭证；"
            "是否受理由法院审查决定（劳动争议司法解释（一）第12条）。"
        ),
    )


def _evaluate_award_overdue(delay_exception, commission, acceptance_date, today):
    if delay_exception is None:
        return LaborEligibility(
            False,
            "请确认仲裁机构的迟延是否因"
            f"{_DELAY_EXCEPTION_TEXT}等情形造成（《劳动争议调解仲裁法》第四十三条、"
            "劳动争议司法解释（一）第12条）。",
        )
    if delay_exception is True:
        return LaborEligibility(False, _delay_exception_reason())
    blocker = _require_commission(commission)
    if blocker is not None:
        return blocker
    blocker = _require_date(acceptance_date, "仲裁受理日期（见受理通知书）")
    if blocker is not None:
        return blocker
    elapsed = _elapsed_days(acceptance_date, today)
    if elapsed is not None and elapsed < 0:
        return LaborEligibility(
            False, "仲裁受理日期晚于今天，请核对后重新填写。"
        )
    if elapsed is not None and elapsed <= AWARD_DECISION_DAYS:
        return LaborEligibility(
            False,
            f"按您填写的受理日期（{acceptance_date.strip()}）计算，法定裁决期限"
            "（受理之日起四十五日，案情复杂经批准可延长十五日，"
            "《劳动争议调解仲裁法》第四十三条）尚未届满，一般应继续等待仲裁裁决。",
        )
    return LaborEligibility(
        True,
        warning=(
            "提醒：以逾期未作出仲裁裁决为由起诉的，应当向法院提交受理通知书或其他"
            "已接受仲裁申请的凭证（劳动争议司法解释（一）第12条）。"
        ),
    )


def _evaluate_award_received(commission, receipt_date, today):
    blocker = _require_commission(commission)
    if blocker is not None:
        return blocker
    blocker = _require_past_date(receipt_date, "收到裁决书的日期", today)
    if blocker is not None:
        return blocker
    return LaborEligibility(True, warning=_non_final_award_warning(receipt_date, today))


def _evaluate_final_award(commission, receipt_date, today):
    blocker = _require_commission(commission)
    if blocker is not None:
        return blocker
    blocker = _require_past_date(receipt_date, "收到裁决书的日期", today)
    if blocker is not None:
        return blocker
    return LaborEligibility(True, warning=_final_award_employee_warning(receipt_date, today))
