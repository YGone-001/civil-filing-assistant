# File: tests/test_labor_procedure.py
# Purpose: The labour procedural classification decides eligibility, wording
# and blocking (Phase 5-B decision table).
# Encoding: UTF-8
"""Regression coverage for the labour procedural-state model.

The former tri-state (``has_arbitrated``) both over-blocked lawful paths and
let unsafe complaints through. These tests pin the fail-closed decision table
implemented in :mod:`utils.labor_security`:

* pure evaluator matrix for every state, including the date thresholds of
  仲裁法 第29条 (5日) / 第43条 (45+15日) and 解释一 第5/6/7/12条 diversions,
* page behaviour (conditional rows, immediate guidance, data preservation),
* draft capture/restore of the classification,
* export-gate blocking with explanations and no DOCX output,
* the per-state arbitration sentence of the generated complaint (the old
  combined “仲裁裁决书（或不予受理通知书）” wording must never return).

All facts are fictional; dates are chosen relative to an injected or real
"today" so the statutory-day thresholds stay deterministic.
"""

import datetime
import os

import pytest
from PySide6.QtWidgets import QWizard

from helpers import (
    fill_case_facts,
    make_wizard,
    prepare_case,
    select_case,
    set_labor_non_final_award,
)
from utils.labor_security import (
    GROUND_NOT_LABOR_DISPUTE,
    GROUND_NO_JURISDICTION,
    GROUND_OTHER_OR_UNSTATED,
    GROUND_PARTY_UNQUALIFIED,
    PROCEDURE_ACCEPTANCE_OVERDUE,
    PROCEDURE_APPLICATION_PENDING,
    PROCEDURE_AWARD_OVERDUE,
    PROCEDURE_FINAL_AWARD,
    PROCEDURE_MEDIATION_EFFECTIVE,
    PROCEDURE_NON_FINAL_AWARD,
    PROCEDURE_NOT_ACCEPTED,
    PROCEDURE_NOT_APPLIED,
    PROCEDURE_OTHER_OR_UNCERTAIN,
    ROLE_EMPLOYER,
    ROLE_EMPLOYEE,
    evaluate_labor_eligibility,
)
from drafts import schema
from views.draft_io import apply_draft, capture_draft

TODAY = datetime.date(2026, 11, 22)
COMMISSION = "示例劳动人事争议仲裁委员会"


def _allow(procedure, **kwargs):
    kwargs.setdefault("role", ROLE_EMPLOYEE)
    kwargs.setdefault("commission", COMMISSION)
    kwargs.setdefault("today", TODAY)
    eligibility = evaluate_labor_eligibility(procedure, **kwargs)
    assert eligibility.eligible, eligibility.reason
    return eligibility


def _block(procedure, **kwargs):
    kwargs.setdefault("role", ROLE_EMPLOYEE)
    kwargs.setdefault("commission", COMMISSION)
    kwargs.setdefault("today", TODAY)
    eligibility = evaluate_labor_eligibility(procedure, **kwargs)
    assert not eligibility.eligible
    assert eligibility.reason.strip()
    return eligibility


# --------------------------------------------------------------------------- #
# Pure decision-table matrix
# --------------------------------------------------------------------------- #


def test_unselected_state_blocks():
    eligibility = _block(None)
    assert "请先选择" in eligibility.reason


def test_not_applied_blocks_with_arbitration_guidance():
    eligibility = _block(PROCEDURE_NOT_APPLIED)
    assert "申请仲裁" in eligibility.reason
    assert "不能为本阶段生成文书" in eligibility.reason


def test_application_pending_blocks_until_procedure_concludes():
    eligibility = _block(PROCEDURE_APPLICATION_PENDING)
    assert "程序进行中" in eligibility.reason
    assert "第五条" in eligibility.reason


def test_mediation_effective_blocks_with_execution_guidance():
    eligibility = _block(
        PROCEDURE_MEDIATION_EFFECTIVE,
        receipt_date="2024-06-01",
    )
    assert "调解书" in eligibility.reason
    assert "第四十二条" in eligibility.reason
    assert "申请执行" in eligibility.reason


def test_other_or_uncertain_blocks_with_review_guidance():
    eligibility = _block(PROCEDURE_OTHER_OR_UNCERTAIN)
    assert "咨询法律专业人士" in eligibility.reason


def test_acceptance_overdue_requires_five_days_to_elapse():
    fresh = _block(
        PROCEDURE_ACCEPTANCE_OVERDUE,
        delay_exception=False,
        application_date="2026-11-20",
    )
    assert "尚未届满" in fresh.reason
    assert "第二十九条" in fresh.reason

    _allow(
        PROCEDURE_ACCEPTANCE_OVERDUE,
        delay_exception=False,
        application_date="2026-11-10",  # 12 days before TODAY
    )


