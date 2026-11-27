# File: tests/test_agent_and_appendix.py
# Purpose: Agent paragraph, appendix note and detail-field pipeline tests.
# Encoding: UTF-8
"""Covers the borrowed features end to end:

* the optional agent paragraph (present with data, absent without, robust to
  blank roles) and its fonts;
* the auto-computed attachment note ("附：本状副本X份");
* natural-person detail fields flowing UI -> model -> document;
* the agent record surviving a draft capture/validate round trip.
"""

import pytest
from docx import Document

from helpers import DEFAULT_DEFENDANTS, DEFAULT_PLAINTIFFS, make_wizard, select_case, set_parties
from models.case_model import AgentInfo, LoanCaseModel, PartyInfo
from presenters.model_builder import build_case_model
from utils.doc_generator import DocumentGenerator
from views.draft_io import capture_draft


def _complaint_paragraphs(path):
    return [p.text for p in Document(str(path)).paragraphs]


def _minimal_model(defendants=1, agent=None):
    model = LoanCaseModel()
    model.has_repayment = False
    model.party_manager.add_party(0, PartyInfo("张三（测试）", "", "北京市示例区原告路1号", ""))
    for i in range(defendants):
        model.party_manager.add_party(
            1, PartyInfo(f"被告{i + 1}（测试）", "", "上海市示例区被告街2号", "")
        )
    model.court_name = "示例区人民法院"
    model.agent = agent
    return model


def test_complaint_includes_agent_paragraph(qapp, tmp_path):
    model = _minimal_model(agent=AgentInfo("王五（测试）", "律师", "示例律师事务所", "13700000000"))
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(model, str(path))

    agent_lines = [line for line in _complaint_paragraphs(path) if line.startswith("诉讼代理人：")]
    assert len(agent_lines) == 1
    assert "王五（测试）（律师），示例律师事务所，联系电话13700000000。" in agent_lines[0]


def test_complaint_agent_paragraph_fonts(qapp, tmp_path):
    from docx.oxml.ns import qn

    model = _minimal_model(agent=AgentInfo("王五（测试）", "律师", "示例律师事务所", ""))
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(model, str(path))

    doc = Document(str(path))
    para = next(p for p in doc.paragraphs if p.text.startswith("诉讼代理人："))
    prefix, content = para.runs[0], para.runs[1]
    assert prefix.font.name == "SimHei"
    assert content.font.name == "FangSong_GB2312"
    assert content._element.rPr.rFonts.get(qn("w:eastAsia")) == "FangSong_GB2312"


def test_complaint_without_agent_has_no_agent_paragraph(qapp, tmp_path):
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(_minimal_model(), str(path))
    assert not any(
        line.startswith("诉讼代理人：") for line in _complaint_paragraphs(path)
    )


def test_agent_without_stated_role_renders_without_parentheses(qapp, tmp_path):
    model = _minimal_model(agent=AgentInfo("王五（测试）", "", "示例律师事务所", ""))
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(model, str(path))
    agent_lines = [line for line in _complaint_paragraphs(path) if line.startswith("诉讼代理人：")]
    assert agent_lines == ["诉讼代理人：王五（测试），示例律师事务所。"]


def test_appendix_notes_one_copy_set_per_defendant(qapp, tmp_path):
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(_minimal_model(defendants=2), str(path))
    appendix = [line for line in _complaint_paragraphs(path) if line.startswith("附：")]
    assert appendix == ["附：本状副本2份。"]


def test_appendix_absent_without_defendants(qapp, tmp_path):
    model = _minimal_model(defendants=0)
    path = tmp_path / "complaint.docx"
    DocumentGenerator().export_complaint(model, str(path))
    assert not any(line.startswith("附：") for line in _complaint_paragraphs(path))


def test_detail_fields_flow_from_ui_to_model(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(
        wizard,
        plaintiffs=[
            {
                "name": "张三（测试）",
                "gender": "男",
                "birth_date": "1990-01-01",
                "ethnicity": "其他",
                "ethnicity_other": "珞巴",
                "occupation": "务农",
            }
        ],
    )

    model = build_case_model(wizard)
    plaintiff = model.party_manager.plaintiffs[0]
    assert plaintiff.gender == "男"
    assert plaintiff.birth_date == "1990-01-01"
    # The "其他" combo selection resolves to the typed free-text value.
    assert plaintiff.ethnicity == "珞巴"
    assert plaintiff.occupation == "务农"

    from utils.doc_generator import DocumentGenerator

    line = DocumentGenerator._party_line(plaintiff)
    assert line == "张三（测试），男，1990年1月1日出生，珞巴族，务农。"


def test_company_party_detail_fields_do_not_leak_into_document(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    set_parties(
        wizard,
        plaintiffs=[
            {
                "name": "示例公司（测试）",
                "is_company": True,
                "credit_code": "91310000MA1FL0XXXX",
                "legal_rep": "王五（测试）",
                "gender": "男",
                "occupation": "务农",
            }
        ],
    )
    model = build_case_model(wizard)
    company = model.party_manager.plaintiffs[0]
    assert company.is_company is True
    line = DocumentGenerator._party_line(company)
    assert "性别" not in line and "务农" not in line and "男" not in line[6:]


def test_agent_record_survives_draft_capture(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=DEFAULT_PLAINTIFFS, defendants=DEFAULT_DEFENDANTS)

    # Section closed -> agent is None in the draft.
    payload = capture_draft(wizard)
    assert payload["agent"] is None

    # Opened and filled -> the full record is captured.
    wizard.party_page.set_agent_data(
        {"name": "王五（测试）", "type": "法律工作者", "org": "示例法律服务所", "phone": ""}
    )
    payload = capture_draft(wizard)
    assert payload["agent"] == {
        "name": "王五（测试）",
        "type": "法律工作者",
        "org": "示例法律服务所",
        "phone": "",
    }

    # The captured record restores verbatim into a fresh page.
    from views.pages.party import PartyPage

    fresh = PartyPage()
    fresh.set_agent_data(payload["agent"])
    assert fresh.get_agent_data() == payload["agent"]


def test_blank_agent_section_is_not_attached_to_the_model(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard)
    wizard.party_page._toggle_agent_section()  # opened but nothing typed
    model = build_case_model(wizard)
    assert model.agent is None
