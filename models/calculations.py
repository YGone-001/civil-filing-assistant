# File: models/calculations.py
# Purpose: Pure domain calculation foundation — finite Decimal parsing,
#          deterministic money formatting, the contract-penalty calculators,
#          the property-fee estimate and labor month ranges. No Qt imports.
# Encoding: UTF-8
"""One authoritative, deterministic calculation contract.

All monetary arithmetic uses :class:`decimal.Decimal` with ``ROUND_HALF_UP``
and the application's two-decimal money presentation; binary floats are never
the source of a financial calculation. Malformed, nonfinite or insufficient
inputs never silently become zero: raising APIs raise
:class:`CalculationError`, reporting APIs return result objects whose invalid
state is explicit.

Compatibility: ``models.case_model`` re-exports ``CalculationError``,
``parse_decimal`` (as ``_to_decimal``), ``format_money`` (as ``_format_money``)
and ``parse_month_range`` so existing callers keep working unchanged.
"""

import datetime
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

from models.validation import DateStatus, ValidationStatus, ValidationResult, parse_full_date

# Two-decimal money presentation (existing application convention).
MONEY_QUANTUM = Decimal("0.01")
DAYS_PER_YEAR = Decimal("365")

# The daily 万五 convention of the auxiliary penalty calculator: 0.0005 per
# overdue day. This describes the software calculation, not a legal rate.
DAILY_RATE_5_PER_10K = Decimal("0.0005")

# Supported magnitude of one monetary operand: at most 12 integral digits and
# 2 fraction digits — exactly what the UI input validators admit. This is a
# computational limit of the calculation contract (it keeps every intermediate
# product exactly quantizable), not a legal cap on any claim.
MAX_MONETARY_OPERAND = Decimal("999999999999.99")


class CalculationError(ValueError):
    """Raised when an input cannot be parsed or a calculation is not applicable.

    Callers must treat this as "the value shown to the user is not authoritative"
    and fall back to an explicit, editable placeholder rather than inventing a
    number or silently returning zero.
    """


# --- Finite Decimal parsing and money formatting ---------------------------


def parse_decimal(value, field_name="数值"):
    """Parse *value* into a finite :class:`~decimal.Decimal` or return ``None``.

    Empty input yields ``None``. Invalid or nonfinite input (``NaN``,
    ``Infinity``) raises :class:`CalculationError`. Negative values are parsed
    as-is; rejecting them is the caller's scenario-specific decision.
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


def format_money(value):
    """Quantize to two decimals (ROUND_HALF_UP) and render deterministically."""
    return f"{quantize_money(value)}"


def quantize_money(value):
    """Quantize to the money quantum (ROUND_HALF_UP); returns a Decimal.

    A local high-precision context makes quantization exact and deterministic
    for every product the supported operand bound can produce (near 30
    significant digits); the default 28-digit context would raise
    ``InvalidOperation`` there. No truncation, clamping or float conversion.
    """
    with localcontext() as ctx:
        ctx.prec = 64
        return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _parse_bounded_decimal(text, field_name):
    """Parse a monetary operand and enforce the supported input magnitude.

    Beyond :data:`MAX_MONETARY_OPERAND` the calculators fail with an explicit
    :class:`CalculationError` instead of truncating, clamping, converting to
    float, or overflowing quantization.
    """
    value = parse_decimal(text, field_name)
    if value is not None and abs(value) > MAX_MONETARY_OPERAND:
        raise CalculationError(f"{field_name}超出可支持的数值范围（最多12位整数）")
    return value


def validate_rate_text(text, field="rate"):
    """Validate an annual-rate percentage input as a structured result.

    Empty input is allowed (no interest agreement); non-numeric and negative
    values carry the historical user-facing messages.
    """
    stripped = "" if text is None else str(text).strip()
    if not stripped:
        return ValidationResult(field, ValidationStatus.EMPTY_ALLOWED, "RATE_EMPTY")
    try:
        value = parse_decimal(stripped, "年利率")
    except CalculationError:
        return ValidationResult(
            field, ValidationStatus.INVALID_FORMAT, "RATE_NOT_NUMERIC", "请输入有效的数字"
        )
    if value is None:
        return ValidationResult(field, ValidationStatus.EMPTY_ALLOWED, "RATE_EMPTY")
    if value < 0:
        return ValidationResult(
            field, ValidationStatus.INVALID_RANGE, "RATE_NEGATIVE", "年利率不应为负数，请核对。"
        )
    return ValidationResult(field, ValidationStatus.VALID, "RATE_OK")


# --- Labor month ranges (distinct from full-date parsing) -------------------

_MONTH_TOKEN = re.compile(r"(\d{4})?\s*[年/\-.]?\s*(\d{1,2})")
_RANGE_SEPARATOR = re.compile(r"[至到~—–～]|\s-\s")


def parse_month_range(text):
    """Parse a labor unpaid-month range into an inclusive month count.

    Returns a ``(months, is_partial)`` tuple. Supported inputs include::

        2023年12月至2024年2月   -> (3, False)
        2023-12 至 2024-02      -> (3, False)
        2023年12月              -> (1, False)
        2023年12月至2月         -> (3, True)   # end year inferred

    ``is_partial`` is ``True`` when the range depends on an inferred year or
    contains explicit day components, i.e. it may not be a whole number of
    fully specified monthly periods. Invalid or reversed ranges raise
    :class:`CalculationError`; empty input also raises so that callers never
    treat "unknown" as zero. These labor-specific semantics are intentionally
    separate from :func:`models.validation.parse_full_date`.
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