def test_acceptance_overdue_rejects_invalid_or_future_dates():
    _block(
        PROCEDURE_ACCEPTANCE_OVERDUE,
        delay_exception=False,
        application_date="not-a-date",
    )
    _block(
        PROCEDURE_ACCEPTANCE_OVERDUE,
        delay_exception=False,
        application_date="2026-12-01",  # future
    )
    _block(
        PROCEDURE_ACCEPTANCE_OVERDUE,
        delay_exception=False,
        application_date="",
    )


def test_award_overdue_requires_sixty_days_to_elapse():
    fresh = _block(
        PROCEDURE_AWARD_OVERDUE,
        delay_exception=False,
        acceptance_date="2026-10-01",
    )
    assert "尚未届满" in fresh.reason
    assert "第四十三条" in fresh.reason

    _allow(
        PROCEDURE_AWARD_OVERDUE,
        delay_exception=False,
        acceptance_date="2026-01-15",  # far beyond 45+15 days
    )


def test_award_overdue_rejects_invalid_or_future_dates():
    _block(
        PROCEDURE_AWARD_OVERDUE,
        delay_exception=False,
        acceptance_date="2026/10/01",
    )
    _block(
        PROCEDURE_AWARD_OVERDUE,
        delay_exception=False,
        acceptance_date="2026-12-31",
    )


@pytest.mark.parametrize("state", [PROCEDURE_ACCEPTANCE_OVERDUE, PROCEDURE_AWARD_OVERDUE])
def test_delay_exception_must_be_confirmed_negative(state):
    kwargs = {"application_date": "2020-01-01", "acceptance_date": "2020-01-01"}
    _block(state, delay_exception=None, **kwargs)
    blocked = _block(state, delay_exception=True, **kwargs)
    assert "第12条" in blocked.reason
    _allow(state, delay_exception=False, **kwargs)


def test_non_acceptance_ground_is_required():
    eligibility = _block(
        PROCEDURE_NOT_ACCEPTED, refusal_ground=None, receipt_date="2024-06-01"
    )
    assert "不予受理决定载明的理由" in eligibility.reason


def test_no_jurisdiction_ground_blocks_with_reapplication_guidance():
    blocked = _block(
        PROCEDURE_NOT_ACCEPTED,
        refusal_ground=GROUND_NO_JURISDICTION,
        receipt_date="2024-06-01",
    )
    assert "有管辖权" in blocked.reason
    assert "第5条" in blocked.reason


@pytest.mark.parametrize(
    "ground",
    [GROUND_NOT_LABOR_DISPUTE, GROUND_PARTY_UNQUALIFIED, GROUND_OTHER_OR_UNSTATED],
)
def test_other_non_acceptance_grounds_allow_generation_with_ground_warning(ground):
    eligibility = _allow(
        PROCEDURE_NOT_ACCEPTED, refusal_ground=ground, receipt_date="2024-06-01"
    )
    assert eligibility.warning.strip()


def test_not_acceptance_requires_commission_and_notice_date():
    _block(
        PROCEDURE_NOT_ACCEPTED,
        refusal_ground=GROUND_NOT_LABOR_DISPUTE,
        commission="",
        receipt_date="2024-06-01",
    )
    _block(
        PROCEDURE_NOT_ACCEPTED,
        refusal_ground=GROUND_NOT_LABOR_DISPUTE,
        receipt_date="",
    )


def test_final_award_employer_blocks_with_cancellation_guidance():
    blocked = _block(
        PROCEDURE_FINAL_AWARD,
        role=ROLE_EMPLOYER,
        receipt_date="2024-06-01",
    )
    assert "一裁终局" in blocked.reason
    assert "第四十九条" in blocked.reason
    assert "撤销" in blocked.reason


def test_final_award_employee_allows_generation_with_window_warning():
    eligibility = _allow(
        PROCEDURE_FINAL_AWARD, role=ROLE_EMPLOYEE, receipt_date="2024-06-01"
    )
    assert "十五日" in eligibility.warning
    _block(PROCEDURE_FINAL_AWARD, role=None, receipt_date="2024-06-01")


def test_filing_window_warning_intensifies_after_fifteen_days():
    recent = _allow(
        PROCEDURE_NON_FINAL_AWARD, receipt_date="2026-11-20",  # 2 days ago
    )
    late = _allow(
        PROCEDURE_NON_FINAL_AWARD, receipt_date="2026-01-01",  # ~10 months ago
    )
    assert "十五日" in recent.warning
    assert "超过十五日" not in recent.warning
    assert "超过十五日" in late.warning


