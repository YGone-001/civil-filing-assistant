# File: tests/test_draft_roundtrip.py
# Purpose: Full-state round trip for every case category, through the real wizard.
# Encoding: UTF-8
"""Save -> close -> open -> continue, exercised with the actual PySide6 wizard.

Each case category is captured from a wizard the user would recognise (parties,
facts, amounts, evidence), encrypted, reloaded into a *fresh* wizard, and then
compared field by field. Where a test completes the restored case it also
previews and exports the three Word documents, so a restore that loses data
fails here instead of at the user's desk.

All personal data is fictional and deliberately obviously so.
"""

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QLineEdit, QWizard

from drafts import load_draft, save_draft, schema
from drafts.errors import DraftValidationError
from helpers import (
    CASE_TYPES,
    docx_all_text,
    fill_minimal_case,
    make_wizard,
    navigate_to_export,
    prepare_case,
    select_case,
    set_parties,
)
from presenters.model_builder import build_case_model
from views.draft_io import (
    CLAIM_PAGE_ATTR_BY_CASE,
    INITIAL_FIELD_VALUES,
    INITIAL_FLAG_VALUES,
    PARTY_TEXT_WIDGET_KEYS,
    _capture_flags,
    apply_draft,
    capture_draft,
    has_meaningful_session,
)


def _read(widget):
    return widget.toPlainText() if hasattr(widget, "toPlainText") else widget.text()


def _field_texts(wizard, case_type):
    page = getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])
    return {
        spec.key: _read(getattr(page, spec.widget))
        for spec in schema.TEXT_FIELDS[case_type]
    }


def _save(wizard, path, resume_page="party"):
    document = schema.validate_document(capture_draft(wizard, resume_page))
    save_draft(str(path), document)
    return document


def _restore(path):
    document = load_draft(str(path))
    wizard, presenter = make_wizard()
    wizard.restart()
    result = apply_draft(wizard, document)
    return wizard, presenter, document, result


def _party_snapshot(page):
    return [
        (
            card["name"].text(),
            card["id"].text(),
            card["addr"].text(),
            card["phone"].text(),
            card["is_company"].isChecked(),
            card["credit_code"].text(),
            card["legal_rep"].text(),
        )
        for card in page.plaintiff_widgets + page.defendant_widgets
    ]


def _isolated_desktop(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))
    return home / "Desktop"


# --------------------------------------------------------------------------- #
# Every registered field, every case category
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_all_case_fields_round_trip(qapp, tmp_path, case_type):
    wizard, _ = make_wizard()
    prepare_case(wizard, case_type)
    before = _field_texts(wizard, case_type)
    assert any(value for value in before.values()), "fixture must fill something"

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, document, _ = _restore(tmp_path / "draft.cfdraft")

    assert document.case_type == case_type
    assert _field_texts(restored, case_type) == before


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_optional_blank_fields_stay_blank(qapp, tmp_path, case_type):
    wizard, _ = make_wizard()
    fill_minimal_case(wizard, case_type)
    before = _field_texts(wizard, case_type)
    blanks = [key for key, value in before.items() if value == ""]
    assert blanks, f"{case_type} fixture should leave optional fields empty"

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    after = _field_texts(restored, case_type)
    assert [key for key, value in after.items() if value == ""] == blanks


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_suggestions_round_trip(qapp, tmp_path, case_type):
    wizard, _ = make_wizard()
    prepare_case(wizard, case_type)
    before = wizard.evidence_page.get_evidence_items()
    assert before

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.evidence_page.get_evidence_items() == before
    assert restored.evidence_page.get_case_state() == wizard.evidence_page.get_case_state()


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_completed_case_after_restore_previews_and_exports(
    qapp, monkeypatch, tmp_path, dialog_recorder, case_type
):
    desktop = _isolated_desktop(tmp_path, monkeypatch)
    wizard, presenter = make_wizard()
    prepare_case(wizard, case_type)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, restored_presenter, _, _ = _restore(tmp_path / "draft.cfdraft")

    finish = navigate_to_export(restored)
    restored.export_page.show_preview()
    assert restored.export_page._last_preview_text

    finish.click()
    qapp.processEvents()

    docs = sorted(desktop.rglob("*.docx"))
    assert len(docs) == 3, [doc.name for doc in docs]
    for doc in docs:
        assert doc.stat().st_size > 0
    complaint = next(doc for doc in docs if "民事起诉状" in doc.name)
    assert docx_all_text(complaint).strip()


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_incomplete_case_saves_and_restores(qapp, tmp_path, case_type):
    """Only the parties are entered; nothing else is required to save."""
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    set_parties(wizard)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, document, result = _restore(tmp_path / "draft.cfdraft")

    assert document.case_type == case_type
    assert restored.field("case_type") == case_type
    assert restored.party_page.isComplete()
    assert result.resume_page == "party"
    assert _field_texts(restored, case_type) == _field_texts(wizard, case_type)
    assert restored.evidence_page.get_evidence_items() == []


