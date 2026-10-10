# File: tests/test_factual_confirmation.py
# Purpose: Regression tests for explicit user confirmation of generated case
#          facts (delivery / receipt / IOU / property relationship).
# Encoding: UTF-8
"""Three-state factual confirmation: UNKNOWN / CONFIRMED_TRUE / CONFIRMED_FALSE.

A default UI state is never evidence of user confirmation. Every test here drives
the *real* QWizard, the shared ``build_case_model`` pipeline and the real DOCX
export — no mocked case model — so an untouched control can never fabricate a
fact in the generated complaint.
"""

import os

import pytest

from helpers import (
    docx_all_text,
    fill_case_facts,
    make_wizard,
    navigate_to_export,
    prepare_case,
    select_case,
    set_parties,
)
from presenters.model_builder import build_case_model


def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))
    return home / "Desktop"


def _export(presenter, desktop):
    presenter.on_wizard_accepted()
    return sorted(desktop.rglob("*.docx"))


def _complaint(docs):
    for doc in docs:
        if "民事起诉状" in doc.name:
            return docx_all_text(doc)
    raise AssertionError(f"no complaint in {[d.name for d in docs]}")


def _preview_text(wizard, dialog_recorder):
    dialog_recorder.clear()
    wizard.export_page.show_preview()
    infos = [e for e in dialog_recorder if e["kind"] == "information"]
    assert infos, "no preview dialog shown"
    return " ".join(str(a) for a in infos[-1]["args"])


def _contract_wizard(tmp_path, monkeypatch, delivery=None, receipt=None, with_evidence=False):
    """Contract case with explicit delivery/receipt states.

    ``None`` leaves the control untouched (UNKNOWN); ``True``/``False`` select the
    explicit positive/negative option.
    """
    desktop = _home(tmp_path, monkeypatch)
    wizard, presenter = make_wizard()
    select_case(wizard, "contract")
    set_parties(wizard)
    fill_case_facts(wizard, "contract", confirm_flags=False)
    page = wizard.contract_claim_page
    if delivery is True:
        page.del_yes.setChecked(True)
    elif delivery is False:
        page.del_no.setChecked(True)
    if receipt is True:
        page.sign_yes.setChecked(True)
    elif receipt is False:
        page.sign_no.setChecked(True)
    if with_evidence:
        wizard.evidence_page.initializePage()
    return wizard, presenter, desktop


def _loan_wizard(tmp_path, monkeypatch, iou=None, with_evidence=False):
    desktop = _home(tmp_path, monkeypatch)
    wizard, presenter = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)
    fill_case_facts(wizard, "loan", confirm_flags=False)
    if iou is True:
        wizard.loan_claim_page.iou_yes.setChecked(True)
    elif iou is False:
        wizard.loan_claim_page.iou_no.setChecked(True)
    if with_evidence:
        wizard.evidence_page.initializePage()
    return wizard, presenter, desktop


# --- C1: sales-contract delivery confirmation ------------------------------


def test_c1_t01_fresh_wizard_delivery_is_unknown(qapp):
    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    assert page.del_unknown.isChecked()
    assert page.get_flags()["is_delivered"] is None


def test_c1_t02_untouched_delivery_makes_no_delivery_statement(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=None)
    docs = _export(presenter, desktop)
    assert len(docs) == 3
    text = _complaint(docs)
    for phrase in ("原告已于", "尚未完成交货", "已交付货物"):
        assert phrase not in text, f"untouched delivery fabricated {phrase!r}"
    assert "尚未确认" in text  # neutral review note instead


def test_c1_t03_confirmed_delivery_states_completion(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True)
    text = _complaint(_export(presenter, desktop))
    assert "原告已于2023年2月1日完成交货。" in text
    assert "尚未完成交货" not in text


def test_c1_t04_confirmed_not_delivered_states_that(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=False)
    text = _complaint(_export(presenter, desktop))
    assert "原告尚未完成交货。" in text
    assert "原告已于" not in text


def test_c1_t05_delivery_date_alone_does_not_confirm(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=None)
    assert wizard.contract_claim_page.delivery_date.text() == "2023年2月1日"
    assert build_case_model(wizard).is_delivered is None
    text = _complaint(_export(presenter, desktop))
    assert "原告已于" not in text and "尚未完成交货" not in text


def test_c1_t06_switching_delivery_state_updates_model(qapp):
    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    assert page.get_flags()["is_delivered"] is None
    page.del_yes.setChecked(True)
    assert page.get_flags()["is_delivered"] is True
    page.del_no.setChecked(True)
    assert page.get_flags()["is_delivered"] is False
    page.del_unknown.setChecked(True)
    assert page.get_flags()["is_delivered"] is None


def test_c1_t07_exported_complaint_preserves_confirmed_delivery(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=None)
    assert build_case_model(wizard).is_delivered is True
    text = _complaint(_export(presenter, desktop))
    assert "原告已于2023年2月1日完成交货。" in text


# --- C2: sales-contract receipt confirmation -------------------------------


