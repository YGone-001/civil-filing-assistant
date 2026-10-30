# File: tests/test_domain_calculations.py
# Purpose: Unit tests for the pure calculation foundation (P2-02 / P2-04 / P2-05).
# Encoding: UTF-8
"""Direct tests for models/calculations.py — the single authoritative contract.

All monetary arithmetic is Decimal with ROUND_HALF_UP and two-decimal money
presentation; the legacy float-based calculators are compared against it to
document calculation equivalence (P2-04 §6.6). No Qt is involved here.
"""

import datetime
from decimal import Decimal

import pytest

from models.calculations import (
    CalculationError,
    calculate_daily_penalty,
    calculate_lpr_penalty,
    calculate_property_fee,
    format_money,
    inclusive_month_count,
    is_whole_month_span,
    parse_decimal,
    quantize_money,
    validate_month_range_text,
    validate_rate_text,
)
from models.validation import ValidationStatus

D1 = datetime.date(2023, 3, 1)
D2 = datetime.date(2023, 3, 8)
D3 = datetime.date(2023, 6, 30)


# --- parse_decimal ----------------------------------------------------------


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_decimal_parse_empty_returns_none(raw):
    assert parse_decimal(raw, "测试") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0", Decimal("0")),
        (" 50000 ", Decimal("50000")),
        ("115.5", Decimal("115.5")),
        ("0.01", Decimal("0.01")),
        ("1000000000000", Decimal("1000000000000")),
        ("0.000001", Decimal("0.000001")),
    ],
)
def test_decimal_parse_valid_values(raw, expected):
    assert parse_decimal(raw, "测试") == expected


def test_decimal_parse_negative_is_parsed_not_rejected():
    """Negative rejection is the caller's scenario-specific decision."""
    assert parse_decimal("-100", "测试") == Decimal("-100")


@pytest.mark.parametrize("raw", ["abc", "12x3", "1.2.3", "NaN", "Infinity", "-Infinity", "nan"])
def test_decimal_parse_invalid_and_nonfinite_raise(raw):
    with pytest.raises(CalculationError):
        parse_decimal(raw, "测试")


def test_decimal_parse_deterministic():
    results = {parse_decimal("7761.605", "测试") for _ in range(50)}
    assert len(results) == 1


# --- format_money -----------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        (Decimal("2.005"), "2.01"),        # exact half rounds up (HALF_UP)
        (Decimal("2.004"), "2.00"),
        (Decimal("2.00500001"), "2.01"),
        (Decimal("0"), "0.00"),
        (Decimal("40"), "40.00"),          # trailing zeros preserved
        (Decimal("-1.005"), "-1.01"),      # away from zero on exact halves
        (Decimal("1372.438356164383"), "1372.44"),
        (Decimal("99999999999.995"), "100000000000.00"),
    ],
)
def test_money_formatting_rounding_boundaries(raw, expected):
    assert format_money(raw) == expected


def test_money_formatting_deterministic():
    assert len({format_money(Decimal("1.005")) for _ in range(50)}) == 1


# --- Contract penalty calculators -------------------------------------------


def test_daily_penalty_valid_inputs():
    result = calculate_daily_penalty("30000", D1, D2)
    assert result.method == "daily_5_per_10k"
    assert result.days == 7
    assert result.amount == Decimal("105.00")
    assert result.principal == Decimal("30000")
    assert result.cutoff == D2


def test_lpr_penalty_valid_inputs():
    result = calculate_lpr_penalty("30000", "3.45", "4", D1, D3)
    # 30000 × (3.45 × 4 / 100) × 121 / 365 = 1372.438356... -> 1372.44
    assert result.method == "lpr_multiple"
    assert result.days == 121
    assert result.amount == Decimal("1372.44")


def test_daily_penalty_zero_principal_is_allowed():
    """The UI validator admits zero; the historical behaviour produced 0.00."""
    result = calculate_daily_penalty("0", D1, D2)
    assert result.amount == Decimal("0.00")


def test_daily_penalty_negative_principal_raises():
    with pytest.raises(CalculationError):
        calculate_daily_penalty("-100", D1, D2)


@pytest.mark.parametrize("principal", ["", "   ", "abc", "NaN"])
def test_penalty_invalid_principal_raises(principal):
    with pytest.raises(CalculationError):
        calculate_daily_penalty(principal, D1, D2)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty(principal, "3.45", "4", D1, D2)


@pytest.mark.parametrize("lpr,multiple", [("", "4"), ("3.45", ""), ("abc", "4"), ("3.45", "x"), ("NaN", "4")])
def test_lpr_penalty_invalid_rate_inputs_raise(lpr, multiple):
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", lpr, multiple, D1, D2)


def test_penalty_reversed_interval_raises():
    with pytest.raises(CalculationError):
        calculate_daily_penalty("30000", D2, D1)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "3.45", "4", D2, D1)


def test_penalty_same_day_interval_raises():
    with pytest.raises(CalculationError):
        calculate_daily_penalty("30000", D1, D1)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "3.45", "4", D1, D1)


