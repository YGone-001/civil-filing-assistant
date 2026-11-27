# File: tests/test_document_preview.py
# Purpose: Document-style complaint preview (plain text, HTML, escaping).
# Encoding: UTF-8

from helpers import make_wizard, prepare_case
from presenters.model_builder import build_case_model
from utils.document_preview import build_complaint_html, build_complaint_text
from views.pages.export import _PreviewDialog


def test_plain_text_preview_contains_the_complaint_sections(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    model = build_case_model(wizard)

    text = build_complaint_text(model)
    assert "民 事 起 诉 状" in text
    assert "原告" in text and "被告" in text
    assert "诉讼请求：" in text
    assert "事实与理由：" in text
    assert "偿还借款本金" in text
    assert "此致" in text
    assert "具状人：" in text


def test_html_preview_contains_the_same_key_content(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "contract")
    model = build_case_model(wizard)

    html = build_complaint_html(model)
    assert "<html>" in html
    assert "民 事 起 诉 状" in html
    assert "诉讼请求：" in html
    assert "事实与理由：" in html
    assert "货款本金" in html


def test_html_preview_escapes_user_text(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.party_page.plaintiff_widgets[0]["name"].setText("<script>alert(1)</script>")
    model = build_case_model(wizard)

    html = build_complaint_html(model)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_preview_counts_the_actual_defendants(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    wizard.party_page.add_party_ui(1)
    wizard.party_page.defendant_widgets[1]["name"].setText("被告乙（测试）")
    model = build_case_model(wizard)

    text = build_complaint_text(model)
    assert "附：本状副本2份。" in text


def test_preview_dialog_accepts_html_and_text(qapp):
    text_dialog = _PreviewDialog("预览", "纯文本内容")
    assert "纯文本内容" in text_dialog.viewer.toPlainText()

    html_dialog = _PreviewDialog("预览", "后备文本", html="<p>HTML 内容</p>")
    assert "HTML 内容" in html_dialog.viewer.toPlainText()


def test_export_page_stashes_the_full_preview(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "property")
    wizard.export_page.show_preview()

    text = getattr(wizard.export_page, "_last_preview_text", "")
    html = getattr(wizard.export_page, "_last_preview_html", "")
    assert "民 事 起 诉 状" in text
    assert "物业费" in text
    assert "<html>" in html


def test_arbitration_application_preview_uses_applicant_terms(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "labor")
    page = wizard.labor_claim_page
    page.procedure_combo.setCurrentIndex(
        page.procedure_combo.findData("not_applied")
    )
    page._role_buttons["employee"].setChecked(True)
    page.arb_commission.setText("示例劳动人事争议仲裁委员会")

    wizard.export_page.show_preview()

    text = getattr(wizard.export_page, "_last_preview_text", "")
    assert "劳 动 仲 裁 申 请 书" in text
    assert "仲裁请求：" in text
    assert "申请人：" in text
    assert "示例劳动人事争议仲裁委员会" in text
    assert "诉讼请求：" not in text
    assert "人民法院" not in text