def test_eligible_states_require_commission():
    _block(PROCEDURE_NON_FINAL_AWARD, commission="", receipt_date="2024-06-01")
    _block(PROCEDURE_FINAL_AWARD, role=ROLE_EMPLOYEE, commission="", receipt_date="2024-06-01")


# --------------------------------------------------------------------------- #
# Page behaviour
# --------------------------------------------------------------------------- #


def _select(page, state):
    index = page.procedure_combo.findData(state)
    assert index >= 0, f"state {state} missing from the selector"
    page.procedure_combo.setCurrentIndex(index)


def test_unselected_page_shows_placeholder_and_blocks(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    page = wizard.labor_claim_page
    assert not page.isComplete()
    assert "请先选择" in page.arbitration_hint.text()


def test_procedure_selection_updates_description_and_guidance(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page

    _select(page, PROCEDURE_MEDIATION_EFFECTIVE)
    assert not page.isComplete()
    assert "调解书" in page.arbitration_hint.text()

    _select(page, PROCEDURE_NON_FINAL_AWARD)
    # The fixture pre-filled these; clear them so "missing field" blocks.
    page.arb_commission.setText("")
    page.arb_receipt_date.setText("")
    assert not page.isComplete()
    assert "仲裁机构" in page.arbitration_hint.text()

    page.arb_commission.setText(COMMISSION)
    assert "收到裁决书的日期" in page.arbitration_hint.text()

    page.arb_receipt_date.setText("2024-06-01")
    assert page.isComplete()
    assert page.arbitration_hint.isHidden()
    assert "十五日" in page.procedure_warning.text()


def test_conditional_rows_follow_the_selected_state(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    page = wizard.labor_claim_page

    _select(page, PROCEDURE_NOT_APPLIED)
    assert page.arb_commission.isHidden()
    assert page.arb_receipt_date.isHidden()
    assert page._role_row.isHidden()
    assert page._delay_row.isHidden()
    assert page._refusal_row.isHidden()

    _select(page, PROCEDURE_NOT_ACCEPTED)
    assert not page.arb_commission.isHidden()
    assert not page.arb_receipt_date.isHidden()
    assert "不予受理通知书" in page._receipt_label.text()
    assert not page._refusal_row.isHidden()
    assert not page._role_row.isHidden()

    _select(page, PROCEDURE_AWARD_OVERDUE)
    assert page.arb_receipt_date.isHidden()
    assert not page.arb_acceptance_date.isHidden()
    assert not page._delay_row.isHidden()
    assert not page._role_row.isHidden()
    assert page._refusal_row.isHidden()

    _select(page, PROCEDURE_FINAL_AWARD)
    assert not page.arb_receipt_date.isHidden()
    assert not page._role_row.isHidden()
    assert page._delay_row.isHidden()
    assert page._acceptance_label.isHidden()
    assert page.arb_acceptance_date.isHidden()


def test_switching_states_preserves_entered_values(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    page = wizard.labor_claim_page

    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    page.no_contract_yes.setChecked(True)

    _select(page, PROCEDURE_MEDIATION_EFFECTIVE)
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    assert page.arb_commission.text() == COMMISSION
    assert page.arb_receipt_date.text() == "2024-06-01"
    assert page.get_has_no_contract() is True


def test_next_button_disabled_for_blocked_states(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    wizard.show()
    wizard.restart()
    for _ in range(3):
        wizard.next()  # welcome -> case selection -> party -> labour claim
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NOT_APPLIED)
    assert not wizard.button(QWizard.NextButton).isEnabled()
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    assert wizard.button(QWizard.NextButton).isEnabled()


def test_delay_confirmation_required_for_overdue_states(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_AWARD_OVERDUE)
    page.arb_commission.setText(COMMISSION)
    page.arb_acceptance_date.setText("2020-01-01")
    # Delay exception still 未确认.
    assert not page.isComplete()
    assert "迟延" in page.arbitration_hint.text()
    page.delay_no.setChecked(True)
    assert page.isComplete()


# --------------------------------------------------------------------------- #
# Draft capture / restore of the classification
# --------------------------------------------------------------------------- #


def _configured_labor_wizard():
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NOT_ACCEPTED)
    page._refusal_buttons[GROUND_PARTY_UNQUALIFIED].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    page.no_contract_no.setChecked(True)
    return wizard, presenter


def test_classification_flags_are_captured_and_restored(qapp):
    wizard, _ = _configured_labor_wizard()
    document = schema.validate_document(capture_draft(wizard, "labor_claim"))
    assert document.factual_flags["labor_procedure"] == PROCEDURE_NOT_ACCEPTED
    assert document.factual_flags["labor_refusal_ground"] == GROUND_PARTY_UNQUALIFIED
    assert document.factual_flags["labor_role"] == ROLE_EMPLOYEE
    assert document.factual_flags["labor_delay_exception"] is None
    assert document.factual_flags["is_no_contract"] is False

    fresh, _ = make_wizard()
    fresh.restart()
    result = apply_draft(fresh, document)
    page = fresh.labor_claim_page
    assert page.get_labor_procedure() == PROCEDURE_NOT_ACCEPTED
    assert page.get_refusal_ground() == GROUND_PARTY_UNQUALIFIED
    assert page.get_labor_role() == ROLE_EMPLOYEE
    assert page.get_delay_exception() is None
    assert page.get_has_no_contract() is False
    assert page.arb_commission.text() == COMMISSION
    assert page.arb_receipt_date.text() == "2024-06-01"
    assert result.resume_page_id == fresh.PAGE_LABOR_CLAIM


def test_restored_classification_keeps_navigation_intact(qapp, tmp_path, monkeypatch):
    """A labour draft restored on the claim page walks Back through the real
    route (Phase 5-A contract) while keeping the restored classification."""
    from PySide6.QtWidgets import QFileDialog

    from presenters.draft_presenter import DraftPresenter

    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NOT_ACCEPTED)
    page._refusal_buttons[GROUND_PARTY_UNQUALIFIED].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    # Stand on the labour claim page so the draft records it as the resume page.
    wizard.restart()
    for _ in range(3):
        wizard.next()
    path = tmp_path / "劳动程序草稿.cfdraft"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: (str(path), ""))
    )
    assert draft.save_draft() is True

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: (str(path), ""))
    )
    assert draft.open_draft() is True
    restored = draft.wizard
    assert restored.currentId() == restored.PAGE_LABOR_CLAIM
    assert restored.labor_claim_page.get_labor_procedure() == PROCEDURE_NOT_ACCEPTED

    restored.button(QWizard.BackButton).click()
    assert restored.currentId() == restored.PAGE_PARTY
    restored.button(QWizard.NextButton).click()
    assert restored.currentId() == restored.PAGE_LABOR_CLAIM
    assert restored.labor_claim_page.get_labor_procedure() == PROCEDURE_NOT_ACCEPTED
    assert restored.labor_claim_page.get_refusal_ground() == GROUND_PARTY_UNQUALIFIED