def validate_month_range_text(text, field="l_unpaid_months"):
    """Report a labor unpaid-month range as a structured validation result.

    Consumed by ``LaborCaseModel`` to select the computed claim or the neutral
    editable placeholder; never raises.
    """
    try:
        months, is_partial = parse_month_range(text)
    except CalculationError as exc:
        return ValidationResult(
            field, ValidationStatus.INVALID_FORMAT, "MONTH_RANGE_UNPARSEABLE", str(exc)
        )
    if is_partial:
        return ValidationResult(
            field, ValidationStatus.VALID, "MONTH_RANGE_PARTIAL",
            "该区间含不完整或推断月份，具体金额请人工核对",
        )
    return ValidationResult(
        field, ValidationStatus.VALID, "MONTH_RANGE_WHOLE", f"共{months}个月"
    )


# --- Contract penalty calculators (pure) ------------------------------------


@dataclass(frozen=True)
class PenaltyCalculation:
    """One successful auxiliary penalty calculation and its full provenance."""

    method: str            # "daily_5_per_10k" | "lpr_multiple"
    principal: Decimal
    start: datetime.date
    cutoff: datetime.date
    days: int
    amount: Decimal        # quantized to MONEY_QUANTUM


def _parse_penalty_principal(principal_text):
    principal = _parse_bounded_decimal(principal_text, "尚欠货款本金")
    if principal is None:
        raise CalculationError("未填写尚欠货款本金")
    if principal < 0:
        raise CalculationError("尚欠货款本金为负数")
    return principal


def _penalty_days(start, cutoff):
    if cutoff < start:
        raise CalculationError("违约金计算截止日早于起算日")
    days = (cutoff - start).days
    if days <= 0:
        raise CalculationError("起算日与截止日为同日，无法按日折算违约金")
    return days


def calculate_daily_penalty(principal_text, start, cutoff):
    """Daily 万五 convention: ``principal × 0.0005 × days`` (Decimal)."""
    principal = _parse_penalty_principal(principal_text)
    days = _penalty_days(start, cutoff)
    amount = quantize_money(principal * DAILY_RATE_5_PER_10K * days)
    return PenaltyCalculation("daily_5_per_10k", principal, start, cutoff, days, amount)


