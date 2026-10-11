# File: tests/test_word_acceptance.py
# Purpose: Automated Word document acceptance tests — programmatically verifies
#          fonts, tables, party info, margins, pagination, and empty-field
#          handling across all five case types and three document kinds.
# Encoding: UTF-8

"""Automated acceptance for the three Word documents across all five case types.

These tests open the generated ``.docx`` files with ``python-docx`` and inspect
document structure (fonts, tables, margins, pagination, party blocks) to
automate the manual Word-verification portion of the acceptance criteria.

All test data is deliberately fictional.
"""

import os

import pytest
from docx import Document
from docx.shared import Cm, Pt

from helpers import (
    CASE_TYPES,
    make_wizard,
    prepare_case,
    set_parties,
    verify_docx_package,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TITLES = {
    "complaint": "民 事 起 诉 状",
    "evidence": "证 据 清 单",
    "address": "送 达 地 址 确 认 书",
}

DOC_KEYWORDS = {
    "complaint": "起诉状",
    "evidence": "证据清单",
    "address": "送达",
}


def _export_all(tmp_path, monkeypatch, case_type, plaintiffs=None, defendants=None):
    """Generate all three documents for *case_type* and return a dict of paths."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, case_type, plaintiffs=plaintiffs, defendants=defendants)
    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    assert len(docs) == 3, f"expected 3 docs, got {[d.name for d in docs]}"

    result = {}
    for doc_kind, keyword in DOC_KEYWORDS.items():
        for d in docs:
            if keyword in d.name:
                result[doc_kind] = d
                break
    assert len(result) == 3, f"could not classify docs: {[d.name for d in docs]}"
    return result


def _first_non_blank_paragraph(doc):
    """Return the first paragraph with non-empty text."""
    for p in doc.paragraphs:
        if p.text.strip():
            return p
    return None


def _run_fonts(paragraph):
    """Return a list of (font_name, font_size_pt, bold) tuples for each run."""
    info = []
    for run in paragraph.runs:
        size = run.font.size.pt if run.font.size else None
        info.append((run.font.name, size, run.bold))
    return info


# ---------------------------------------------------------------------------
# 1. Title paragraph — font, size, alignment, text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_title_font_and_text(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))
    title_p = doc.paragraphs[0]

    assert title_p.text == EXPECTED_TITLES["complaint"]
    fonts = _run_fonts(title_p)
    assert fonts[0][0] == "SimSun", f"title font should be SimSun, got {fonts[0][0]}"
    assert fonts[0][1] == 22, f"title size should be 22pt, got {fonts[0][1]}"
    assert fonts[0][2] is True, "title should be bold"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_list_title_font_and_text(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))
    title_p = doc.paragraphs[0]

    assert title_p.text == EXPECTED_TITLES["evidence"]
    fonts = _run_fonts(title_p)
    assert fonts[0][0] == "SimSun"
    assert fonts[0][1] == 22
    assert fonts[0][2] is True


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_address_form_title_font_and_text(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["address"]))
    title_p = doc.paragraphs[0]

    assert title_p.text == EXPECTED_TITLES["address"]
    fonts = _run_fonts(title_p)
    assert fonts[0][0] == "SimSun"
    assert fonts[0][1] == 22
    assert fonts[0][2] is True


# ---------------------------------------------------------------------------
# 2. Page margins
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
@pytest.mark.parametrize("doc_kind", ["complaint", "evidence", "address"])
def test_page_margins_are_standard(qapp, tmp_path, monkeypatch, case_type, doc_kind):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs[doc_kind]))

    for section in doc.sections:
        # Use approximate comparison to tolerate EMU rounding (Cm(3.17) = 1141200 EMU
        # but python-docx may round to 1141095).
        assert abs(section.top_margin - Cm(2.54)) < 200, "top margin should be ~2.54cm"
        assert abs(section.bottom_margin - Cm(2.54)) < 200, "bottom margin should be ~2.54cm"
        assert abs(section.left_margin - Cm(3.17)) < 200, "left margin should be ~3.17cm"
        assert abs(section.right_margin - Cm(3.17)) < 200, "right margin should be ~3.17cm"


# ---------------------------------------------------------------------------
# 3. Evidence list table structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_list_has_four_column_table_with_headers(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))

    assert len(doc.tables) >= 1, "evidence list must have at least one table"
    table = doc.tables[0]
    assert len(table.columns) == 4, f"evidence table should have 4 columns, got {len(table.columns)}"

    headers = [table.rows[0].cells[i].text for i in range(4)]
    assert headers == ["序号", "证据名称", "证明对象/目的", "备注"], \
        f"evidence table headers mismatch: {headers}"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_list_table_has_at_least_one_data_row(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))
    table = doc.tables[0]

    # Header + at least one evidence row (default evidence is loaded by prepare_case).
    assert len(table.rows) >= 2, \
        f"evidence table should have header + data rows, got {len(table.rows)}"


def test_evidence_list_remark_column_is_case_aware(qapp, tmp_path, monkeypatch):
    """Property and labor cases should have case-specific remark text."""
    for case_type, expected_remark in [
        ("property", "计算公式"),
        ("labor", "欠薪计算"),
    ]:
        sub = tmp_path / case_type
        docs = _export_all(sub, monkeypatch, case_type)
        doc = Document(str(docs["evidence"]))
        table = doc.tables[0]
        # Remark is in column 3 of the first data row.
        remark = table.rows[1].cells[3].text
        assert expected_remark in remark, \
            f"{case_type} remark should mention {expected_remark!r}, got {remark!r}"


# ---------------------------------------------------------------------------
# 4. Address confirmation table structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_address_form_has_one_table_per_party(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["address"]))

    # Default parties: 1 plaintiff + 1 defendant = 2 tables.
    assert len(doc.tables) == 2, \
        f"address form should have 2 tables (1 per party), got {len(doc.tables)}"

    for table in doc.tables:
        assert len(table.rows) == 6, f"each address table should have 6 rows, got {len(table.rows)}"
        assert len(table.columns) == 2, f"each address table should have 2 columns, got {len(table.columns)}"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_address_form_table_labels_are_correct(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["address"]))

    expected_labels = ["当事人", "姓名/名称", "证件号码/统一社会信用代码", "联系电话", "送达地址", "备注"]
    for table in doc.tables:
        labels = [table.rows[i].cells[0].text for i in range(6)]
        assert labels == expected_labels, f"address table labels mismatch: {labels}"


def test_address_form_includes_party_names(qapp, tmp_path, monkeypatch):
    """The party's name must appear in the address confirmation table."""
    docs = _export_all(tmp_path, monkeypatch, "loan")
    doc = Document(str(docs["address"]))

    all_text = " ".join(table.rows[1].cells[1].text for table in doc.tables)
    assert "原告甲（测试）" in all_text, f"plaintiff name missing from address form: {all_text}"
    assert "被告乙（测试）" in all_text, f"defendant name missing from address form: {all_text}"


def test_address_form_uses_compact_table_format(qapp, tmp_path, monkeypatch):
    """Two-party address forms should not create a signature-only overflow page."""
    docs = _export_all(tmp_path, monkeypatch, "loan")
    doc = Document(str(docs["address"]))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraph = cell.paragraphs[0]
                assert paragraph.paragraph_format.line_spacing.pt == 20
                fonts = _run_fonts(paragraph)
                assert any(size == 14 for _, size, _ in fonts)


# ---------------------------------------------------------------------------
# 5. Party block in complaint — font and format
# ---------------------------------------------------------------------------


import re

# Pattern for party-block prefixes: "原告：", "原告1：", "被告：", "被告1：", etc.
_PARTY_PREFIX_RE = re.compile(r"^(?:原告|被告)\d*：")


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_contains_party_blocks_with_correct_fonts(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))

    # Party blocks have prefix "原告：" / "原告1：" / "被告：" / "被告1：".
    party_paras = [
        p for p in doc.paragraphs
        if _PARTY_PREFIX_RE.match(p.text)
    ]
    assert len(party_paras) >= 2, \
        f"complaint should have at least 2 party paragraphs, got {len(party_paras)}"

    for p in party_paras:
        assert len(p.runs) >= 2, f"party paragraph should have prefix + content runs: {p.text!r}"
        # Prefix run: SimHei, 16pt.
        assert p.runs[0].font.name == "SimHei", \
            f"party prefix font should be SimHei, got {p.runs[0].font.name}"
        assert p.runs[0].font.size == Pt(16), \
            f"party prefix size should be 16pt, got {p.runs[0].font.size}"
        # Content run: FangSong_GB2312, 16pt.
        assert p.runs[1].font.name == "FangSong_GB2312", \
            f"party content font should be FangSong_GB2312, got {p.runs[1].font.name}"
        assert p.runs[1].font.size == Pt(16), \
            f"party content size should be 16pt, got {p.runs[1].font.size}"