def test_legacy_style_draft_falls_back_to_the_claim_page(qapp):
    """A migrated draft (classified other_or_uncertain) must not pretend the
    case passed the procedure gate: with complete parties it restores onto the
    labour claim page, never onto the export page."""
    fields = {
        spec.key: ""
        for spec in schema.TEXT_FIELDS["labor"]
        if spec.key not in ("l_arb_application_date", "l_arb_acceptance_date")
        and spec.widget not in ("extra_claims", "extra_facts")
    }
    document = schema.validate_document(
        {
            "schema_version": 2,
            "case_type": "labor",
            "fields": fields,
            "parties": {
                "plaintiffs": [_party("原告甲（测试）")],
                "defendants": [_party("被告乙（测试）")],
            },
            "factual_flags": {"has_arbitrated": True, "is_no_contract": None},
            "evidence": {"state": "NOT_INITIALIZED", "rows": []},
            "resume_page": "export",
        }
    )
    assert document.factual_flags["labor_procedure"] == PROCEDURE_OTHER_OR_UNCERTAIN

    fresh, _ = make_wizard()
    fresh.restart()
    result = apply_draft(fresh, document)
    assert result.resume_page == "labor_claim"
    assert fresh.currentId() == fresh.PAGE_LABOR_CLAIM
    assert not fresh.labor_claim_page.isComplete()
    assert "无法确认" in fresh.labor_claim_page.arbitration_hint.text() or \
        "咨询法律专业人士" in fresh.labor_claim_page.arbitration_hint.text()


def _party(name):
    return {
        "name": name,
        "id_number": "示例证件号-" + name,
        "address": "示例地址",
        "phone": "13800000000",
        "is_company": False,
        "credit_code": "",
        "legal_representative": "",
    }


# --------------------------------------------------------------------------- #
# Export gate + generated wording
# --------------------------------------------------------------------------- #


def _redirect_desktop(monkeypatch, base):
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(base))
    return base / "Desktop"