def calculate_lpr_penalty(principal_text, lpr_text, multiple_text, start, cutoff):
    """LPR-multiple convention: ``principal × (LPR × multiple / 100) × days / 365``."""
    principal = _parse_penalty_principal(principal_text)
    lpr = _parse_bounded_decimal(lpr_text, "LPR")
    if lpr is None:
        raise CalculationError("未填写LPR")
    if lpr < 0:
        raise CalculationError("LPR不应为负数")
    multiple = _parse_bounded_decimal(multiple_text, "LPR倍数")
    if multiple is None:
        raise CalculationError("未填写LPR倍数")
    if multiple < 0:
        raise CalculationError("LPR倍数不应为负数")
    days = _penalty_days(start, cutoff)
    annual_rate = (lpr * multiple) / Decimal("100")
    amount = quantize_money(principal * annual_rate * days / DAYS_PER_YEAR)
    return PenaltyCalculation("lpr_multiple", principal, start, cutoff, days, amount)


# --- Property-fee estimate (pure, single authoritative implementation) ------


@dataclass(frozen=True)
class PropertyFeeEstimate:
    """One property-fee estimate with an explicit validity state.

    ``total is None`` means the inputs are insufficient or invalid; the UI
    must present a neutral "cannot calculate" message instead of a fabricated
    valid-looking zero. ``months``/``is_partial`` stay meaningful whenever the
    billing period itself parses, mirroring the historical model behaviour.
    """

    months: int
    is_partial: bool
    total: Decimal | None
    reason: str = ""       # "" when valid; a machine-readable status otherwise


def inclusive_month_count(start, end):
    """Inclusive touched-month count; ``0`` for a reversed interval."""
    if start is None or end is None or end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def is_whole_month_span(start, end):
    """True when the period starts on day 1 and ends on a month's last day."""
    if start is None or end is None:
        return False
    if end.month == 12:
        nxt = datetime.date(end.year + 1, 1, 1)
    else:
        nxt = datetime.date(end.year, end.month + 1, 1)
    return start.day == 1 and end.day == (nxt - datetime.timedelta(days=1)).day


def calculate_property_fee(area_text, rate_text, start_text, end_text):
    """Estimate ``area × monthly rate × inclusive touched months``.

    The single authoritative property-fee implementation, consumed by both
    ``PropertyCaseModel`` and ``PropertyClaimPage`` so the on-screen estimate
    and the exported document can never disagree.
    """
    start_result = parse_full_date(start_text)
    end_result = parse_full_date(end_text)
    if start_result.status == DateStatus.EMPTY or end_result.status == DateStatus.EMPTY:
        return PropertyFeeEstimate(0, False, None, "PERIOD_MISSING")
    if start_result.status != DateStatus.VALID:
        return PropertyFeeEstimate(0, False, None, "PERIOD_START_INVALID")
    if end_result.status != DateStatus.VALID:
        return PropertyFeeEstimate(0, False, None, "PERIOD_END_INVALID")

    start, end = start_result.value, end_result.value
    months = inclusive_month_count(start, end)
    if end < start:
        return PropertyFeeEstimate(0, False, None, "PERIOD_REVERSED")
    partial = not is_whole_month_span(start, end)

    try:
        area = parse_decimal(area_text, "房屋面积")
        rate = parse_decimal(rate_text, "计费标准")
    except CalculationError:
        return PropertyFeeEstimate(months, partial, None, "AREA_OR_RATE_INVALID")
    if area is None or rate is None:
        return PropertyFeeEstimate(months, partial, None, "AREA_OR_RATE_MISSING")
    if area < 0 or rate < 0:
        return PropertyFeeEstimate(months, partial, None, "AREA_OR_RATE_NEGATIVE")
    if abs(area) > MAX_MONETARY_OPERAND or abs(rate) > MAX_MONETARY_OPERAND:
        return PropertyFeeEstimate(months, partial, None, "OPERAND_OUT_OF_RANGE")

    total = quantize_money(area * rate * months)
    return PropertyFeeEstimate(months, partial, total)