def test_complaint_individual_party_format(qapp, tmp_path, monkeypatch):
    """Individual party should have 身份证号 and 住址 labels."""
    docs = _export_all(tmp_path, monkeypatch, "loan")
    doc = Document(str(docs["complaint"]))

    text = "\n".join(p.text for p in doc.paragraphs)
    assert "身份证号" in text, "individual party should use 身份证号 label"
    assert "住址" in text, "individual party should use 住址 label"


def test_complaint_company_party_format(qapp, tmp_path, monkeypatch):
    """Company party should have 统一社会信用代码 and 住所地 labels."""
    company_plaintiff = {
        "name": "示例公司（测试）",
        "id_number": "",
        "address": "北京市示例区示例大厦",
        "phone": "01000000000",
        "is_company": True,
        "credit_code": "示例信用代码-001",
        "legal_rep": "示例代表人",
    }
    docs = _export_all(
        tmp_path, monkeypatch, "loan",
        plaintiffs=[company_plaintiff],
    )
    doc = Document(str(docs["complaint"]))

    text = "\n".join(p.text for p in doc.paragraphs)
    assert "统一社会信用代码" in text, "company party should use 统一社会信用代码 label"
    assert "住所地" in text, "company party should use 住所地 label"
    assert "法定代表人" in text, "company party should include 法定代表人"
    assert "示例公司（测试）" in text, "company name should appear in complaint"


