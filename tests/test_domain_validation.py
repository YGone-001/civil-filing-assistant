# File: tests/test_domain_validation.py
# Purpose: Unit tests for full-date validation and the structured validation
#          contract, plus GUI-callback safety (P2-03 / P2-07).
# Encoding: UTF-8
"""Direct tests for models/validation.py and its production consumption.

Invalid full-date input must produce a controlled validation outcome — never
an uncaught Qt callback exception and never a fabricated calculation result.
All sample data is fictional.
"""

import datetime

import pytest

from models.calculations import CalculationError, parse_month_range
from models.validation import (
    DateStatus,
    ValidationResult,
    ValidationStatus,
    parse_full_date,
)


# --- parse_full_date ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2023-01-31", datetime.date(2023, 1, 31)),
        ("2023/1/31", datetime.date(2023, 1, 31)),
        ("2023年1月31日", datetime.date(2023, 1, 31)),
        (" 2024-02-29 ", datetime.date(2024, 2, 29)),   # leap year
    ],
)
def test_full_date_valid_forms(raw, expected):
    result = parse_full_date(raw)
    assert result.status == DateStatus.VALID
    assert result.value == expected


@pytest.mark.parametrize(
    "raw,status",
    [
        ("", DateStatus.EMPTY),
        ("   ", DateStatus.EMPTY),
        (None, DateStatus.EMPTY),
        ("2023-01", DateStatus.INVALID_FORMAT),          # missing day
        ("01-02", DateStatus.INVALID_FORMAT),            # missing year
        ("20230101", DateStatus.INVALID_FORMAT),         # no separators
        ("垃圾", DateStatus.INVALID_FORMAT),
        ("2023-02-29", DateStatus.INVALID_CALENDAR_DATE),  # non-leap year
        ("2023-02-30", DateStatus.INVALID_CALENDAR_DATE),
        ("2023-00-10", DateStatus.INVALID_CALENDAR_DATE),  # month 00
        ("2023-13-10", DateStatus.INVALID_CALENDAR_DATE),  # month 13
        ("2023-01-00", DateStatus.INVALID_CALENDAR_DATE),  # day 00
        ("1899-12-31", DateStatus.OUT_OF_SUPPORTED_RANGE),
        ("2101-01-01", DateStatus.OUT_OF_SUPPORTED_RANGE),
    ],
)
def test_full_date_invalid_and_edge_inputs(raw, status):
    result = parse_full_date(raw)
    assert result.status == status
    assert result.value is None


def test_full_date_never_raises_and_never_substitutes_a_date():
    """A malformed date must not unexpectedly escape from a Qt callback."""
    for raw in ("不是日期", "----", "２０２３年？", "99999999999999-1-1", "2023年月日"):
        result = parse_full_date(raw)
        assert result.status != DateStatus.VALID
        assert result.value is None


def test_full_date_leap_year_february_29_variants():
    assert parse_full_date("2024年2月29日").status == DateStatus.VALID
    assert parse_full_date("2100-02-29").status == DateStatus.INVALID_CALENDAR_DATE


# --- C-03: extra components and surrounding text must be rejected -----------


@pytest.mark.parametrize(
    "raw",
    [
        "2023-01-31-99",            # extra numeric component
        "2023-01-31-01",
        "2023年01月31日-extra-99",   # trailing material after a Chinese date
        "2023/01/31/99",
        "abc2023-01-31",            # textual prefix
        "2023-01-31备注",            # textual suffix
    ],
)
def test_full_date_rejects_extra_components_and_surrounding_text(raw):
    result = parse_full_date(raw)
    assert result.status == DateStatus.INVALID_FORMAT
    assert result.value is None


def test_full_date_preserved_historical_forms():
    """The strict grammar keeps every documented valid representation."""
    for raw, expected in (
        ("2023-01-31", datetime.date(2023, 1, 31)),
        ("2023/1/31", datetime.date(2023, 1, 31)),
        ("2023.1.31", datetime.date(2023, 1, 31)),
        ("2023年1月31日", datetime.date(2023, 1, 31)),
        ("2023年1月31", datetime.date(2023, 1, 31)),  # trailing 日 optional
        ("2023-1-3", datetime.date(2023, 1, 3)),
    ):
        result = parse_full_date(raw)
        assert result.status == DateStatus.VALID, raw
        assert result.value == expected, raw


# --- C-04: property user-total validation must be callback-safe -------------


def test_property_user_total_malformed_is_controlled(qapp):
    """Malformed comparison amounts must not escape update_calc (direct or via
    a Qt signal) and must not erase the valid system estimate."""
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    page = wizard.property_claim_page
    assert "7761.60" in page.calc_label.text()  # valid estimate established

    for raw in ("abc", "NaN", "Infinity", "1.2.3"):
        page.total_input.setText(raw)
        page.update_calc()  # must not raise
        assert "7761.60" in page.calc_label.text(), raw  # estimate preserved
        assert page.warn_label.text(), raw  # a correction hint is shown

    # Empty / zero: no warning (historically non-errors).
    page.total_input.setText("")
    page.update_calc()
    assert page.warn_label.text() == ""
    page.total_input.setText("0")
    page.update_calc()
    assert page.warn_label.text() == ""

    # Negative and matching/mismatched values must not raise either.
    for raw in ("-100", "7761.60", "9000"):
        page.total_input.setText(raw)
        page.update_calc()
        assert "7761.60" in page.calc_label.text()


