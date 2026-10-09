# File: tests/test_party_data.py
# Purpose: Regression tests for party extraction/validation across case types.
# Encoding: UTF-8

import pytest

from helpers import DEFAULT_DEFENDANTS, DEFAULT_PLAINTIFFS, make_wizard, select_case, set_parties


@pytest.mark.parametrize("case_type", ["loan", "contract", "property", "labor", "divorce"])
def test_get_party_data_never_raises_for_any_case(qapp, case_type):
    """Regression: company fields used to be None for non-property cases."""
    wizard, _ = make_wizard()
    select_case(wizard, case_type)
    set_parties(wizard)

    data = wizard.party_page.get_party_data()
    assert len(data["plaintiffs"]) >= 1
    assert len(data["defendants"]) >= 1
    assert data["plaintiffs"][0]["name"] == "原告甲（测试）"

    expected_keys = {
        "name",
        "id_number",
        "address",
        "phone",
        "is_company",
        "credit_code",
        "legal_representative",
    }
    assert set(data["plaintiffs"][0]) == expected_keys


def test_company_party_values_extracted(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "contract")
    set_parties(
        wizard,
        plaintiffs=[
            {
                "name": "示例物业服务有限公司",
                "is_company": True,
                "credit_code": "91310000MA1FL0XXXX",
                "legal_rep": "王五",
                "address": "上海市示例区示例路9号",
                "phone": "021-12345678",
            }
        ],
    )

    data = wizard.party_page.get_party_data()
    plaintiff = data["plaintiffs"][0]
    assert plaintiff["is_company"] is True
    assert plaintiff["credit_code"] == "91310000MA1FL0XXXX"
    assert plaintiff["legal_representative"] == "王五"


def test_multiple_plaintiffs_and_defendants_preserved(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(
        wizard,
        plaintiffs=[
            {"name": "原告甲（测试）", "id_number": "示例A", "address": "地A", "phone": "13800000001"},
            {"name": "原告丙（测试）", "id_number": "示例C", "address": "地C", "phone": "13800000003"},
        ],
        defendants=[
            {"name": "被告乙（测试）", "id_number": "示例B", "address": "地B", "phone": "13800000002"},
            {"name": "被告丁（测试）", "id_number": "示例D", "address": "地D", "phone": "13800000004"},
        ],
    )

    data = wizard.party_page.get_party_data()
    assert [p["name"] for p in data["plaintiffs"]] == ["原告甲（测试）", "原告丙（测试）"]
    assert [d["name"] for d in data["defendants"]] == ["被告乙（测试）", "被告丁（测试）"]


def test_missing_plaintiff_detected(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=[{"name": ""}], defendants=DEFAULT_DEFENDANTS)

    issues = wizard.party_page.validate_parties()
    assert any("原告" in i for i in issues)
    assert wizard.party_page.isComplete() is False


def test_missing_defendant_detected(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=DEFAULT_PLAINTIFFS, defendants=[{"name": "  "}])

    issues = wizard.party_page.validate_parties()
    assert any("被告" in i for i in issues)
    assert wizard.party_page.isComplete() is False


def test_blank_party_name_reported(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=[{"name": "   "}], defendants=DEFAULT_DEFENDANTS)

    issues = wizard.party_page.validate_parties()
    assert any("不能为空" in i for i in issues)


def test_phone_length_warning_is_advisory(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "loan")
    set_parties(wizard, plaintiffs=[{**DEFAULT_PLAINTIFFS[0], "phone": "123"}])

    issues = wizard.party_page.validate_parties()
    assert any("电话" in i for i in issues)
    # Advisory only: a named plaintiff/defendant is still considered complete.
    assert wizard.party_page.isComplete() is True


def test_company_credit_code_format_warning(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "property")
    set_parties(
        wizard,
        plaintiffs=[
            {"name": "示例公司", "is_company": True, "credit_code": "BAD-CODE"}
        ],
    )

    issues = wizard.party_page.validate_parties()
    assert any("统一社会信用代码" in i for i in issues)


def test_complete_with_valid_parties(qapp):
    wizard, _ = make_wizard()
    select_case(wizard, "divorce")
    set_parties(wizard)
    assert wizard.party_page.isComplete() is True