def test_c2_t01_fresh_wizard_receipt_is_unknown(qapp):
    wizard, _ = make_wizard()
    page = wizard.contract_claim_page
    assert page.sign_unknown.isChecked()
    assert page.get_flags()["is_signed"] is None


def test_c2_t02_untouched_receipt_makes_no_signature_statement(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=None)
    text = _complaint(_export(presenter, desktop))
    assert "被告已签收" not in text
    assert "被告尚未签收" not in text


def test_c2_t03_confirmed_receipt_states_signature(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=True)
    text = _complaint(_export(presenter, desktop))
    assert "被告已签收。" in text


def test_c2_t04_confirmed_non_receipt_is_neutral(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=False)
    text = _complaint(_export(presenter, desktop))
    assert "被告尚未签收。" in text
    for phrase in ("无理拒绝", "拒签"):
        assert phrase not in text, f"non-receipt fabricated {phrase!r}"


def test_c2_t05_delivery_date_does_not_establish_receipt(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=None)
    assert wizard.contract_claim_page.delivery_date.text() == "2023年2月1日"
    assert build_case_model(wizard).is_signed is None
    assert "被告已签收" not in _complaint(_export(presenter, desktop))


def test_c2_t06_unconfirmed_receipt_not_coerced_to_false(qapp, monkeypatch, tmp_path):
    wizard, _presenter, _desktop = _contract_wizard(tmp_path, monkeypatch, delivery=None, receipt=None)
    model = build_case_model(wizard)
    assert model.is_signed is None
    assert model.is_delivered is None


def test_c2_t07_contradictory_states_are_detected_and_block_export(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=False, receipt=True)
    model = build_case_model(wizard)
    assert model.delivery_receipt_conflict() is True

    result = presenter.attempt_finish()
    assert result == presenter.FINISH_VALIDATION_FAILED
    assert any(e["kind"] == "warning" for e in dialog_recorder)
    assert not list(desktop.rglob("*.docx")), "contradictory input must not publish a document"


def test_c2_t07b_finish_button_blocks_contradiction_then_retry_succeeds(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=False, receipt=True)
    finish = navigate_to_export(wizard)
    accepted = []
    wizard.accepted.connect(lambda: accepted.append(True))
    wizard.show()
    qapp.processEvents()

    finish.click()
    qapp.processEvents()
    assert not accepted
    assert wizard.result() == 0
    assert wizard.isVisible()
    assert not list(desktop.rglob("*.docx"))

    # Correct the contradiction through the real control, then retry.
    wizard.contract_claim_page.del_yes.setChecked(True)
    finish.click()
    qapp.processEvents()
    assert accepted
    docs = sorted(desktop.rglob("*.docx"))
    assert len(docs) == 3, [d.name for d in docs]


def test_c2_t08_preview_agrees_with_exported_complaint(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=True, receipt=True)
    model = build_case_model(wizard)
    preview_facts = model.render_facts()
    preview = _preview_text(wizard, dialog_recorder)
    assert preview_facts in preview
    text = _complaint(_export(presenter, desktop))
    assert preview_facts in text


# --- C3: private-lending IOU confirmation ----------------------------------


def test_c3_t01_fresh_wizard_iou_is_unknown(qapp):
    wizard, _ = make_wizard()
    page = wizard.loan_claim_page
    assert page.iou_unknown.isChecked()
    assert page.get_has_iou() is None


def test_c3_t02_untouched_iou_makes_no_iou_statement(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=None)
    text = _complaint(_export(presenter, desktop))
    assert "借条" not in text, "untouched IOU control fabricated an IOU fact"
    assert "50000" in text  # other supplied facts survive


def test_c3_t03_confirmed_iou_states_existence(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=True)
    text = _complaint(_export(presenter, desktop))
    assert "被告出具了借条。" in text


def test_c3_t04_confirmed_no_iou_states_absence(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=False)
    text = _complaint(_export(presenter, desktop))
    assert "被告未出具借条。" in text
    assert "出具了借条。" not in text


def test_c3_t05_unknown_iou_survives_model_builder(qapp, monkeypatch, tmp_path):
    wizard, _presenter, _desktop = _loan_wizard(tmp_path, monkeypatch, iou=None)
    assert build_case_model(wizard).has_iou is None


