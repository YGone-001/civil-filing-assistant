# File: tests/test_e2e_documents.py
# Purpose: End-to-end acceptance for all five case categories (5 x 3 DOCX).
# Encoding: UTF-8
"""Full-flow document acceptance.

Each case category runs the real wizard -> model -> DocumentGenerator pipeline
and produces three Word documents in a temporary directory. No case model or
document generator is replaced with a fake implementation here.
"""

import os

import pytest

from helpers import (
    CASE_TYPES,
    docx_all_text,
    make_wizard,
    prepare_case,
    set_parties,
    verify_docx_package,
)

CASE_CONTENT = {
    "loan": ["偿还借款本金", "上海市徐汇区人民法院", "原告甲（测试）", "被告乙（测试）", "50000"],
    "contract": ["货款本金", "上海市徐汇区人民法院", "30000"],
    "property": ["物业费", "7761.60", "115.5"],
    "labor": ["欠付工资", "24000.00", "8000"],
    "divorce": ["离婚", "抚养费", "3000"],
}

# C3: every phrase below was previously invented by the template without any
# corresponding user input. Each must now be absent from the generated complaint.
FORBIDDEN_FABRICATIONS = {
    "loan": ["朋友关系", "多次催讨"],
    "contract": ["无理拒绝", "多次催告"],
    "property": ["无故拖欠", "已构成违约", "多次向被告履行"],
    "labor": ["兢兢业业"],
    "divorce": ["生活琐事"],
}

# What the corrected template actually emits for each filled, fictional case.
CORRECTED_PHRASES = {
    "loan": ["被告未偿还借款"],
    "contract": ["被告已签收"],
    "property": ["向被告催缴"],
    "labor": ["未按时足额支付"],
    "divorce": ["双方感情确已破裂"],
}

# C3: every phrase below was previously invented by the template without any
# corresponding user input. Each must now be absent from the generated complaint.
FORBIDDEN_FABRICATIONS = {
    "loan": ["朋友关系", "多次催讨"],
    "contract": ["无理拒绝", "多次催告"],
    "property": ["无故拖欠", "已构成违约", "多次向被告履行"],
    "labor": ["兢兢业业"],
    "divorce": ["生活琐事"],
}

# What the corrected template actually emits for each filled, fictional case.
CORRECTED_PHRASES = {
    "loan": ["被告未偿还借款"],
    "contract": ["被告已签收"],
    "property": ["向被告催缴"],
    "labor": ["未按时足额支付"],
    "divorce": ["双方感情确已破裂"],
}


def _export(tmp_path, monkeypatch, case_type, plaintiffs=None, defendants=None, mutate=None):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, case_type, plaintiffs=plaintiffs, defendants=defendants)
    if mutate is not None:
        mutate(wizard)

    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    return docs


def _find(docs, keyword):
    for doc in docs:
        if keyword in doc.name:
            return doc
    raise AssertionError(f"no document matching {keyword!r} in {[d.name for d in docs]}")


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_e2e_three_documents_per_case(qapp, monkeypatch, tmp_path, case_type):
    docs = _export(tmp_path, monkeypatch, case_type)

    assert len(docs) == 3, [d.name for d in docs]
    for doc in docs:
        verify_docx_package(doc)

    names = " ".join(d.name for d in docs)
    assert "民事起诉状" in names
    assert "证据清单" in names
    assert "送达地址确认书" in names

    joined = "\n".join(docx_all_text(doc) for doc in docs)
    for needle in CASE_CONTENT[case_type]:
        assert needle in joined, f"{case_type}: missing {needle!r}"


def test_multiple_plaintiffs_and_corporate_party(qapp, monkeypatch, tmp_path):
    plaintiffs = [
        {"name": "原告甲（测试）", "id_number": "示例A", "address": "地A", "phone": "13800000001"},
        {
            "name": "示例科技（测试）有限公司",
            "is_company": True,
            "credit_code": "91310000MA1FL0TEST",
            "legal_rep": "赵六",
            "address": "地B",
            "phone": "021-00000000",
        },
    ]
    defendants = [
        {"name": "被告乙（测试）", "id_number": "示例B", "address": "地C", "phone": "13900000001"},
        {"name": "被告丙（测试）", "id_number": "示例C", "address": "地D", "phone": "13900000002"},
    ]
    docs = _export(tmp_path, monkeypatch, "loan", plaintiffs=plaintiffs, defendants=defendants)
    assert len(docs) == 3

    complaint = docx_all_text(_find(docs, "民事起诉状"))
    assert "原告甲（测试）" in complaint
    assert "示例科技（测试）有限公司" in complaint
    assert "91310000MA1FL0TEST" in complaint
    assert "被告丙（测试）" in complaint

    address = docx_all_text(_find(docs, "送达地址确认书"))
    for label in ("原告1", "原告2", "被告1", "被告2"):
        assert label in address, f"address form missing distinct party label {label!r}"
    assert "91310000MA1FL0TEST" in address