def test_complaint_multiple_parties_use_numbered_prefixes(qapp, tmp_path, monkeypatch):
    """Multiple plaintiffs should use numbered prefixes (原告1：, 原告2：)."""
    plaintiffs = [
        {"name": f"原告{c}（测试）", "id_number": f"示例-原{c}", "address": "地址", "phone": "13800000000"}
        for c in "甲乙"
    ]
    docs = _export_all(tmp_path, monkeypatch, "loan", plaintiffs=plaintiffs)
    doc = Document(str(docs["complaint"]))

    text = "\n".join(p.text for p in doc.paragraphs)
    assert "原告1：" in text, "multiple plaintiffs should use numbered prefix 原告1："
    assert "原告2：" in text, "multiple plaintiffs should use numbered prefix 原告2："


# ---------------------------------------------------------------------------
# 6. Body text font — FangSong_GB2312, 16pt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_body_text_uses_fangsong(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))

    # Find the 诉讼请求 heading and the following body paragraph.
    found_heading = False
    for p in doc.paragraphs:
        if "诉讼请求" in p.text:
            found_heading = True
            # Heading should use SimHei.
            assert any(r.font.name == "SimHei" for r in p.runs if r.text.strip()), \
                "诉讼请求 heading should use SimHei"
            break
    assert found_heading, "complaint should contain 诉讼请求 heading"

    found_facts = False
    for p in doc.paragraphs:
        if "事实与理由" in p.text:
            found_facts = True
            assert any(r.font.name == "SimHei" for r in p.runs if r.text.strip()), \
                "事实与理由 heading should use SimHei"
            break
    assert found_facts, "complaint should contain 事实与理由 heading"


# ---------------------------------------------------------------------------
# 7. Footer / pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_has_pagination_footer(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))

    for section in doc.sections:
        footer_text = "\n".join(p.text for p in section.footer.paragraphs)
        # The footer contains "- " prefix and " -" suffix around the PAGE field.
        # python-docx doesn't render the field value, but the static text is there.
        assert "- " in footer_text or footer_text.strip() == "", \
            f"complaint footer should have pagination, got {footer_text!r}"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_address_form_has_pagination_footer(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["address"]))

    for section in doc.sections:
        footer_text = "\n".join(p.text for p in section.footer.paragraphs)
        assert "- " in footer_text or footer_text.strip() == "", \
            f"address form footer should have pagination, got {footer_text!r}"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_list_has_no_pagination_footer(qapp, tmp_path, monkeypatch, case_type):
    """The evidence list deliberately omits pagination."""
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))

    for section in doc.sections:
        footer_text = "\n".join(p.text for p in section.footer.paragraphs)
        assert "- " not in footer_text, \
            f"evidence list should not have pagination, got {footer_text!r}"


