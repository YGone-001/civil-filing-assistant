# File: tests/test_rental_case.py
# Purpose: Rental-contract case model, page validation, draft and DOCX output.
# Encoding: UTF-8

from docx import Document

from drafts import schema
from helpers import make_wizard, prepare_case
from presenters.model_builder import build_case_model
from utils.doc_generator import DocumentGenerator
from utils.evidence_library import EvidenceLibrary
from views.draft_io import apply_draft, capture_draft


def _set_status(page, value):
    page.lease_status_combo.setCurrentIndex(page.lease_status_combo.findData(value))
    page._refresh_conditional()


def test_rental_contract_status_is_required_for_completion(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page

    page.lease_status_combo.setCurrentIndex(0)
    page._refresh_conditional()
    assert page.isComplete() is False

    _set_status(page, "active")
    assert page.isComplete() is True


def test_terminated_rental_requires_a_termination_date(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page

    _set_status(page, "terminated")
    page.termination_date.setText("")
    page._refresh_conditional()
    assert page.isComplete() is False
    assert "解除日期" in page.cond_hint.text()

    page.termination_date.setText("2024-04-01")
    page._refresh_conditional()
    assert page.isComplete() is True


def test_rental_date_order_is_blocked(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page

    page.arrears_end.setText("2023-12-31")
    page._refresh_conditional()
    assert page.isComplete() is False
    assert "早于" in page.cond_hint.text()

    page.arrears_end.setText("2024-03-31")
    page._refresh_conditional()
    assert page.isComplete() is True


def test_active_rental_has_no_termination_or_return_claims(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page
    _set_status(page, "active")

    model = build_case_model(wizard)
    claims = model.all_claims()
    facts = model.all_facts()

    assert not any("解除" in claim for claim in claims)
    assert not any("腾退" in claim for claim in claims)
    assert "双方租赁合同仍在履行中。" in facts
    assert "解除" not in facts


def test_request_termination_adds_termination_and_return_claims(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")  # request_termination + not returned
    model = build_case_model(wizard)

    claims = model.all_claims()
    facts = model.all_facts()

    assert claims[0].startswith("判令解除")
    assert any("腾退" in claim for claim in claims)
    assert "原告因被告欠付租金，请求解除双方租赁合同。" in facts
    assert "被告尚未腾退返还房屋。" in facts
    assert "多次催讨" not in facts


def test_terminated_and_returned_rental_states_are_reflected(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page
    _set_status(page, "terminated")
    page.termination_date.setText("2024-04-01")
    page.returned_yes.setChecked(True)
    page._refresh_conditional()

    model = build_case_model(wizard)
    claims = model.all_claims()
    facts = model.all_facts()

    assert not any("解除" in claim for claim in claims)
    assert not any("腾退" in claim for claim in claims)
    assert "双方租赁合同已于2024-04-01解除。" in facts
    assert "被告已腾退并返还房屋。" in facts


def test_rental_draft_round_trip_preserves_status_and_return(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    page = wizard.rental_claim_page
    page.extra_claims.setPlainText("判令被告支付律师费1000元")
    page.extra_facts.setPlainText("另：被告曾书面确认欠租。")

    payload = capture_draft(wizard, resume_page="rental_claim")
    document = schema.validate_document(payload)
    assert document.fields["r_property_address"] == "示例市示例区示例路5号602室"
    assert document.factual_flags["lease_status"] == "request_termination"
    assert document.factual_flags["property_returned"] is False

    restored, _ = make_wizard()
    apply_draft(restored, document)
    restored_page = restored.rental_claim_page
    assert restored_page.get_lease_status() == "request_termination"
    assert restored_page.get_property_returned() is False
    assert restored_page.extra_claims.toPlainText() == "判令被告支付律师费1000元"


def test_rental_evidence_suggestions_are_available():
    items = EvidenceLibrary.get_default_evidence("rental")
    assert len(items) >= 3
    assert any("租赁合同" in name for name, _target in items)
    assert all(name.strip() and target.strip() for name, target in items)


def test_rental_complaint_contains_the_structured_result(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "rental")
    model = build_case_model(wizard)

    path = tmp_path / "rental.docx"
    DocumentGenerator().export_complaint(model, str(path))
    text = "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)

    assert "判令解除原告与被告之间关于示例市示例区示例路5号602室的房屋租赁合同" in text
    assert "判令被告向原告支付欠付租金人民币 9000 元" in text
    assert "判令被告腾退并返还位于示例市示例区示例路5号602室的房屋" in text
    assert "本案诉讼费由被告承担。" in text