def test_penalty_decimal_precision_boundaries():
    """One-cent boundary: float noise must not shift the quantized result."""
    result = calculate_lpr_penalty("10000", "3.65", "4", datetime.date(2023, 1, 1),
                                   datetime.date(2023, 1, 11))
    assert result.amount == Decimal("40.00")


def test_penalty_legacy_float_equivalence_on_documented_inputs():
    """P2-04 §6.6: the Decimal results match the legacy float presentation for
    the documented example inputs (no formula change, no cent differences)."""
    legacy_floats = [
        ("30000", D1, D2, None, None),                       # daily, 7 days
        ("30000", D1, D3, "3.45", "4"),                      # lpr, 121 days
        ("10000", datetime.date(2023, 1, 1), datetime.date(2023, 1, 11), "3.65", "4"),
    ]
    for principal, start, cutoff, lpr, multiple in legacy_floats:
        if lpr is None:
            old = float(principal) * 0.0005 * (cutoff - start).days
            new = calculate_daily_penalty(principal, start, cutoff).amount
        else:
            old = float(principal) * ((float(lpr) * float(multiple)) / 100.0) * ((cutoff - start).days / 365.0)
            new = calculate_lpr_penalty(principal, lpr, multiple, start, cutoff).amount
        assert f"{old:.2f}" == format_money(new), (principal, start, cutoff, lpr)


def test_penalty_calculation_repeats_deterministically():
    amounts = {
        calculate_lpr_penalty("30000", "3.45", "4", D1, D3).amount for _ in range(50)
    }
    assert len(amounts) == 1


# --- validate_rate_text ------------------------------------------------------


def test_rate_validation_accepts_valid_values():
    assert validate_rate_text("14.6").status == ValidationStatus.VALID
    assert validate_rate_text("0").status == ValidationStatus.VALID


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_rate_validation_empty_is_allowed(raw):
    result = validate_rate_text(raw)
    assert result.status == ValidationStatus.EMPTY_ALLOWED
    assert result.is_valid


def test_rate_validation_invalid_and_negative():
    invalid = validate_rate_text("abc")
    assert invalid.status == ValidationStatus.INVALID_FORMAT
    assert invalid.message == "请输入有效的数字"

    negative = validate_rate_text("-1")
    assert negative.status == ValidationStatus.INVALID_RANGE
    assert negative.message == "年利率不应为负数，请核对。"


# --- Property-fee estimate ---------------------------------------------------


def test_property_fee_full_calendar_months():
    estimate = calculate_property_fee("115.5", "2.8", "2024-01-01", "2025-12-31")
    assert estimate.months == 24
    assert estimate.is_partial is False
    assert estimate.total == Decimal("7761.60")
    assert estimate.reason == ""


def test_property_fee_cross_year_period():
    estimate = calculate_property_fee("100", "2", "2024-11-01", "2025-02-28")
    assert estimate.months == 4
    assert estimate.total == Decimal("800.00")


def test_property_fee_partial_first_and_last_month():
    estimate = calculate_property_fee("100", "2", "2024-01-15", "2024-03-20")
    assert estimate.months == 3
    assert estimate.is_partial is True
    assert estimate.total == Decimal("600.00")


def test_property_fee_single_day_period_is_partial():
    estimate = calculate_property_fee("100", "2", "2024-05-05", "2024-05-05")
    assert estimate.months == 1
    assert estimate.is_partial is True
    assert estimate.total == Decimal("200.00")


@pytest.mark.parametrize(
    "area,rate,start,end,reason",
    [
        ("", "2.8", "2024-01-01", "2024-12-31", "AREA_OR_RATE_MISSING"),
        ("115.5", "", "2024-01-01", "2024-12-31", "AREA_OR_RATE_MISSING"),
        ("115.5", "2.8", "", "2024-12-31", "PERIOD_MISSING"),
        ("115.5", "2.8", "2024-01-01", "", "PERIOD_MISSING"),
        ("115.5", "2.8", "垃圾", "2024-12-31", "PERIOD_START_INVALID"),
        ("115.5", "2.8", "2024-01-01", "2024-13-40", "PERIOD_END_INVALID"),
        ("115.5", "2.8", "2024-12-31", "2024-01-01", "PERIOD_REVERSED"),
        ("-100", "2.8", "2024-01-01", "2024-12-31", "AREA_OR_RATE_NEGATIVE"),
        ("115.5", "-2.8", "2024-01-01", "2024-12-31", "AREA_OR_RATE_NEGATIVE"),
    ],
)
def test_property_fee_invalid_inputs_never_fake_a_total(area, rate, start, end, reason):
    estimate = calculate_property_fee(area, rate, start, end)
    assert estimate.total is None
    assert estimate.reason == reason


def test_property_fee_zero_area_is_a_true_zero():
    """Zero inputs multiply to a true zero; negatives are rejected instead."""
    estimate = calculate_property_fee("0", "2.8", "2024-01-01", "2024-12-31")
    assert estimate.total == Decimal("0.00")
    assert estimate.reason == ""