# --------------------------------------------------------------------------- #
# Parties
# --------------------------------------------------------------------------- #


def test_multiple_plaintiffs_and_defendants_round_trip(qapp, tmp_path):
    plaintiffs = [
        {"name": "原告甲（测试）", "id_number": "示例-甲", "address": "地址甲", "phone": "13800000001"},
        {"name": "原告乙（测试）", "id_number": "示例-乙", "address": "地址乙", "phone": "13800000002"},
        {"name": "原告丙（测试）", "id_number": "示例-丙", "address": "地址丙", "phone": "13800000003"},
    ]
    defendants = [
        {"name": "被告丁（测试）", "id_number": "示例-丁", "address": "地址丁", "phone": "13900000001"},
        {"name": "被告戊（测试）", "id_number": "示例-戊", "address": "地址戊", "phone": "13900000002"},
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan", plaintiffs=plaintiffs, defendants=defendants)
    before = _party_snapshot(wizard.party_page)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert len(restored.party_page.plaintiff_widgets) == 3
    assert len(restored.party_page.defendant_widgets) == 2
    assert _party_snapshot(restored.party_page) == before


def test_company_party_fields_round_trip(qapp, tmp_path):
    plaintiffs = [
        {
            "name": "示例科技（测试）有限公司",
            "is_company": True,
            "credit_code": "91310000MA1FL0TEST",
            "legal_rep": "赵六",
            "address": "示例市示例区示例路9号",
            "phone": "021-00000000",
        }
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract", plaintiffs=plaintiffs)
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    card = restored.party_page.plaintiff_widgets[0]
    assert card["is_company"].isChecked() is True
    assert card["credit_code"].text() == "91310000MA1FL0TEST"
    assert card["legal_rep"].text() == "赵六"
    # The company fields really are the visible ones after restore.
    assert not card["credit_code"].isHidden()
    assert card["id"].isHidden()


def test_mixed_individual_and_company_parties_round_trip(qapp, tmp_path):
    plaintiffs = [
        {"name": "原告甲（测试）", "id_number": "示例-甲", "address": "地址甲", "phone": "13800000001"},
        {
            "name": "示例物业（测试）公司",
            "is_company": True,
            "credit_code": "91310000MA1FL0ABCD",
            "legal_rep": "钱七",
            "address": "地址乙",
            "phone": "021-11111111",
        },
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "property", plaintiffs=plaintiffs)
    before = _party_snapshot(wizard.party_page)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert _party_snapshot(restored.party_page) == before
    assert restored.party_page.plaintiff_widgets[1]["is_company"].isChecked()


def test_partially_completed_company_card_round_trip(qapp, tmp_path):
    """A company card with a missing credit code and legal representative."""
    plaintiffs = [
        {
            "name": "示例劳务（测试）公司",
            "is_company": True,
            "credit_code": "",
            "legal_rep": "",
            "address": "示例市示例路1号",
            "phone": "",
        }
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor", plaintiffs=plaintiffs)
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    card = restored.party_page.plaintiff_widgets[0]
    assert card["is_company"].isChecked() is True
    assert card["name"].text() == "示例劳务（测试）公司"
    assert card["credit_code"].text() == ""
    assert card["legal_rep"].text() == ""
    assert not card["credit_code"].isHidden()


def test_blank_extra_party_card_is_preserved(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.party_page.add_party_ui(0)  # a deliberately empty third card
    assert wizard.party_page.plaintiff_widgets[-1]["name"].text() == ""

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    cards = restored.party_page.plaintiff_widgets
    assert len(cards) == 2
    assert cards[1]["name"].text() == ""
    assert restored.party_page.validatePage() is False


def test_deleted_middle_party_is_not_resurrected(qapp, tmp_path):
    plaintiffs = [
        {"name": "原告甲（测试）", "id_number": "示例-甲"},
        {"name": "原告乙（测试）", "id_number": "示例-乙"},
        {"name": "原告丙（测试）", "id_number": "示例-丙"},
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan", plaintiffs=plaintiffs)
    wizard.party_page.remove_party_ui(0, 1)  # delete the middle card
    remaining = [card["name"].text() for card in wizard.party_page.plaintiff_widgets]

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert [card["name"].text() for card in restored.party_page.plaintiff_widgets] == remaining
    # Card numbering is contiguous again, exactly as on the live page.
    assert [card["group"].title() for card in restored.party_page.plaintiff_widgets] == [
        "原告1",
        "原告2",
    ]


def test_party_tab_order_and_numbering_are_rebuilt(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.party_page.add_party_ui(1)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    page = restored.party_page
    assert [card["group"].title() for card in page.defendant_widgets] == ["被告1", "被告2"]
    assert page.plaintiff_widgets[0]["name"].accessibleName() == "原告1姓名/名称"
    assert page.defendant_widgets[1]["name"].accessibleName() == "被告2姓名/名称"


def test_restored_party_page_is_not_reinitialised(qapp, tmp_path):
    """A later visit must not delete the restored cards."""
    plaintiffs = [
        {"name": "原告甲（测试）", "id_number": "示例-甲"},
        {"name": "原告乙（测试）", "id_number": "示例-乙"},
    ]
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan", plaintiffs=plaintiffs)
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    restored.setCurrentId(restored.PAGE_PARTY)
    qapp.processEvents()

    assert len(restored.party_page.plaintiff_widgets) == 2
    assert restored.party_page.plaintiff_widgets[1]["name"].text() == "原告乙（测试）"


# --------------------------------------------------------------------------- #
# Tri-state confirmations
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("iou", [True, False, None])
def test_loan_iou_tri_state_survives_round_trip(qapp, tmp_path, iou):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan", confirm_flags=False)
    page = wizard.loan_claim_page
    if iou is True:
        page.iou_yes.setChecked(True)
    elif iou is False:
        page.iou_no.setChecked(True)
    else:
        page.iou_unknown.setChecked(True)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.loan_claim_page.get_has_iou() is iou
    assert build_case_model(restored).has_iou is iou


@pytest.mark.parametrize("delivered", [True, False, None])
@pytest.mark.parametrize("signed", [True, False, None])
def test_contract_tri_states_survive_round_trip(qapp, tmp_path, delivered, signed):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract", confirm_flags=False)
    page = wizard.contract_claim_page
    for group_value, yes, no, unknown in (
        (delivered, page.del_yes, page.del_no, page.del_unknown),
        (signed, page.sign_yes, page.sign_no, page.sign_unknown),
    ):
        if group_value is True:
            yes.setChecked(True)
        elif group_value is False:
            no.setChecked(True)
        else:
            unknown.setChecked(True)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.contract_claim_page.get_flags() == {
        "is_delivered": delivered,
        "is_signed": signed,
    }


def test_unconfirmed_loan_fact_is_not_rendered_after_restore(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan", confirm_flags=False)
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    facts = build_case_model(restored).render_facts()
    assert "借条" not in facts


def test_labor_binary_contract_flag_round_trip(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    wizard.labor_claim_page.no_contract_yes.setChecked(True)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.labor_claim_page.get_has_no_contract() is True
    assert build_case_model(restored).is_no_contract is True


# --------------------------------------------------------------------------- #
# Amounts and calculation provenance
# --------------------------------------------------------------------------- #


def test_property_manual_total_is_preserved_exactly(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    wizard.property_claim_page.total_input.setText("2765.00")

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.property_claim_page.total_input.text() == "2765.00"
    model = build_case_model(restored)
    assert model.total_principal == "2765.00"
    assert "2765.00" in model.render_claims()[0]


def test_property_derived_estimate_is_recomputed(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.property_claim_page.calc_label.text() == wizard.property_claim_page.calc_label.text()
    assert build_case_model(restored)._calc_total() == build_case_model(wizard)._calc_total()


def test_contract_calculator_provenance_is_not_restored(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.contract_claim_page
    page.overdue_end.setText("2023-06-30")
    page.calc_penalty_by_lpr_multiple()
    assert page.get_penalty_calc_basis() == {"method": "lpr_multiple", "cutoff": "2023-06-30"}
    amount = page.penalty_amount.text()

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    restored_page = restored.contract_claim_page
    assert restored_page.penalty_amount.text() == amount
    assert restored_page.overdue_start.text() == "2023-03-01"
    assert restored_page.overdue_end.text() == "2023-06-30"
    assert restored_page.lpr_value.text() == "3.45"
    assert restored_page.lpr_multiple.text() == "4"
    # Fail-closed: the restored amount was never recomputed, so no verified
    # calculation basis may be claimed for it.
    assert restored_page.get_penalty_calc_basis() is None

    model = build_case_model(restored)
    assert model.penalty_calc_method == ""
    assert model.penalty_calc_cutoff == ""
    assert model.penalty_calc_standard == ""
    claim = model.render_claims()[1]
    assert "LPR" not in claim
    assert "日万分之五" not in claim
    assert "暂计至" not in claim
    assert amount in claim


def test_contract_manual_penalty_stays_manual(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    wizard.contract_claim_page.penalty_amount.setText("1234.56")

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.contract_claim_page.get_penalty_calc_basis() is None
    assert build_case_model(restored).render_claims()[1] == (
        "判令被告向原告支付违约金（或逾期付款利息）人民币 1234.56 元；"
    )


def test_contract_provenance_can_be_regained_by_recalculating(qapp, tmp_path):
    """The user can deliberately re-run the calculator to restore provenance."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    wizard.contract_claim_page.overdue_end.setText("2023-06-30")
    wizard.contract_claim_page.calc_penalty_by_lpr_multiple()

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")
    restored.contract_claim_page.calc_penalty_by_lpr_multiple()

    model = build_case_model(restored)
    assert model.penalty_calc_method == "lpr_multiple"
    assert model.penalty_calc_standard == "3.45%×4"
    assert "暂计至 2023-06-30" in model.render_claims()[1]


# --------------------------------------------------------------------------- #
# Evidence states
# --------------------------------------------------------------------------- #


def test_explicitly_cleared_evidence_stays_empty_after_restore(qapp, tmp_path, dialog_recorder):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    page = wizard.evidence_page
    page.table.selectAll()
    page.remove_selected_rows()
    assert page.table.rowCount() == 0

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, document, _ = _restore(tmp_path / "draft.cfdraft")

    assert document.evidence_state == "USER_EXPLICITLY_CLEARED"
    assert document.evidence_rows == ()
    assert restored.evidence_page.table.rowCount() == 0
    restored.setCurrentId(restored.PAGE_EVIDENCE)
    assert restored.evidence_page.table.rowCount() == 0
    assert restored.evidence_page.get_evidence_items() == []


def test_untouched_evidence_page_stays_uninitialised(qapp, tmp_path):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    set_parties(wizard)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, document, _ = _restore(tmp_path / "draft.cfdraft")

    assert document.evidence_state == "NOT_INITIALIZED"
    assert document.evidence_rows == ()
    assert restored.evidence_page.table.rowCount() == 0
    # Visiting the page still loads the category suggestions, as on a fresh run.
    restored.setCurrentId(restored.PAGE_EVIDENCE)
    assert restored.evidence_page.table.rowCount() > 0


def test_user_rows_and_suggestion_markers_round_trip(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    page = wizard.evidence_page
    page.table.item(0, 0).setText("修改后的借条（测试）")
    page.add_row("用户补充证据（测试）", "证明目的（测试）", auto_edit=False)
    before = page._collect_rows()

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    assert restored.evidence_page._collect_rows() == before
    assert restored.evidence_page._suggested_count == page._suggested_count
    assert restored.evidence_page.get_case_state() == page.USER_MODIFIED


def test_evidence_from_another_category_never_leaks(qapp, tmp_path):
    """Switch the case type without visiting evidence again, then save."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    assert "借条/借款协议" in [name for name, _ in wizard.evidence_page.get_evidence_items()]

    select_case(wizard, "divorce")
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, document, _ = _restore(tmp_path / "draft.cfdraft")

    assert document.case_type == "divorce"
    assert document.evidence_state == "NOT_INITIALIZED"
    names = [name for name, _ in restored.evidence_page.get_evidence_items()]
    assert not any("借条" in name for name in names)


# --------------------------------------------------------------------------- #
# Resume behaviour
# --------------------------------------------------------------------------- #


def test_resume_page_is_honoured_when_safe(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    wizard.setCurrentId(wizard.PAGE_CONTRACT_CLAIM)

    _save(wizard, tmp_path / "draft.cfdraft", resume_page="contract_claim")
    restored, _, _, result = _restore(tmp_path / "draft.cfdraft")

    assert result.resume_page == "contract_claim"
    assert restored.currentId() == restored.PAGE_CONTRACT_CLAIM
    assert result.note == ""


def test_resume_falls_back_when_parties_are_incomplete(qapp, tmp_path):
    wizard, _ = make_wizard()
    select_case(wizard, "labor")
    set_parties(wizard)
    # Blank the defendant name: the case can no longer stand on the claim page.
    wizard.party_page.defendant_widgets[0]["name"].setText("")

    _save(wizard, tmp_path / "draft.cfdraft", resume_page="labor_claim")
    restored, _, _, result = _restore(tmp_path / "draft.cfdraft")

    assert result.resume_page == "party"
    assert result.note
    assert restored.currentId() == restored.PAGE_PARTY


def test_resume_falls_back_when_page_and_case_type_disagree(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "divorce")

    _save(wizard, tmp_path / "draft.cfdraft", resume_page="loan_claim")
    restored, _, _, result = _restore(tmp_path / "draft.cfdraft")

    assert result.resume_page == "party"
    assert restored.currentId() == restored.PAGE_PARTY
    assert result.note


def test_resume_to_export_requires_a_complete_party_list(qapp, tmp_path):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)
    wizard.party_page.plaintiff_widgets[0]["name"].setText("")

    _save(wizard, tmp_path / "draft.cfdraft", resume_page="export")
    restored, _, _, result = _restore(tmp_path / "draft.cfdraft")

    assert result.resume_page == "party"


def test_restored_incomplete_case_still_blocks_navigation(qapp, tmp_path, dialog_recorder):
    """Restoration must never silently mark an incomplete case as validated."""
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")

    restored.setCurrentId(restored.PAGE_LOAN_CLAIM)
    qapp.processEvents()
    next_button = restored.button(QWizard.NextButton)
    assert not next_button.isEnabled()

    next_button.click()  # a disabled click must be rejected
    qapp.processEvents()
    assert restored.currentId() == restored.PAGE_LOAN_CLAIM


def test_resume_to_export_requires_a_complete_claim_page(qapp, tmp_path):
    """A draft saved on the export page but missing required facts opens earlier."""
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    set_parties(wizard)  # parties only: every required fact is still blank

    _save(wizard, tmp_path / "draft.cfdraft", resume_page="export")
    restored, _, _, result = _restore(tmp_path / "draft.cfdraft")

    assert result.resume_page == "contract_claim"
    assert restored.currentId() == restored.PAGE_CONTRACT_CLAIM
    assert result.note


# --------------------------------------------------------------------------- #
# Isolation between categories
# --------------------------------------------------------------------------- #


def test_no_cross_case_data_leakage(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")
    fresh, _ = make_wizard()

    assert restored.field("case_type") == "property"
    for other in CASE_TYPES:
        if other == "property":
            continue
        restored_page = getattr(restored, CLAIM_PAGE_ATTR_BY_CASE[other])
        fresh_page = getattr(fresh, CLAIM_PAGE_ATTR_BY_CASE[other])
        for spec in schema.TEXT_FIELDS[other]:
            assert _read(getattr(restored_page, spec.widget)) == _read(
                getattr(fresh_page, spec.widget)
            ), (other, spec.key)


def test_restored_wizard_matches_a_directly_filled_wizard(qapp, tmp_path):
    """The restored model must render identically to the original one."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "divorce")
    original = build_case_model(wizard)

    _save(wizard, tmp_path / "draft.cfdraft")
    restored, _, _, _ = _restore(tmp_path / "draft.cfdraft")
    rebuilt = build_case_model(restored)

    assert rebuilt.render_claims() == original.render_claims()
    assert rebuilt.render_facts() == original.render_facts()
    assert [(ev.name, ev.target) for ev in rebuilt.evidences] == [
        (ev.name, ev.target) for ev in original.evidences
    ]


def test_draft_opens_in_a_separate_process(qapp, tmp_path):
    """A saved draft is readable from a brand-new Python process.

    This is the closest automated approximation of "close the application,
    reopen it, open the draft": no wizard, no Qt, no in-process state - only
    the file and the current Windows user's key.
    """
    import json
    import subprocess
    import sys

    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    _save(wizard, tmp_path / "draft.cfdraft")

    script = (
        "import json\n"
        "from drafts import load_draft\n"
        f"document = load_draft({str(tmp_path / 'draft.cfdraft')!r})\n"
        # ASCII-only output: the child's stdout is a pipe whose encoding follows
        # the host console code page, so raw CJK text would raise
        # UnicodeEncodeError on an English-locale runner.
        "print(json.dumps({'case_type': document.case_type,"
        " 'loan_date': document.fields['loan_date'],"
        " 'principal': document.fields['principal'],"
        " 'parties': document.party_count()}, ensure_ascii=True))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {
        "case_type": "loan",
        "loan_date": "2023年1月1日",
        "principal": "50000",
        "parties": 2,
    }


def test_captured_document_validates_without_a_file(qapp):
    """The capture path alone must already produce a schema-valid document."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    document = schema.validate_document(capture_draft(wizard))
    assert document.case_type == "labor"
    assert document.fields["l_job_title"] == "测试工程师"


def test_capture_rejects_an_unsupported_case_type(qapp, monkeypatch):
    wizard, _ = make_wizard()
    original_field = wizard.field

    def _fake_field(name):
        if name == "case_type":
            return "traffic"
        return original_field(name)

    monkeypatch.setattr(wizard, "field", _fake_field)
    with pytest.raises(ValueError):
        capture_draft(wizard)


# --------------------------------------------------------------------------- #
# C-08 — the meaningful-session contract and its initial-value metadata
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_registered_field_initial_values_match_the_real_pages(qapp, case_type):
    """The "initial value" table must describe what the pages really start with."""
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    page = getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])
    for spec in schema.TEXT_FIELDS[case_type]:
        expected = INITIAL_FIELD_VALUES.get(spec.key, "")
        assert _read(getattr(page, spec.widget)) == expected, spec.key


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_confirmation_initial_values_match_the_real_pages(qapp, case_type):
    """Every confirmation starts at its declared initial state, including False."""
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    page = getattr(wizard, CLAIM_PAGE_ATTR_BY_CASE[case_type])
    for name, value in _capture_flags(page, case_type).items():
        assert value == INITIAL_FLAG_VALUES[name], name


def test_initial_value_table_covers_every_persisted_confirmation():
    declared = set(schema.TRI_STATE_FLAGS) | set(schema.BINARY_FLAGS)
    assert set(INITIAL_FLAG_VALUES) == declared
    # Only the two contract calculator inputs start non-empty.
    assert set(INITIAL_FIELD_VALUES) == {"c_lpr_value", "c_lpr_multiple"}


def test_party_text_keys_cover_every_text_widget_on_a_card(qapp):
    """A new party text field must not slip past the detection contract."""
    wizard, _ = make_wizard()
    wizard.party_page.initializePage()
    card = wizard.party_page.plaintiff_widgets[0]
    text_widgets = {key for key, value in card.items() if isinstance(value, QLineEdit)}
    assert text_widgets == set(PARTY_TEXT_WIDGET_KEYS)


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_pristine_wizard_has_no_meaningful_session(qapp, case_type):
    """A brand-new wizard (even after picking a category) holds no user data."""
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    assert has_meaningful_session(wizard) is False


def test_session_detection_is_observational(qapp):
    """Inspecting the session must not initialize, load or mutate anything."""
    wizard, _ = make_wizard()
    assert wizard.party_page.plaintiff_widgets == []
    assert wizard.party_page.is_initialized is False
    assert wizard.evidence_page._loaded_case_type is None

    assert has_meaningful_session(wizard) is False

    assert wizard.party_page.plaintiff_widgets == []
    assert wizard.party_page.defendant_widgets == []
    assert wizard.party_page.is_initialized is False
    assert wizard.evidence_page._loaded_case_type is None
    assert wizard.evidence_page.table.rowCount() == 0


def test_detection_reports_true_for_a_populated_case(qapp):
    """Sanity check the other direction: a filled case is meaningful."""
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    assert has_meaningful_session(wizard) is True


def test_defaults_only_contract_session_is_not_meaningful(qapp):
    """LPR 3.45 and multiplier 4 alone must not look like user input."""
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    assert wizard.contract_claim_page.lpr_value.text() == "3.45"
    assert wizard.contract_claim_page.lpr_multiple.text() == "4"
    assert has_meaningful_session(wizard) is False
