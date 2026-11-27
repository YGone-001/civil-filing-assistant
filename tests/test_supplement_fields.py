# File: tests/test_supplement_fields.py
# Purpose: Optional user-supplied claims/facts across UI, model, draft and DOCX.
# Encoding: UTF-8

import pytest
from docx import Document
from PySide6.QtWidgets import QPlainTextEdit

from drafts import schema
from helpers import make_wizard, prepare_case
from models.case_model import LoanCaseModel
from presenters.model_builder import build_case_model
from utils.doc_generator import DocumentGenerator
from utils.document_preview import build_complaint_html, build_complaint_text
from views.draft_io import apply_draft, capture_draft


@pytest.mark.parametrize(
    "page_attr,prefix",
    (
        ("loan_claim_page", "loan"),
        ("contract_claim_page", "c"),
        ("property_claim_page", "p"),
        ("labor_claim_page", "l"),
        ("divorce_claim_page", "d"),
        ("rental_claim_page", "r"),
    ),
)
def test_every_claim_page_exposes_supplement_fields(qapp, page_attr, prefix):
    wizard, _ = make_wizard()
    page = getattr(wizard, page_attr)
    assert isinstance(page.extra_claims, QPlainTextEdit)
    assert isinstance(page.extra_facts, QPlainTextEdit)
    assert wizard.field(f"{prefix}_extra_claims") == ""
    assert wizard.field(f"{prefix}_extra_facts") == ""


def test_model_inserts_extra_claims_before_the_cost_claim_and_appends_facts():
    model = LoanCaseModel()
    model.has_repayment = False
    model.extra_claims = [
        "判令被告支付律师费人民币1000元；",
        "   ",
        "判令被告承担本案保全费",
    ]
    model.extra_facts = "另：被告曾书面确认欠款。"

    claims = model.all_claims()
    assert claims[-1] == model.LITIGATION_COST_CLAIM
    assert "判令被告支付律师费人民币1000元；" in claims
    assert "判令被告承担本案保全费；" in claims
    assert claims.index("判令被告承担本案保全费；") < len(claims) - 1

    facts = model.all_facts()
    assert facts.endswith("补充说明：另：被告曾书面确认欠款。")


def test_empty_supplements_leave_generated_content_unchanged():
    model = LoanCaseModel()
    model.has_repayment = False
    model.principal_amount = "1000"
    assert model.all_claims() == model.render_claims()
    assert model.all_facts() == model.render_facts()


def test_model_builder_reads_the_page_supplements(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.contract_claim_page
    page.extra_claims.setPlainText("判令被告支付律师费\n\n判令被告承担保全费")
    page.extra_facts.setPlainText("另：双方曾对欠款进行对账。")

    model = build_case_model(wizard)
    assert model.extra_claims == ["判令被告支付律师费", "判令被告承担保全费"]
    assert model.extra_facts == "另：双方曾对欠款进行对账。"


def test_preview_includes_supplements(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.loan_claim_page.extra_claims.setPlainText("判令被告支付律师费1000元")
    wizard.loan_claim_page.extra_facts.setPlainText("另：被告曾书面承诺还款。")
    model = build_case_model(wizard)

    text = build_complaint_text(model)
    html = build_complaint_html(model)
    assert "律师费1000元" in text
    assert "补充说明：另：被告曾书面承诺还款。" in text
    assert "律师费1000元" in html
    assert "补充说明：另：被告曾书面承诺还款。" in html


def test_exported_complaint_contains_supplements(qapp, tmp_path):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.loan_claim_page.extra_claims.setPlainText("判令被告支付律师费1000元")
    wizard.loan_claim_page.extra_facts.setPlainText("另：被告曾书面承诺还款。")
    model = build_case_model(wizard)

    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(model, str(path))
    text = "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)

    assert "律师费1000元" in text
    assert "补充说明：另：被告曾书面承诺还款。" in text
    assert text.index("律师费1000元") < text.index("本案诉讼费由被告承担")


def test_supplements_survive_draft_capture_and_restore(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.loan_claim_page.extra_claims.setPlainText("判令被告支付律师费1000元")
    wizard.loan_claim_page.extra_facts.setPlainText("另：被告曾书面承诺还款。")

    payload = capture_draft(wizard, resume_page="party")
    document = schema.validate_document(payload)
    assert document.fields["loan_extra_claims"] == "判令被告支付律师费1000元"
    assert document.fields["loan_extra_facts"] == "另：被告曾书面承诺还款。"

    restored, _ = make_wizard()
    apply_draft(restored, document)
    assert restored.loan_claim_page.extra_claims.toPlainText() == (
        "判令被告支付律师费1000元"
    )
    assert restored.loan_claim_page.extra_facts.toPlainText() == (
        "另：被告曾书面承诺还款。"
    )
