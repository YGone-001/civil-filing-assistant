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