def test_property_user_total_malformed_is_safe_via_qt_signal(qapp):
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    page = wizard.property_claim_page
    page.total_input.setText("NaN")
    page.total_input.textChanged.emit("NaN")  # connected slot must not raise
    assert "7761.60" in page.calc_label.text()


# --- C-06: the manual penalty warning consumes the shared Decimal contract ---


def test_penalty_amount_warning_uses_decimal_validation(qapp):
    page = _contract_page()

    page.penalty_amount.setText("NaN")
    assert "数字" in page.penalty_warning.text()

    page.penalty_amount.setText("Infinity")
    assert "数字" in page.penalty_warning.text()

    page.penalty_amount.setText("-5")
    assert "负数" in page.penalty_warning.text()

    page.penalty_amount.setText("5000")
    assert "人工核对" in page.penalty_warning.text()

    page.penalty_amount.setText("")
    assert page.penalty_warning.text() == ""


# --- ValidationResult contract -----------------------------------------------


def test_validation_result_is_frozen():
    result = ValidationResult("field", ValidationStatus.VALID, "CODE", "msg")
    with pytest.raises(Exception):
        result.status = ValidationStatus.INVALID_FORMAT  # dataclass(frozen=True)


def test_validation_result_is_valid_distinguishes_allowed_empty():
    assert ValidationResult("f", ValidationStatus.VALID).is_valid is True
    assert ValidationResult("f", ValidationStatus.EMPTY_ALLOWED).is_valid is True
    assert ValidationResult("f", ValidationStatus.REQUIRED_MISSING).is_valid is False
    assert ValidationResult("f", ValidationStatus.INVALID_FORMAT).is_valid is False
    assert ValidationResult("f", ValidationStatus.INVALID_RANGE).is_valid is False
    assert ValidationResult("f", ValidationStatus.INCONSISTENT).is_valid is False


# --- Production consumption: GUI-callback safety -----------------------------


def _contract_page():
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    return wizard.contract_claim_page


def test_contract_cutoff_resolution_never_raises_on_garbage(qapp):
    page = _contract_page()
    page.overdue_start.setText("垃圾")
    start, cutoff, error = page._resolve_overdue_cutoff()
    assert start is None and cutoff is None
    assert error.status == ValidationStatus.INVALID_FORMAT
    assert error.message

    page.overdue_start.setText("2023-03-01")
    page.overdue_end.setText("不是日期")
    start, cutoff, error = page._resolve_overdue_cutoff()
    assert start is None and cutoff is None  # error paths return no dates
    assert error.status == ValidationStatus.INVALID_FORMAT
    assert error.field == "c_overdue_end"


def test_contract_cutoff_reversed_reports_inconsistent_interval(qapp):
    page = _contract_page()
    page.overdue_start.setText("2023-03-01")
    page.overdue_end.setText("2023-02-01")
    start, cutoff, error = page._resolve_overdue_cutoff()
    assert start is None and cutoff is None
    assert error.status == ValidationStatus.INVALID_RANGE
    assert error.code == "OVERDUE_REVERSED"


def test_property_page_update_calc_never_raises_on_garbage(qapp):
    """The historical failure mode: a malformed date escaping update_calc."""
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    page = wizard.property_claim_page

    for start, end in (("垃圾", "2024-12-31"), ("2024-01-01", "2024-13-40"),
                       ("2024-13-01", "2023-01-01"), ("", "")):
        page.period_start.setText(start)
        page.period_end.setText(end)
        page.update_calc()  # must not raise
        assert "尚无法计算" in page.calc_label.text()
        assert "月数=0，总本金=0.00" not in page.calc_label.text()


def test_property_page_update_calc_matches_model_value(qapp):
    from helpers import make_wizard, prepare_case

    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    page = wizard.property_claim_page
    page.update_calc()
    assert "7761.60" in page.calc_label.text()
    assert "月数=24" in page.calc_label.text()


def test_loan_rate_validation_consumes_shared_contract(qapp):
    from helpers import make_wizard

    wizard, _ = make_wizard()
    page = wizard.loan_claim_page

    page.rate.setText("abc")
    assert page.rate_warning.text() == "请输入有效的数字"
    page.rate.setText("-1")
    assert page.rate_warning.text() == "年利率不应为负数，请核对。"
    page.rate.setText("")
    assert page.rate_warning.text() == ""
    page.rate.setText("14.6")
    assert "人工核对" in page.rate_warning.text()


def test_labor_period_validation_gates_the_model_fallback():
    """The labor model consumes the structured result for its fallback branch."""
    from models.case_model import LaborCaseModel

    model = LaborCaseModel()
    model.monthly_salary = "8000"

    model.unpaid_months = "不清楚"
    result = model._unpaid_period_result()
    assert result.is_valid is False
    assert model._ensure_unpaid_total() is None
    assert "人工确认" in "".join(model.render_claims())

    model.unpaid_months = "2023年12月至2024年2月"
    result = model._unpaid_period_result()
    assert result.is_valid is True
    assert model._ensure_unpaid_total() == (3, False)
    assert model.total_unpaid_amount == "24000.00"


def test_parse_month_range_semantics_unchanged():
    """The labor-specific parser keeps its own contract (P2-03 §5.3)."""
    assert parse_month_range("2023年12月至2024年2月") == (3, False)
    assert parse_month_range("2023年12月至2月") == (3, True)
    with pytest.raises(CalculationError):
        parse_month_range("")
    with pytest.raises(CalculationError):
        parse_month_range("2024年5月至2024年1月")
