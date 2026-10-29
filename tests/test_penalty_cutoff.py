# File: tests/test_penalty_cutoff.py
# Purpose: Contract penalty cutoff-date contract and provenance (P1-04 / D-02, P1-07 / D-07).
# Encoding: UTF-8
"""Regression coverage for the auxiliary penalty calculation cutoff contract.

The complaint used to claim "暂计至起诉之日" even when the amount came from a
manual entry or from a calculator run with an explicit (earlier) cutoff. The
page now records the calculation basis (method + actual cutoff) and the claim
may only state a cutoff while that basis is intact. All data is fictional.
"""

import datetime

from helpers import make_wizard, prepare_case
from presenters.model_builder import build_case_model


def _freeze_today(monkeypatch, y, m, d):
    """Freeze ``datetime.date.today()`` for deterministic fallback assertions."""
    real_date = datetime.date

    class _FrozenDate(real_date):
        @classmethod
        def today(cls):
            return cls(y, m, d)

    monkeypatch.setattr(datetime, "date", _FrozenDate)
    return _FrozenDate


def _penalty_claim(model):
    claims = [c for c in model.render_claims() if "违约金" in c]
    assert len(claims) == 1, claims
    return claims[0]


def _prepared_page():
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.contract_claim_page
    page.unpaid_amount.setText("30000")
    page.overdue_start.setText("2023-03-01")
    page.lpr_value.setText("3.45")
    page.lpr_multiple.setText("4")
    return wizard, page


def test_explicit_cutoff_is_recorded_end_to_end(qapp):
    wizard, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()

    days = (datetime.date(2023, 6, 30) - datetime.date(2023, 3, 1)).days
    expected = 30000 * ((3.45 * 4) / 100.0) * (days / 365.0)
    assert page.penalty_amount.text() == f"{expected:.2f}"

    basis = page.get_penalty_calc_basis()
    assert basis == {"method": "lpr_multiple", "cutoff": "2023-06-30"}

    model = build_case_model(wizard)
    assert model.penalty_cutoff_date == "2023-06-30"
    assert model.penalty_calc_cutoff == "2023-06-30"
    assert model.penalty_calc_method == "lpr_multiple"

    claim = _penalty_claim(model)
    assert f"暂计至 2023-06-30 为" in claim
    assert "起诉之日" not in claim


def test_blank_cutoff_uses_the_calculation_day_and_is_recorded(qapp, monkeypatch):
    frozen = _freeze_today(monkeypatch, 2026, 3, 15)
    wizard, page = _prepared_page()
    page.overdue_end.setText("")  # blank -> calculation-day fallback
    page.calc_penalty_by_lpr_multiple()

    basis = page.get_penalty_calc_basis()
    assert basis == {"method": "lpr_multiple", "cutoff": "2026-03-15"}
    assert basis["cutoff"] == frozen(2026, 3, 15).isoformat()

    claim = _penalty_claim(build_case_model(wizard))
    assert "暂计至 2026-03-15" in claim
    assert "起诉之日" not in claim


def test_manual_amount_gets_flat_claim_without_cutoff_claim(qapp):
    """A hand-typed amount must not be described as app-calculated."""
    wizard, page = _prepared_page()
    page.penalty_amount.setText("5000")  # manual entry, no calculator run

    assert page.get_penalty_calc_basis() is None
    model = build_case_model(wizard)
    assert model.penalty_calc_method == ""
    assert model.penalty_calc_cutoff == ""
    claim = _penalty_claim(model)
    assert "人民币 5000 元" in claim
    assert "暂计至" not in claim
    assert "起诉之日" not in claim


def test_invalid_explicit_cutoff_blocks_the_calculator(qapp, dialog_recorder):
    wizard, page = _prepared_page()
    page.penalty_amount.setText("")
    page.overdue_end.setText("不是日期")

    page.calc_penalty_by_lpr_multiple()

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert page.penalty_amount.text() == ""
    assert page.get_penalty_calc_basis() is None


def test_reversed_cutoff_blocks_the_calculator(qapp, dialog_recorder):
    wizard, page = _prepared_page()
    page.penalty_amount.setText("")
    page.overdue_end.setText("2023-02-01")  # before the start date

    page.calc_penalty_by_lpr_multiple()

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert page.penalty_amount.text() == ""
    assert page.get_penalty_calc_basis() is None


def test_daily_calculator_records_its_basis(qapp):
    wizard, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    assert page.penalty_amount.text() == "105.00"  # 30000 × 0.0005 × 7 days
    assert page.get_penalty_calc_basis() == {
        "method": "daily_5_per_10k",
        "cutoff": "2023-03-08",
    }


def test_editing_calculation_inputs_invalidates_the_basis(qapp):
    wizard, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()
    assert page.get_penalty_calc_basis() is not None

    page.overdue_start.setText("2023-04-01")
    assert page.get_penalty_calc_basis() is None

    page.calc_penalty_by_lpr_multiple()  # recalculate on the new inputs
    assert page.get_penalty_calc_basis()["cutoff"] == "2023-06-30"
    page.lpr_value.setText("3.65")
    assert page.get_penalty_calc_basis() is None


def test_manual_override_after_calculation_invalidates_the_basis(qapp):
    wizard, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()
    assert page.get_penalty_calc_basis() is not None

    page.penalty_amount.setText("123.45")
    assert page.get_penalty_calc_basis() is None

    claim = _penalty_claim(build_case_model(wizard))
    assert "暂计至" not in claim


def test_calculation_basis_survives_back_next_navigation(qapp):
    wizard, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()

    from PySide6.QtWidgets import QWizard

    back = wizard.button(QWizard.BackButton)
    next_btn = wizard.button(QWizard.NextButton)
    back.click()
    qapp.processEvents()
    next_btn.click()
    qapp.processEvents()

    assert page.get_penalty_calc_basis() == {
        "method": "lpr_multiple",
        "cutoff": "2023-06-30",
    }
    assert "暂计至 2023-06-30" in _penalty_claim(build_case_model(wizard))


def test_provenance_hints_present_on_contract_page(qapp):
    """The LPR defaults must be presented as unverified examples (P1-07)."""
    wizard, page = _prepared_page()
    help_text = page.calc_help.text()
    assert "示例" in help_text
    assert "不代表" in help_text
    assert "核实" in help_text
    assert "核实" in page.lpr_value.placeholderText()