def _complaint(docs):
    for doc in docs:
        if "民事起诉状" in doc.name:
            from helpers import docx_all_text

            return docx_all_text(doc)
    raise AssertionError(f"no complaint in {[d.name for d in docs]}")


def _finish(wizard, presenter):
    return presenter.attempt_finish()


def test_mediation_effective_export_is_blocked_without_output(
    qapp, monkeypatch, tmp_path, dialog_recorder
):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    _select(wizard.labor_claim_page, PROCEDURE_MEDIATION_EFFECTIVE)

    assert _finish(wizard, presenter) == presenter.FINISH_VALIDATION_FAILED
    warnings = [c for c in dialog_recorder if c["kind"] == "warning"]
    assert warnings and "调解书" in warnings[-1]["args"][2]
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))


def test_final_award_employer_export_is_blocked(qapp, monkeypatch, tmp_path, dialog_recorder):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_FINAL_AWARD)
    page._role_buttons[ROLE_EMPLOYER].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")

    assert _finish(wizard, presenter) == presenter.FINISH_VALIDATION_FAILED
    warnings = [c for c in dialog_recorder if c["kind"] == "warning"]
    assert warnings and "第四十九条" in warnings[-1]["args"][2]
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))


def test_final_award_employee_exports_with_exact_wording(
    qapp, monkeypatch, tmp_path
):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_FINAL_AWARD)
    page._role_buttons[ROLE_EMPLOYEE].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_case_no.setText("示例仲裁案号-终局-001")
    page.arb_receipt_date.setText("2024-06-01")

    assert _finish(wizard, presenter) == presenter.FINISH_SUCCESS
    text = _complaint(sorted(desktop.rglob("*.docx")))
    assert "并于2024-06-01收到该委员会作出的终局裁决" in text
    assert "原告对该裁决不服" in text
    assert "非终局" not in text
    assert "（或不予受理通知书）" not in text


def test_non_acceptance_exports_only_the_document_type_the_user_stated(
    qapp, monkeypatch, tmp_path
):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NOT_ACCEPTED)
    page._refusal_buttons[GROUND_NOT_LABOR_DISPUTE].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-05-20")

    assert _finish(wizard, presenter) == presenter.FINISH_SUCCESS
    text = _complaint(sorted(desktop.rglob("*.docx")))
    assert "不予受理书面决定" in text
    assert "2024-05-20" in text
    assert "（或不予受理通知书）" not in text


def test_overdue_paths_never_require_a_fabricated_award_date(
    qapp, monkeypatch, tmp_path
):
    """The statutory-delay paths generate without any award receipt date."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_AWARD_OVERDUE)
    page.delay_no.setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_acceptance_date.setText("2025-01-01")
    # The award receipt date is not part of this procedure: its row hides and
    # the generated complaint must not use it.
    assert page.arb_receipt_date.isHidden()

    assert _finish(wizard, presenter) == presenter.FINISH_SUCCESS
    text = _complaint(sorted(desktop.rglob("*.docx")))
    assert "该委员会于2025-01-01受理" in text
    assert "未作出仲裁裁决" in text
    assert "第四十三条第二款" in text
    assert "第四十二条" not in text
    # The (hidden, preserved) award receipt date is never asserted as fact.
    assert "2024-06-01" not in text


def test_acceptance_overdue_wording_cites_article_twenty_nine(
    qapp, monkeypatch, tmp_path
):
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_ACCEPTANCE_OVERDUE)
    page.delay_no.setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_application_date.setText("2025-06-01")

    assert _finish(wizard, presenter) == presenter.FINISH_SUCCESS
    text = _complaint(sorted(desktop.rglob("*.docx")))
    assert "未作出是否受理的决定" in text
    assert "第二十九条" in text


def test_gate_blocks_when_the_model_disagrees_with_the_page(qapp, monkeypatch, tmp_path, dialog_recorder):
    """Defense in depth: even if the model carries an unconfirmed
    classification, the export gate refuses and explains."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    # Prepare the page eligible, then tamper with the built model indirectly by
    # unselecting the procedure before finishing (user could do this by
    # clearing the combo through the placeholder item).
    page = wizard.labor_claim_page
    page.procedure_combo.setCurrentIndex(0)  # placeholder -> None

    assert _finish(wizard, presenter) == presenter.FINISH_VALIDATION_FAILED
    warnings = [c for c in dialog_recorder if c["kind"] == "warning"]
    assert warnings and "请先选择" in warnings[-1]["args"][2]
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))