def test_divorce_without_children_has_no_custody_or_support(qapp, monkeypatch, tmp_path):
    def _clear(wizard):
        page = wizard.divorce_claim_page
        page.child_name.setText("")
        page.child_birthday.setText("")
        page.custody_preference.setText("")
        page.support_monthly.setText("")

    docs = _export(tmp_path, monkeypatch, "divorce", mutate=_clear)
    assert len(docs) == 3

    complaint = docx_all_text(_find(docs, "民事起诉状"))
    assert "离婚" in complaint
    assert "抚养" not in complaint
    assert "子女" not in complaint


def test_divorce_with_property_division(qapp, monkeypatch, tmp_path):
    docs = _export(tmp_path, monkeypatch, "divorce")
    complaint = docx_all_text(_find(docs, "民事起诉状"))
    assert "共同财产" in complaint
    assert "房产归原告" in complaint


def test_invalid_interest_rate_keeps_neutral_claim(qapp, monkeypatch, tmp_path):
    def _bad_rate(wizard):
        wizard.loan_claim_page.rate.setText("abc")

    docs = _export(tmp_path, monkeypatch, "loan", mutate=_bad_rate)
    assert len(docs) == 3
    complaint = docx_all_text(_find(docs, "民事起诉状"))
    # No fabricated interest figure; an explicit manual-review statement instead.
    assert "具体金额以实际清偿日结算为准" in complaint


def test_reversed_labor_period_uses_editable_placeholder(qapp, monkeypatch, tmp_path):
    def _reversed(wizard):
        wizard.labor_claim_page.unpaid_months.setText("2024年5月至2024年1月")

    docs = _export(tmp_path, monkeypatch, "labor", mutate=_reversed)
    assert len(docs) == 3
    complaint = docx_all_text(_find(docs, "民事起诉状"))
    assert "人工确认" in complaint


def test_evidence_order_matches_interface(qapp, monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, "contract")
    page = wizard.evidence_page
    page.table.setRowCount(0)
    page.add_row("证据甲（测试）", "目的甲")
    page.add_row("证据乙（测试）", "目的乙")

    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    evidence_text = docx_all_text(_find(docs, "证据清单"))
    assert evidence_text.index("证据甲（测试）") < evidence_text.index("证据乙（测试）")


def test_optional_fields_omitted_does_not_fabricate(qapp, monkeypatch, tmp_path):
    """Empty optional fields must not invent facts and must not crash."""
    def _strip(wizard):
        page = wizard.contract_claim_page
        page.penalty_amount.setText("")
        page.overdue_start.setText("")
        page.lpr_value.setText("")
        page.lpr_multiple.setText("")

    docs = _export(tmp_path, monkeypatch, "contract", mutate=_strip)
    assert len(docs) == 3
    complaint = docx_all_text(_find(docs, "民事起诉状"))
    assert "违约金" not in complaint


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_no_fabricated_case_facts(qapp, monkeypatch, tmp_path, case_type):
    """The complaint must not contain phrases the template once invented on its own."""
    docs = _export(tmp_path, monkeypatch, case_type)
    complaint = docx_all_text(_find(docs, "民事起诉状"))

    for phrase in FORBIDDEN_FABRICATIONS[case_type]:
        assert phrase not in complaint, f"{case_type}: fabricated phrase {phrase!r} still present"

    for phrase in CORRECTED_PHRASES[case_type]:
        assert phrase in complaint, f"{case_type}: expected phrase {phrase!r} missing"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_no_fabricated_case_facts(qapp, monkeypatch, tmp_path, case_type):
    """The complaint must not contain phrases the template once invented on its own."""
    docs = _export(tmp_path, monkeypatch, case_type)
    complaint = docx_all_text(_find(docs, "民事起诉状"))

    for phrase in FORBIDDEN_FABRICATIONS[case_type]:
        assert phrase not in complaint, f"{case_type}: fabricated phrase {phrase!r} still present"

    for phrase in CORRECTED_PHRASES[case_type]:
        assert phrase in complaint, f"{case_type}: expected phrase {phrase!r} missing"
