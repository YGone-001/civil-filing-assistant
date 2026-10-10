# File: tests/test_e2e_documents.py
# Purpose: End-to-end acceptance for all five case categories (5 x 3 DOCX) and
#          case-fact integrity regression (no unsupported factual assertions).
# Encoding: UTF-8
"""Full-flow document acceptance and case-fact integrity.

Each case category runs the real wizard -> model -> DocumentGenerator pipeline
and produces three Word documents in a temporary directory. No case model or
document generator is replaced with a fake implementation here.

The factual-integrity tests assert against the *generated DOCX text*, not just
``render_facts()`` strings, so a regression that re-introduces an unsupported
assertion is caught where it actually matters.
"""

import os

import pytest

from helpers import (
    CASE_TYPES,
    docx_all_text,
    fill_minimal_case,
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
    "contract": ["无理拒绝", "多次催告", "原告已向被告催告"],
    "property": ["无故拖欠", "已构成违约", "多次向被告履行", "签署了《物业服务合同》"],
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


def _complaint_text(docs):
    return docx_all_text(_find(docs, "民事起诉状"))


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

    complaint = _complaint_text(docs)
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

    complaint = _complaint_text(docs)
    assert "离婚" in complaint
    assert "抚养" not in complaint
    assert "子女" not in complaint


def test_divorce_with_property_division(qapp, monkeypatch, tmp_path):
    docs = _export(tmp_path, monkeypatch, "divorce")
    complaint = _complaint_text(docs)
    assert "共同财产" in complaint
    assert "房产归原告" in complaint


def test_invalid_interest_rate_keeps_neutral_claim(qapp, monkeypatch, tmp_path):
    def _bad_rate(wizard):
        wizard.loan_claim_page.rate.setText("abc")

    docs = _export(tmp_path, monkeypatch, "loan", mutate=_bad_rate)
    assert len(docs) == 3
    complaint = _complaint_text(docs)
    # No fabricated interest figure; an explicit manual-review statement instead.
    assert "具体金额以实际清偿日结算为准" in complaint


def test_reversed_labor_period_uses_editable_placeholder(qapp, monkeypatch, tmp_path):
    def _reversed(wizard):
        wizard.labor_claim_page.unpaid_months.setText("2024年5月至2024年1月")

    docs = _export(tmp_path, monkeypatch, "labor", mutate=_reversed)
    assert len(docs) == 3
    complaint = _complaint_text(docs)
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
    complaint = _complaint_text(docs)
    assert "违约金" not in complaint


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_no_fabricated_case_facts(qapp, monkeypatch, tmp_path, case_type):
    """The complaint must not contain phrases the template once invented on its own."""
    docs = _export(tmp_path, monkeypatch, case_type)
    complaint = _complaint_text(docs)

    for phrase in FORBIDDEN_FABRICATIONS[case_type]:
        assert phrase not in complaint, f"{case_type}: fabricated phrase {phrase!r} still present"

    for phrase in CORRECTED_PHRASES[case_type]:
        assert phrase in complaint, f"{case_type}: expected phrase {phrase!r} missing"


# --- C1: case-fact integrity (no unsupported assertions) -------------------


def test_contract_without_demand_has_no_demand_assertion(qapp, monkeypatch, tmp_path):
    """C1-T01: the sales-contract complaint must not invent a payment demand."""
    docs = _export(tmp_path, monkeypatch, "contract")
    complaint = _complaint_text(docs)

    for phrase in ("原告已向被告催告", "经原告多次催告", "原告已多次催告", "催告", "催讨"):
        assert phrase not in complaint, f"unsupported demand assertion: {phrase!r}"
    # The supplied balance must still be stated.
    assert "30000" in complaint


def test_contract_with_confirmed_delivery_preserved(qapp, monkeypatch, tmp_path):
    """C1-T02: confirmed delivery details must remain accurate."""
    docs = _export(tmp_path, monkeypatch, "contract")
    complaint = _complaint_text(docs)

    assert "2023年2月1日" in complaint
    assert "完成交货" in complaint
    assert "被告已签收" in complaint


def test_contract_without_receipt_does_not_assert_receipt(qapp, monkeypatch, tmp_path):
    """C1-T03: with 'not signed' selected, receipt must not be asserted."""
    def _not_signed(wizard):
        wizard.contract_claim_page.sign_no.setChecked(True)

    docs = _export(tmp_path, monkeypatch, "contract", mutate=_not_signed)
    complaint = _complaint_text(docs)

    assert "被告已签收" not in complaint
    assert "尚未签收" in complaint
    assert "无理拒绝" not in complaint


def test_property_without_contract_signature_makes_no_signature_claim(qapp, monkeypatch, tmp_path):
    """C1-T04: no specific contract-signature event may be invented."""
    docs = _export(tmp_path, monkeypatch, "property")
    complaint = _complaint_text(docs)

    assert "签署了《物业服务合同》" not in complaint
    assert "物业服务企业" not in complaint
    # Supplied facts survive.
    assert "115.5" in complaint
    assert "7761.60" in complaint
    # Contract details are flagged as requiring confirmation.
    assert "人工核对" in complaint


def test_property_without_demand_record_has_no_demand(qapp, monkeypatch, tmp_path):
    """C1-T05: an empty demand record must not become a demand allegation."""
    def _no_demand(wizard):
        wizard.property_claim_page.demand_record.setPlainText("")

    docs = _export(tmp_path, monkeypatch, "property", mutate=_no_demand)
    complaint = _complaint_text(docs)

    assert "催缴" not in complaint
    assert "无故拖欠" not in complaint
    assert "已构成违约" not in complaint


def test_property_with_supplied_demand_record_keeps_only_supported_demand(qapp, monkeypatch, tmp_path):
    """C1-T06: a supplied demand record is preserved verbatim and alone."""
    docs = _export(tmp_path, monkeypatch, "property")
    complaint = _complaint_text(docs)

    assert "向被告催缴" in complaint
    assert "2025年6月多次张贴催缴通知并发送短信。" in complaint
    # Still no invented bad-faith/legal-conclusion assertions.
    assert "无故拖欠" not in complaint
    assert "已构成违约" not in complaint


def test_loan_optional_fields_omitted_no_fabrication(qapp, monkeypatch, tmp_path):
    """C1-T07: omitting optional loan fields invents no relationship or demand."""
    def _strip(wizard):
        page = wizard.loan_claim_page
        page.rate.setText("")
        page.start_date.setText("")
        page.demand_date.setText("")
        page.demand_method.setText("")

    docs = _export(tmp_path, monkeypatch, "loan", mutate=_strip)
    complaint = _complaint_text(docs)

    assert "朋友关系" not in complaint
    assert "催讨" not in complaint
    assert "约定借款年利率" not in complaint
    assert "50000" in complaint


def test_labor_optional_fields_omitted_no_fabrication(qapp, monkeypatch, tmp_path):
    """C1-T08: omitting optional labor fields invents no overtime/performance facts."""
    def _strip(wizard):
        page = wizard.labor_claim_page
        page.overtime_hours.setText("")
        page.overtime_pay.setText("")
        page.social_sec_info.setText("")

    docs = _export(tmp_path, monkeypatch, "labor", mutate=_strip)
    complaint = _complaint_text(docs)

    assert "兢兢业业" not in complaint
    assert "加班" not in complaint
    assert "8000" in complaint


def test_divorce_without_optional_conflict_details(qapp, monkeypatch, tmp_path):
    """C1-T09: an unprovided conflict/separation/child/property fact is not invented."""
    def _strip(wizard):
        page = wizard.divorce_claim_page
        page.divorce_reason.setText("")
        page.separation_start_date.setText("")
        page.child_name.setText("")
        page.child_birthday.setText("")
        page.custody_preference.setText("")
        page.support_monthly.setText("")
        page.asset_description.setText("")

    docs = _export(tmp_path, monkeypatch, "divorce", mutate=_strip)
    complaint = _complaint_text(docs)

    assert "离婚" in complaint
    assert "生活琐事" not in complaint
    assert "分居" not in complaint
    assert "抚养" not in complaint
    assert "共同财产" not in complaint


@pytest.mark.parametrize(
    "case_type,needle",
    [
        ("loan", "50000"),
        ("contract", "30000"),
        ("property", "115.5"),
        ("labor", "8000"),
        ("divorce", "3000"),
    ],
)
def test_confirmed_user_facts_preserved(qapp, monkeypatch, tmp_path, case_type, needle):
    """C1-T10: explicitly supplied facts must survive into the complaint."""
    docs = _export(tmp_path, monkeypatch, case_type)
    complaint = _complaint_text(docs)
    assert needle in complaint, f"{case_type}: supplied fact {needle!r} missing"


def test_preview_matches_exported_complaint(qapp, monkeypatch, tmp_path):
    """C1-T11: the preview is derived from the same model as the export."""
    from presenters.model_builder import build_case_model

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    prepare_case(wizard, "property")

    model = build_case_model(wizard)
    preview_facts = model.render_facts()
    preview_claims = model.render_claims()

    presenter.on_wizard_accepted()
    docs = sorted((home / "Desktop").rglob("*.docx"))
    complaint = _complaint_text(docs)

    assert preview_facts in complaint, "preview facts differ from the exported complaint"
    for claim in preview_claims:
        assert claim in complaint, f"preview claim missing from export: {claim!r}"


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_minimum_factual_input_no_fabrication(qapp, monkeypatch, tmp_path, case_type):
    """C1-T12: minimal supported input produces three documents and no invented facts."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))

    wizard, presenter = make_wizard()
    fill_minimal_case(wizard, case_type)
    presenter.on_wizard_accepted()

    docs = sorted((home / "Desktop").rglob("*.docx"))
    assert len(docs) == 3, [d.name for d in docs]
    complaint = _complaint_text(docs)

    for phrase in FORBIDDEN_FABRICATIONS[case_type]:
        assert phrase not in complaint, f"{case_type}: fabricated phrase {phrase!r} present"