def test_all_five_case_types_still_export_after_procedure_work(
    qapp, monkeypatch, tmp_path
):
    """The other four case types are untouched by the labour rework."""
    from helpers import CASE_TYPES, navigate_to_export

    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    for case_type in CASE_TYPES:
        prepare_case(wizard, case_type)
        navigate_to_export(wizard)
        assert _finish(wizard, presenter) == presenter.FINISH_SUCCESS, case_type
        docs = list(desktop.rglob("*.docx"))
        assert len(docs) == 3 * (CASE_TYPES.index(case_type) + 1), case_type


def test_fill_case_facts_labor_fixture_is_eligible(qapp):
    """The shared fixture must configure an eligible procedure."""
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    assert page.get_labor_procedure() == PROCEDURE_NON_FINAL_AWARD
    assert page.isComplete()
    assert page.evaluate_current().eligible


# --------------------------------------------------------------------------- #
# B5-01: employee-plaintiff contract (role + company-form plaintiff)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "state,extra",
    [
        (PROCEDURE_ACCEPTANCE_OVERDUE,
         {"delay_exception": False, "application_date": "2020-01-01"}),
        (PROCEDURE_NOT_ACCEPTED,
         {"refusal_ground": GROUND_OTHER_OR_UNSTATED, "receipt_date": "2024-06-01"}),
        (PROCEDURE_AWARD_OVERDUE,
         {"delay_exception": False, "acceptance_date": "2020-01-01"}),
        (PROCEDURE_NON_FINAL_AWARD, {"receipt_date": "2024-06-01"}),
        (PROCEDURE_FINAL_AWARD, {"receipt_date": "2024-06-01"}),
    ],
)
def test_every_complaint_path_requires_the_plaintiff_role(state, extra):
    blocked = _block(state, role=None, **extra)
    assert "请先确认您在本案中的身份" in blocked.reason


@pytest.mark.parametrize(
    "state,extra",
    [
        (PROCEDURE_ACCEPTANCE_OVERDUE,
         {"delay_exception": False, "application_date": "2020-01-01"}),
        (PROCEDURE_NOT_ACCEPTED,
         {"refusal_ground": GROUND_OTHER_OR_UNSTATED, "receipt_date": "2024-06-01"}),
        (PROCEDURE_AWARD_OVERDUE,
         {"delay_exception": False, "acceptance_date": "2020-01-01"}),
        (PROCEDURE_NON_FINAL_AWARD, {"receipt_date": "2024-06-01"}),
    ],
)
def test_employer_plaintiff_is_blocked_as_unsupported_template(state, extra):
    blocked = _block(state, role=ROLE_EMPLOYER, **extra)
    assert "不支持生成起诉状" in blocked.reason
    # The product boundary must not be misstated as a legal prohibition.
    assert "并不否定用人单位依法可享有的起诉权利" in blocked.reason
    assert "另行准备相应法律文书或咨询法律专业人士" in blocked.reason


def test_final_award_employer_keeps_article_forty_nine_guidance():
    blocked = _block(PROCEDURE_FINAL_AWARD, role=ROLE_EMPLOYER, receipt_date="2024-06-01")
    assert "一裁终局" in blocked.reason
    assert "第四十九条" in blocked.reason
    assert "撤销裁决" in blocked.reason


@pytest.mark.parametrize(
    "state,extra",
    [
        (PROCEDURE_ACCEPTANCE_OVERDUE,
         {"delay_exception": False, "application_date": "2020-01-01"}),
        (PROCEDURE_NOT_ACCEPTED,
         {"refusal_ground": GROUND_OTHER_OR_UNSTATED, "receipt_date": "2024-06-01"}),
        (PROCEDURE_AWARD_OVERDUE,
         {"delay_exception": False, "acceptance_date": "2020-01-01"}),
        (PROCEDURE_NON_FINAL_AWARD, {"receipt_date": "2024-06-01"}),
        (PROCEDURE_FINAL_AWARD, {"receipt_date": "2024-06-01"}),
    ],
)
def test_confirmed_employee_role_proceeds_when_procedural_facts_pass(state, extra):
    _allow(state, role=ROLE_EMPLOYEE, **extra)


def test_company_form_plaintiff_blocks_the_employee_template():
    blocked = _block(
        PROCEDURE_NON_FINAL_AWARD, plaintiff_is_company=True, receipt_date="2024-06-01"
    )
    assert "单位／公司" in blocked.reason
    assert "两者不一致" in blocked.reason