def test_property_fee_month_helpers():
    assert inclusive_month_count(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)) == 12
    assert inclusive_month_count(datetime.date(2024, 12, 31), datetime.date(2024, 1, 1)) == 0
    assert is_whole_month_span(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)) is True
    assert is_whole_month_span(datetime.date(2024, 1, 15), datetime.date(2024, 12, 31)) is False


def test_property_fee_model_and_estimate_agree(qapp):
    """The model delegates to the same function the UI uses."""
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    model = build_property_model(wizard)
    model._resolved_principal()  # the model's own resolution path

    estimate = calculate_property_fee(
        model.house_area, model.fee_rate, model.period_start, model.period_end
    )
    assert f"{estimate.total}" == model.total_principal == "7761.60"


def build_property_model(wizard):
    from presenters.model_builder import build_case_model

    return build_case_model(wizard)


# --- C-05: extreme operands and quantization precision -----------------------


def test_property_fee_extreme_ui_sized_operands_are_deterministic():
    """12-integral-digit operands (the UI input contract) over the longest
    supported period quantize exactly instead of raising InvalidOperation."""
    estimate = calculate_property_fee("999999999999", "999999999999", "1900-01-01", "2100-12-31")
    expected = quantize_money(Decimal("999999999999") * Decimal("999999999999") * 2412)
    assert estimate.total == expected
    assert estimate.reason == ""
    repeat = calculate_property_fee("999999999999", "999999999999", "1900-01-01", "2100-12-31")
    assert repeat.total == estimate.total  # deterministic under repetition


def test_property_fee_beyond_ui_magnitude_fails_controlled():
    """Operands beyond the documented 12-integral-digit contract fail with an
    explicit reason — no clamping, no float conversion, no fabricated zero."""
    estimate = calculate_property_fee("9999999999999", "2.8", "2024-01-01", "2024-12-31")
    assert estimate.total is None
    assert estimate.reason == "OPERAND_OUT_OF_RANGE"
    estimate = calculate_property_fee("115.5", "9999999999999", "2024-01-01", "2024-12-31")
    assert estimate.total is None
    assert estimate.reason == "OPERAND_OUT_OF_RANGE"


def test_penalty_extreme_inputs_fail_controlled():
    with pytest.raises(CalculationError):
        calculate_daily_penalty("9999999999999", D1, D3)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "9999999999999", "4", D1, D3)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "3.45", "9999999999999", D1, D3)


def test_penalty_at_operand_bound_quantizes_exactly():
    """At (not beyond) the documented bound both calculators stay exact."""
    start = datetime.date(1900, 1, 1)
    end = datetime.date(2100, 12, 31)
    days = (end - start).days  # 73413
    daily = calculate_daily_penalty("999999999999", start, end)
    assert daily.days == days
    assert daily.amount == quantize_money(Decimal("999999999999") * Decimal("0.0005") * days)
    lpr = calculate_lpr_penalty("999999999999", "3.45", "4", start, end)
    assert lpr.amount == quantize_money(
        Decimal("999999999999") * (Decimal("3.45") * 4 / Decimal("100")) * days / Decimal("365")
    )


# --- C-06: contract numeric validation consistency ---------------------------


def test_lpr_penalty_rejects_negative_rate_inputs():
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "-3.45", "4", D1, D3)
    with pytest.raises(CalculationError):
        calculate_lpr_penalty("30000", "3.45", "-4", D1, D3)


def test_lpr_penalty_zero_inputs_explicitly_compute_zero():
    """Zero LPR or multiplier is accepted and computes a true 0.00 (no legal
    special-casing); the daily method stays independent of LPR inputs."""
    assert calculate_lpr_penalty("30000", "0", "4", D1, D3).amount == Decimal("0.00")
    assert calculate_lpr_penalty("30000", "3.45", "0", D1, D3).amount == Decimal("0.00")
    daily = calculate_daily_penalty("30000", D1, D3)
    assert daily.method == "daily_5_per_10k"
    assert daily.amount > 0


# --- Labor month-range validation -------------------------------------------



def test_month_range_validation_whole_and_partial():
    whole = validate_month_range_text("2023年12月至2024年2月")
    assert whole.status == ValidationStatus.VALID
    assert whole.code == "MONTH_RANGE_WHOLE"

    partial = validate_month_range_text("2023年12月至2月")
    assert partial.status == ValidationStatus.VALID
    assert partial.code == "MONTH_RANGE_PARTIAL"
    assert "人工核对" in partial.message


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_month_range_validation_empty_requires_input(raw):
    result = validate_month_range_text(raw)
    assert result.status == ValidationStatus.INVALID_FORMAT
    assert result.is_valid is False


@pytest.mark.parametrize("raw", ["不清楚", "2024年5月至2024年1月"])
def test_month_range_validation_malformed_and_reversed(raw):
    result = validate_month_range_text(raw)
    assert result.status == ValidationStatus.INVALID_FORMAT
    assert result.is_valid is False