def test_c3_t06_preview_omits_unconfirmed_iou(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, _presenter, _desktop = _loan_wizard(tmp_path, monkeypatch, iou=None)
    preview = _preview_text(wizard, dialog_recorder)
    assert "借条" not in preview


def test_c3_t07_docx_omits_unconfirmed_iou(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=None)
    text = _complaint(_export(presenter, desktop))
    assert "借条" not in text


def test_c3_t08_iou_evidence_suggestion_is_distinct_from_confirmed_fact(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=None, with_evidence=True)
    # The evidence list still *suggests* an IOU as a possible document ...
    suggested = [name for name, _target in wizard.evidence_page.get_evidence_items()]
    assert any("借条" in name for name in suggested), suggested
    # ... but the complaint asserts no IOU fact, because none was confirmed.
    text = _complaint(_export(presenter, desktop))
    assert "借条" not in text


# --- C4: property ownership / occupancy accuracy ---------------------------


def _property_complaint(tmp_path, monkeypatch, mutate=None):
    desktop = _home(tmp_path, monkeypatch)
    wizard, presenter = make_wizard()
    prepare_case(wizard, "property")
    if mutate is not None:
        mutate(wizard)
    presenter.on_wizard_accepted()
    return _complaint(sorted(desktop.rglob("*.docx")))


def test_c4_t01_address_alone_does_not_establish_ownership(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "的业主。" not in text
    assert "业主或使用人" not in text
    assert "人工核对" in text


def test_c4_t02_address_alone_does_not_establish_occupancy(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "的业主或使用人" not in text
    assert "使用人。" not in text


def test_c4_t03_claimed_relationship_is_flagged_for_review(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "原告主张" in text
    assert "需结合物业服务合同、产权资料及其他证据人工核对" in text


def test_c4_t04_entered_address_is_preserved(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "示例小区3栋1201室" in text


def test_c4_t05_fee_calculation_unchanged(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "7761.60" in text
    assert "115.5" in text
    assert "2.8" in text


def test_c4_t06_partial_period_warning_unchanged(qapp, monkeypatch, tmp_path, dialog_recorder):
    def _partial(wizard):
        wizard.property_claim_page.period_start.setText("2024-01-15")
        wizard.property_claim_page.period_end.setText("2024-12-31")

    text = _property_complaint(tmp_path, monkeypatch, mutate=_partial)
    assert "按整月计费估算" in text
    assert "以双方核对及缴费记录为准" in text


def test_c4_t07_neutral_wording_reaches_the_docx(qapp, monkeypatch, tmp_path, dialog_recorder):
    text = _property_complaint(tmp_path, monkeypatch)
    assert "物业费负担存在相关权利义务关系" in text
    assert "物业服务企业" not in text
    assert "签署了《物业服务合同》" not in text


# --- Integration: unknown survives the whole pipeline ------------------------


def test_pipeline_unknown_state_is_preserved_end_to_end(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=None, receipt=None)

    flags = wizard.contract_claim_page.get_flags()
    assert flags["is_delivered"] is None and flags["is_signed"] is None

    model = build_case_model(wizard)
    assert model.is_delivered is None and model.is_signed is None

    facts = model.render_facts()
    assert "原告已于" not in facts and "被告已签收" not in facts and "被告尚未签收" not in facts

    preview = _preview_text(wizard, dialog_recorder)
    assert "原告已于" not in preview and "被告已签收" not in preview

    text = _complaint(_export(presenter, desktop))
    assert "原告已于" not in text and "被告已签收" not in text and "被告尚未签收" not in text


@pytest.mark.parametrize(
    "delivery,receipt,expected,forbidden",
    [
        (None, None, ["尚未确认"], ["原告已于", "尚未完成交货", "被告已签收", "被告尚未签收"]),
        (True, None, ["原告已于"], ["尚未完成交货", "被告已签收", "被告尚未签收"]),
        (True, True, ["原告已于", "被告已签收"], ["尚未完成交货", "被告尚未签收"]),
        (True, False, ["原告已于", "被告尚未签收"], ["尚未完成交货", "被告已签收"]),
        (False, None, ["尚未完成交货"], ["原告已于", "被告已签收", "被告尚未签收"]),
        (False, False, ["尚未完成交货", "被告尚未签收"], ["原告已于", "被告已签收"]),
    ],
)
def test_contract_delivery_receipt_docx_matrix(qapp, monkeypatch, tmp_path, dialog_recorder,
                                               delivery, receipt, expected, forbidden):
    """DOCX output for every non-contradictory delivery/receipt combination."""
    wizard, presenter, desktop = _contract_wizard(tmp_path, monkeypatch, delivery=delivery, receipt=receipt)
    docs = _export(presenter, desktop)
    assert len(docs) == 3
    text = _complaint(docs)
    for phrase in expected:
        assert phrase in text, f"missing {phrase!r} for delivery={delivery} receipt={receipt}"
    for phrase in forbidden:
        assert phrase not in text, f"unexpected {phrase!r} for delivery={delivery} receipt={receipt}"


@pytest.mark.parametrize(
    "iou,expected,forbidden",
    [
        (None, [], ["借条"]),
        (True, ["被告出具了借条。"], ["被告未出具借条"]),
        (False, ["被告未出具借条。"], ["被告出具了借条"]),
    ],
)
def test_loan_iou_docx_matrix(qapp, monkeypatch, tmp_path, dialog_recorder, iou, expected, forbidden):
    wizard, presenter, desktop = _loan_wizard(tmp_path, monkeypatch, iou=iou)
    docs = _export(presenter, desktop)
    assert len(docs) == 3
    text = _complaint(docs)
    for phrase in expected:
        assert phrase in text, f"missing {phrase!r} for iou={iou}"
    for phrase in forbidden:
        assert phrase not in text, f"unexpected {phrase!r} for iou={iou}"