def test_page_role_row_follows_all_complaint_paths(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    for state in (PROCEDURE_NOT_APPLIED, PROCEDURE_APPLICATION_PENDING,
                  PROCEDURE_MEDIATION_EFFECTIVE, PROCEDURE_OTHER_OR_UNCERTAIN):
        _select(page, state)
        assert page._role_row.isHidden(), state
    for state in (PROCEDURE_ACCEPTANCE_OVERDUE, PROCEDURE_NOT_ACCEPTED,
                  PROCEDURE_AWARD_OVERDUE, PROCEDURE_NON_FINAL_AWARD,
                  PROCEDURE_FINAL_AWARD):
        _select(page, state)
        assert not page._role_row.isHidden(), state


def test_role_is_never_defaulted_to_employee(qapp):
    """Without user selection the role stays unconfirmed even on an otherwise
    filled page; the guidance asks for it before anything else."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    # Reset to a state the fixture did not configure, keeping the party/claim
    # fields, then verify the role itself is only ever a user choice.
    _select(page, PROCEDURE_AWARD_OVERDUE)
    page.delay_no.setChecked(True)
    page.arb_acceptance_date.setText("2020-01-01")
    assert page.get_labor_role() == ROLE_EMPLOYEE  # fixture chose it explicitly

    fresh, _ = make_wizard()
    select_case(fresh, "labor")
    fresh_page = fresh.labor_claim_page
    _select(fresh_page, PROCEDURE_NON_FINAL_AWARD)
    assert fresh_page.get_labor_role() is None
    assert "请先确认您在本案中的身份" in fresh_page._conditional_issue()


def test_company_plaintiff_contradiction_blocks_the_real_export_path(
    qapp, monkeypatch, tmp_path, dialog_recorder
):
    """Pre-fix this exact flow published three employee wage DOCX files for a
    company plaintiff; it must now be blocked with no output at all."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page._role_buttons[ROLE_EMPLOYEE].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    # Enter the page once so its party-form wiring is live (as in real use),
    # then mark the plaintiff as a company.
    wizard.show()
    page.initializePage()
    card = wizard.party_page.plaintiff_widgets[0]
    card["name"].setText("示例有限公司（虚构）")
    card["is_company"].setChecked(True)

    assert not page.isComplete()
    assert "单位／公司" in page.arbitration_hint.text()
    assert presenter.attempt_finish() == presenter.FINISH_VALIDATION_FAILED
    warnings = [c for c in dialog_recorder if c["kind"] == "warning"]
    assert warnings and "单位／公司" in warnings[-1]["args"][2]
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))


def test_unconfirmed_role_blocks_the_real_export_path(qapp, monkeypatch, tmp_path):
    """Pre-fix, role=None + non-final award exported the employee wage claim.
    Exclusive radio buttons cannot be unchecked, so the unconfirmed-role gate
    is exercised through a role-less v3 draft restored via the real open path:
    export is refused until the user confirms the role, then succeeds."""
    from PySide6.QtWidgets import QFileDialog

    from drafts import save_draft as save_draft_file
    from presenters.draft_presenter import DraftPresenter

    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    draft = DraftPresenter(wizard, presenter)
    from helpers import set_parties

    select_case(wizard, "labor")
    set_parties(wizard)
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    # role deliberately left unselected
    document = schema.validate_document(capture_draft(wizard, "labor_claim"))
    assert document.factual_flags["labor_role"] is None
    path = tmp_path / "role-less draft.cfdraft"
    save_draft_file(str(path), document)

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **kw: (str(path), "")),
    )
    assert draft.open_draft() is True
    restored = draft.wizard
    restored_page = restored.labor_claim_page
    assert restored_page.get_labor_role() is None
    assert not restored_page.isComplete()
    assert presenter.attempt_finish() == presenter.FINISH_VALIDATION_FAILED
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))

    # Confirming the role on the restored wizard (without retyping anything)
    # resolves the procedural block and restores the ordinary export path.
    # (The draft intentionally carries no claim fields, so the page's own
    # mandatory-field completeness stays off; the role block itself is gone.)
    restored_page._role_buttons[ROLE_EMPLOYEE].setChecked(True)
    assert restored_page._conditional_issue() == ""
    assert presenter.attempt_finish() == presenter.FINISH_SUCCESS
    assert len(list(desktop.rglob("*.docx"))) == 3