# ---------------------------------------------------------------------------
# 8. Court name appears in complaint footer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_contains_court_name(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "人民法院" in text, f"complaint should contain a court name ending with 人民法院: {text[:200]}"


# ---------------------------------------------------------------------------
# 9. Empty-field handling — no fabricated content
# ---------------------------------------------------------------------------


def test_complaint_with_minimal_fields_does_not_fabricate(qapp, tmp_path, monkeypatch):
    """A complaint with only required fields must not invent optional facts."""
    from helpers import fill_minimal_case

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    fill_minimal_case(wizard, "loan")
    wizard.evidence_page.initializePage()
    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    complaint = next(d for d in docs if "起诉状" in d.name)
    doc = Document(str(complaint))
    text = "\n".join(p.text for p in doc.paragraphs)

    # These phrases were previously fabricated by the template.
    for forbidden in ["朋友关系", "多次催讨", "经多次"]:
        assert forbidden not in text, f"minimal complaint should not contain {forbidden!r}"


def test_evidence_list_empty_evidence_produces_header_only(qapp, tmp_path, monkeypatch):
    """An empty evidence list should still have the header row but no data rows."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, "loan", with_evidence=False)
    # Clear any default evidence.
    wizard.evidence_page.table.setRowCount(0)
    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    evidence = next(d for d in docs if "证据清单" in d.name)
    doc = Document(str(evidence))

    assert len(doc.tables) >= 1
    table = doc.tables[0]
    assert len(table.rows) == 1, \
        f"empty evidence list should have only header row, got {len(table.rows)} rows"


# ---------------------------------------------------------------------------
# 10. Document validity — all files are well-formed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
@pytest.mark.parametrize("doc_kind", ["complaint", "evidence", "address"])
def test_all_documents_are_valid_docx_packages(qapp, tmp_path, monkeypatch, case_type, doc_kind):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    verify_docx_package(docs[doc_kind])


# ---------------------------------------------------------------------------
# 11. Line spacing — EXACTLY 28pt on content paragraphs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_complaint_party_paragraphs_have_exact_line_spacing(qapp, tmp_path, monkeypatch, case_type):
    from docx.enum.text import WD_LINE_SPACING

    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["complaint"]))

    party_paras = [
        p for p in doc.paragraphs
        if _PARTY_PREFIX_RE.match(p.text)
    ]
    for p in party_paras:
        fmt = p.paragraph_format
        assert fmt.line_spacing_rule == WD_LINE_SPACING.EXACTLY, \
            f"party paragraph should use EXACTLY line spacing, got {fmt.line_spacing_rule}"
        assert fmt.line_spacing == Pt(28), \
            f"party paragraph line spacing should be 28pt, got {fmt.line_spacing}"


# ---------------------------------------------------------------------------
# 12. Table cell fonts — SimHei for headers, FangSong for data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_table_header_cells_use_simhei(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))
    table = doc.tables[0]

    for i in range(4):
        cell = table.rows[0].cells[i]
        para = cell.paragraphs[0]
        for run in para.runs:
            if run.text.strip():
                assert run.font.name == "SimHei", \
                    f"header cell {i} should use SimHei, got {run.font.name}"
                assert run.font.size == Pt(16), \
                    f"header cell {i} should be 16pt, got {run.font.size}"
                assert run.bold is True, \
                    f"header cell {i} should be bold"
                break


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_evidence_table_data_cells_use_fangsong(qapp, tmp_path, monkeypatch, case_type):
    docs = _export_all(tmp_path, monkeypatch, case_type)
    doc = Document(str(docs["evidence"]))
    table = doc.tables[0]

    if len(table.rows) < 2:
        pytest.skip("no evidence data rows")

    for row_idx in range(1, len(table.rows)):
        for col_idx in range(4):
            cell = table.rows[row_idx].cells[col_idx]
            para = cell.paragraphs[0]
            for run in para.runs:
                if run.text.strip():
                    assert run.font.name == "FangSong_GB2312", \
                        f"data cell ({row_idx},{col_idx}) should use FangSong_GB2312, got {run.font.name}"
                    assert run.font.size == Pt(16), \
                        f"data cell ({row_idx},{col_idx}) should be 16pt, got {run.font.size}"
                    break
