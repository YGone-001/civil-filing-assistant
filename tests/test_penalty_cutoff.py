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
import os

from helpers import docx_all_text, make_wizard, prepare_case
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
    wizard, presenter = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.contract_claim_page
    page.unpaid_amount.setText("30000")
    page.overdue_start.setText("2023-03-01")
    page.lpr_value.setText("3.45")
    page.lpr_multiple.setText("4")
    return wizard, presenter, page


def test_explicit_cutoff_is_recorded_end_to_end(qapp):
    wizard, presenter, page = _prepared_page()
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
    wizard, presenter, page = _prepared_page()
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
    wizard, presenter, page = _prepared_page()
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
    wizard, presenter, page = _prepared_page()
    page.penalty_amount.setText("")
    page.overdue_end.setText("不是日期")

    page.calc_penalty_by_lpr_multiple()

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert page.penalty_amount.text() == ""
    assert page.get_penalty_calc_basis() is None


def test_reversed_cutoff_blocks_the_calculator(qapp, dialog_recorder):
    wizard, presenter, page = _prepared_page()
    page.penalty_amount.setText("")
    page.overdue_end.setText("2023-02-01")  # before the start date

    page.calc_penalty_by_lpr_multiple()

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert page.penalty_amount.text() == ""
    assert page.get_penalty_calc_basis() is None


def test_daily_calculator_records_its_basis(qapp):
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    assert page.penalty_amount.text() == "105.00"  # 30000 × 0.0005 × 7 days
    assert page.get_penalty_calc_basis() == {
        "method": "daily_5_per_10k",
        "cutoff": "2023-03-08",
    }


def test_editing_calculation_inputs_invalidates_the_basis(qapp):
    wizard, presenter, page = _prepared_page()
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
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()
    assert page.get_penalty_calc_basis() is not None

    page.penalty_amount.setText("123.45")
    assert page.get_penalty_calc_basis() is None

    claim = _penalty_claim(build_case_model(wizard))
    assert "暂计至" not in claim


def test_calculation_basis_survives_back_next_navigation(qapp):
    wizard, presenter, page = _prepared_page()
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
    wizard, presenter, page = _prepared_page()
    help_text = page.calc_help.text()
    assert "示例" in help_text
    assert "不代表" in help_text
    assert "核实" in help_text
    assert "核实" in page.lpr_value.placeholderText()


# --- C-01: the claimed standard must name the calculator actually used ------


def _redirect_home(monkeypatch, tmp_path):
    """Redirect expanduser BEFORE wizard creation: ExportPage captures its
    default output directory at construction time."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))
    return home / "Desktop"


def _export_complaint(desktop, wizard, presenter):
    """Run a real export and return the generated complaint's full text."""
    assert presenter.attempt_finish() == presenter.FINISH_SUCCESS
    docs = sorted(desktop.rglob("*.docx"))
    assert len(docs) == 3
    complaint = next(d for d in docs if "民事起诉状" in d.name)
    return docx_all_text(complaint)


def test_daily_calculation_describes_daily_standard_not_lpr(qapp):
    """C-01 repro (deterministic): a daily 万五 amount must never be described
    with the LPR-multiple standard, even when the LPR fields hold values."""
    wizard, presenter, page = _prepared_page()  # LPR fields carry the 3.45 / 4 defaults
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    assert page.penalty_amount.text() == "105.00"
    assert page.get_penalty_calc_basis() == {
        "method": "daily_5_per_10k",
        "cutoff": "2023-03-08",
    }

    claim = _penalty_claim(build_case_model(wizard))
    assert "3.45%×4" not in claim, claim
    assert "日万分之五" in claim, claim


def test_daily_method_docx_names_daily_standard(qapp, monkeypatch, tmp_path, dialog_recorder):
    """The exported complaint must state the method that produced the amount."""
    desktop = _redirect_home(monkeypatch, tmp_path)
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    text = _export_complaint(desktop, wizard, presenter)

    assert "105.00" in text
    assert "日万分之五" in text
    assert "3.45%×4" not in text
    assert "起诉之日" not in text
    assert "30000" in text  # the outstanding-principal claim is unchanged


def test_daily_basis_valid_without_lpr_inputs(qapp):
    """The daily calculator must not require LPR inputs to keep its basis."""
    wizard, presenter, page = _prepared_page()
    page.lpr_value.setText("")
    page.lpr_multiple.setText("")
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    assert page.penalty_amount.text() == "105.00"
    assert page.get_penalty_calc_basis()["method"] == "daily_5_per_10k"

    claim = _penalty_claim(build_case_model(wizard))
    assert "日万分之五" in claim
    assert "3.45%×4" not in claim


def test_editing_lpr_after_daily_calc_conservatively_invalidates(qapp):
    """Editing any recorded-relevant input clears the basis (no false facts)."""
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()
    assert page.get_penalty_calc_basis() is not None

    page.lpr_value.setText("3.65")

    assert page.get_penalty_calc_basis() is None
    claim = _penalty_claim(build_case_model(wizard))
    assert "日万分之五" not in claim and "3.45%×4" not in claim


def test_lpr_method_does_not_mention_daily_standard(qapp):
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()

    claim = _penalty_claim(build_case_model(wizard))
    assert "3.45%×4" in claim
    assert "万分之五" not in claim
    assert "日万分之五" not in claim


def test_switching_daily_then_lpr_updates_recorded_method(qapp):
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()
    page.calc_penalty_by_lpr_multiple()

    basis = page.get_penalty_calc_basis()
    assert basis["method"] == "lpr_multiple"
    claim = _penalty_claim(build_case_model(wizard))
    assert "3.45%×4" in claim
    assert "日万分之五" not in claim


def test_switching_lpr_then_daily_updates_recorded_method(qapp):
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_by_lpr_multiple()
    page.calc_penalty_daily_5_per_10k()

    basis = page.get_penalty_calc_basis()
    assert basis["method"] == "daily_5_per_10k"
    assert page.penalty_amount.text() == "105.00"
    claim = _penalty_claim(build_case_model(wizard))
    assert "日万分之五" in claim
    assert "3.45%×4" not in claim


def test_editing_cutoff_invalidates_basis(qapp):
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()
    assert page.get_penalty_calc_basis() is not None

    page.overdue_end.setText("2023-07-31")

    assert page.get_penalty_calc_basis() is None
    claim = _penalty_claim(build_case_model(wizard))
    assert "暂计至" not in claim


def test_preview_and_docx_agree_on_daily_method(qapp, monkeypatch, tmp_path, dialog_recorder):
    """Preview and the exported DOCX must use the same calculation description."""
    desktop = _redirect_home(monkeypatch, tmp_path)
    wizard, presenter, page = _prepared_page()
    page.overdue_end.setText("2023-03-08")
    page.calc_penalty_daily_5_per_10k()

    dialog_recorder.clear()
    wizard.export_page.show_preview()
    preview = getattr(wizard.export_page, "_last_preview_text", "")
    assert preview, "no preview produced"
    assert "日万分之五" in preview
    assert "3.45%×4" not in preview

    text = _export_complaint(desktop, wizard, presenter)
    assert "日万分之五" in text
    assert "3.45%×4" not in text
    assert "105.00" in text