def test_restored_draft_without_role_requires_confirmation(qapp):
    """A v3 draft saved before role confirmation must not silently become an
    employee complaint: it restores readable, then blocks until confirmed."""
    from views.draft_io import capture_draft

    from helpers import set_parties

    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    set_parties(wizard)
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2024-06-01")
    page.emp_join_date.setText("2023-01-15")
    page.job_title.setText("示例岗位")
    page.monthly_salary.setText("6000")
    page.unpaid_months.setText("2023年12月")
    page.court_name.setText("示例人民法院")
    # role deliberately left unselected
    document = schema.validate_document(capture_draft(wizard, "labor_claim"))
    assert document.factual_flags["labor_role"] is None

    fresh, _ = make_wizard()
    fresh.restart()
    result = apply_draft(fresh, document)
    assert result.resume_page == "labor_claim"
    restored = fresh.labor_claim_page
    assert restored.get_labor_role() is None
    assert not restored.isComplete()
    assert "请先确认您在本案中的身份" in restored.arbitration_hint.text()
    assert not fresh.button(QWizard.NextButton).isEnabled()

    restored._role_buttons[ROLE_EMPLOYEE].setChecked(True)
    assert restored.isComplete()
    assert fresh.button(QWizard.NextButton).isEnabled()


# --------------------------------------------------------------------------- #
# B5-02: separate final / non-final award warnings
# --------------------------------------------------------------------------- #


def test_non_final_warning_cites_article_fifty_only():
    recent = _allow(PROCEDURE_NON_FINAL_AWARD, receipt_date="2026-11-20")
    assert "第五十条" in recent.warning
    assert "第四十七条" not in recent.warning
    assert "期满不起诉" in recent.warning


def test_non_final_warning_stays_calm_within_fifteen_days():
    recent = _allow(PROCEDURE_NON_FINAL_AWARD, receipt_date="2026-11-20")
    assert "超过十五日" not in recent.warning


def test_final_award_employee_warning_cites_forty_seven_and_forty_eight():
    recent = _allow(PROCEDURE_FINAL_AWARD, receipt_date="2026-11-20")
    assert "第四十七条" in recent.warning
    assert "第四十八条" in recent.warning
    # The final award takes effect under its own rule, not upon expiry of the
    # filing period: Article 50 language must never appear.
    assert "第五十条" not in recent.warning
    assert "自作出之日起发生法律效力" in recent.warning


def test_final_award_employee_warning_intensifies_after_fifteen_days():
    late = _allow(PROCEDURE_FINAL_AWARD, receipt_date="2026-01-01")
    assert "超过十五日" in late.warning
    assert "第四十八条" in late.warning
    assert "第五十条" not in late.warning


# --------------------------------------------------------------------------- #
# B5-03: future receipt dates
# --------------------------------------------------------------------------- #


_FUTURE_STATES = (
    (PROCEDURE_NOT_ACCEPTED, {"refusal_ground": GROUND_OTHER_OR_UNSTATED}),
    (PROCEDURE_NON_FINAL_AWARD, {}),
    (PROCEDURE_FINAL_AWARD, {}),
)


@pytest.mark.parametrize("state,extra", _FUTURE_STATES)
def test_future_receipt_date_is_rejected(state, extra):
    blocked = _block(state, receipt_date="2027-01-01", **extra)
    assert "晚于今天" in blocked.reason


@pytest.mark.parametrize("state,extra", _FUTURE_STATES)
def test_receipt_date_on_today_is_accepted(state, extra):
    _allow(state, receipt_date="2026-11-22", **extra)


@pytest.mark.parametrize("state,extra", _FUTURE_STATES)
def test_receipt_date_one_day_ahead_is_rejected(state, extra):
    blocked = _block(state, receipt_date="2026-11-23", **extra)
    assert "晚于今天" in blocked.reason


@pytest.mark.parametrize("state,extra", _FUTURE_STATES)
def test_malformed_receipt_dates_stay_rejected(state, extra):
    _block(state, receipt_date="2026-02-30", **extra)  # impossible calendar date
    _block(state, receipt_date="2026/11/22", **extra)  # wrong format


def test_valid_receipt_date_does_not_bypass_role_confirmation():
    for state, extra in _FUTURE_STATES:
        blocked = _block(state, role=None, receipt_date="2024-06-01", **extra)
        assert "请先确认您在本案中的身份" in blocked.reason


def test_future_date_never_reaches_the_published_complaint(
    qapp, monkeypatch, tmp_path
):
    """Pre-fix, receipt 2027-01-01 flowed into the DOCX as a completed event."""
    desktop = _redirect_desktop(monkeypatch, tmp_path / "home")
    wizard, presenter = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    _select(page, PROCEDURE_NON_FINAL_AWARD)
    page._role_buttons[ROLE_EMPLOYEE].setChecked(True)
    page.arb_commission.setText(COMMISSION)
    page.arb_receipt_date.setText("2027-01-01")

    assert not page.isComplete()
    assert "晚于今天" in page.arbitration_hint.text()
    assert presenter.attempt_finish() == presenter.FINISH_VALIDATION_FAILED
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))
