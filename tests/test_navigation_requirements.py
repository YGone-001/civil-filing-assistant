# File: tests/test_navigation_requirements.py
# Purpose: Real QWizard Next/Finish-button acceptance for conditional field
#          requirements (C1 delivery date, C2 demand information, C3 children).
# Encoding: UTF-8
"""Real Next-button navigation acceptance.

These tests drive the *actual* QWizard Next and Finish buttons (via
``QTest.mouseClick``) rather than ``wizard.next()`` or presenter calls, so they
prove a real user can reach the export page for each supported scenario — and
that genuinely required fields still block progress.
"""

import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QValidator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QGroupBox, QWizard

from helpers import docx_all_text, make_wizard, select_case, set_parties
from presenters.model_builder import build_case_model
from views.theme import REMINDER_LABEL, SECONDARY_BUTTON

CLAIM_PAGE_ATTR = {
    "loan": "PAGE_LOAN_CLAIM",
    "contract": "PAGE_CONTRACT_CLAIM",
    "property": "PAGE_PROPERTY_CLAIM",
    "labor": "PAGE_LABOR_CLAIM",
    "divorce": "PAGE_DIVORCE_CLAIM",
}


def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda *a, **k: str(home))
    return home / "Desktop"


def _next(wizard):
    return wizard.button(QWizard.NextButton)


def _back(wizard):
    return wizard.button(QWizard.BackButton)


def _finish(wizard):
    return wizard.button(QWizard.FinishButton)


def _raw_click(wizard, qapp, button):
    """Click a real button, even if disabled (to prove the click is rejected)."""
    assert button is not None, "button missing"
    wizard.show()
    qapp.processEvents()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    qapp.processEvents()


def _click(wizard, qapp, button):
    """Click a real button that is expected to be enabled."""
    assert button is not None, "button missing"
    assert button.isEnabled(), f"button {button.text()!r} is disabled"
    _raw_click(wizard, qapp, button)


def _start(tmp_path, monkeypatch, case_type, qapp):
    """Drive a fresh wizard with real Next clicks to the case-specific claim page."""
    desktop = _home(tmp_path, monkeypatch)
    wizard, presenter = make_wizard()
    wizard.show()
    qapp.processEvents()

    _click(wizard, qapp, _next(wizard))                     # welcome -> case selection
    assert wizard.currentId() == wizard.PAGE_CASE_SELECTION
    select_case(wizard, case_type)
    qapp.processEvents()

    _click(wizard, qapp, _next(wizard))                     # -> party
    assert wizard.currentId() == wizard.PAGE_PARTY
    set_parties(wizard)
    qapp.processEvents()

    _click(wizard, qapp, _next(wizard))                     # -> claim page
    assert wizard.currentId() == getattr(wizard, CLAIM_PAGE_ATTR[case_type])
    return wizard, presenter, desktop


def _advance_to_export(wizard, qapp):
    _click(wizard, qapp, _next(wizard))                     # claim -> evidence
    assert wizard.currentId() == wizard.PAGE_EVIDENCE
    _click(wizard, qapp, _next(wizard))                     # evidence -> export
    assert wizard.currentId() == wizard.PAGE_EXPORT


def _finish_and_collect(wizard, qapp, desktop):
    _click(wizard, qapp, _finish(wizard))
    return sorted(desktop.rglob("*.docx"))


def _complaint(docs):
    for doc in docs:
        if "民事起诉状" in doc.name:
            return docx_all_text(doc)
    raise AssertionError(f"no complaint in {[d.name for d in docs]}")


def _fill_contract(wizard, delivery="unknown", date=""):
    p = wizard.contract_claim_page
    p.contract_date.setText("2023年1月1日")
    p.contract_name.setText("示例合同")
    p.product_name.setText("示例货物")
    p.total_amount.setText("10000")
    p.unpaid_amount.setText("8000")
    p.court_name.setText("示例人民法院")
    if delivery == "yes":
        p.del_yes.setChecked(True)
    elif delivery == "no":
        p.del_no.setChecked(True)
    p.delivery_date.setText(date)
    return p


def _fill_loan(wizard, demand_date="", demand_method="", iou=None):
    p = wizard.loan_claim_page
    p.loan_date.setText("2023年1月1日")
    p.loan_reason.setText("资金周转")
    p.principal.setText("10000")
    p.payment_method.setText("银行转账")
    p.court_name.setText("示例人民法院")
    p.demand_date.setText(demand_date)
    p.demand_method.setText(demand_method)
    if iou is True:
        p.iou_yes.setChecked(True)
    elif iou is False:
        p.iou_no.setChecked(True)
    return p


def _fill_divorce(wizard, child_name="", child_birthday="", custody="", support="", assets=""):
    p = wizard.divorce_claim_page
    p.marriage_date.setText("2018-05-20")
    p.court_name.setText("示例人民法院")
    p.child_name.setText(child_name)
    p.child_birthday.setText(child_birthday)
    p.custody_preference.setText(custody)
    p.support_monthly.setText(support)
    p.asset_description.setText(assets)
    return p


# --- C1: conditional delivery date -----------------------------------------


def test_c1_t01_unknown_delivery_empty_date_navigates(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "unknown", "")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)


def test_c1_t02_not_delivered_empty_date_navigates(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "no", "")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)


def test_c1_t03_delivered_without_date_blocks_then_recovers(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    page = _fill_contract(wizard, "yes", "")
    assert not _next(wizard).isEnabled()
    assert "交货日期" in page.cond_hint.text(), page.cond_hint.text()

    _raw_click(wizard, qapp, _next(wizard))                 # a disabled click must be rejected
    assert wizard.currentId() == wizard.PAGE_CONTRACT_CLAIM

    page.delivery_date.setText("2023年2月1日")               # correct it via the real control
    qapp.processEvents()
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)


def test_c1_t04_delivered_with_date_navigates_and_exports(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "yes", "2023年2月1日")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert len(docs) == 3, [d.name for d in docs]
    assert "原告已于2023年2月1日完成交货。" in _complaint(docs)


def test_c1_t05_true_to_unknown_reenables_next(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    page = _fill_contract(wizard, "yes", "")
    assert not _next(wizard).isEnabled()
    page.del_unknown.setChecked(True)
    qapp.processEvents()
    assert _next(wizard).isEnabled()


def test_c1_t06_unknown_to_true_disables_next(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    page = _fill_contract(wizard, "unknown", "")
    assert _next(wizard).isEnabled()
    page.del_yes.setChecked(True)
    qapp.processEvents()
    assert not _next(wizard).isEnabled()


def test_c1_t07_date_without_delivery_keeps_state_unknown(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "unknown", "2023年2月1日")
    assert build_case_model(wizard).is_delivered is None
    assert _next(wizard).isEnabled()


def test_c1_t08_unknown_no_date_exports_without_delivery_claim(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "unknown", "")
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert len(docs) == 3, [d.name for d in docs]
    text = _complaint(docs)
    assert "原告已于" not in text
    assert "尚未完成交货" not in text


def test_c1_t09_not_delivered_no_date_exports_negative_narrative(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "contract", qapp)
    _fill_contract(wizard, "no", "")
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert len(docs) == 3, [d.name for d in docs]
    assert "原告尚未完成交货。" in _complaint(docs)


# --- C2: optional private-lending demand information ------------------------


def test_c2_t01_no_demand_navigates(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)


def test_c2_t02_full_demand_navigates_and_is_preserved(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "2023年10月", "微信")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert "2023年10月" in _complaint(docs)


def test_c2_t03_only_demand_date_blocks(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    page = _fill_loan(wizard, "2023年10月", "")
    assert not _next(wizard).isEnabled()
    assert page.cond_hint.text()
    _raw_click(wizard, qapp, _next(wizard))
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM


# --- G: T05 民间借贷 / 买卖合同表单分组与输入约束 -------------------------


def _loan_page(qapp):
    wizard, _ = make_wizard()
    return wizard.loan_claim_page


def _contract_page(qapp):
    wizard, _ = make_wizard()
    return wizard.contract_claim_page


def _group_titles(page):
    return [g.title() for g in page.findChildren(QGroupBox)]


def test_g_t05_loan_form_is_grouped(qapp):
    titles = _group_titles(_loan_page(qapp))
    for expected in ("基本事实", "金额与利息", "催款情况", "管辖法院"):
        assert any(expected in t for t in titles), titles


def test_g_t05_contract_form_is_grouped(qapp):
    titles = _group_titles(_contract_page(qapp))
    for expected in ("基本事实", "履行与签收", "违约金", "管辖法院"):
        assert any(expected in t for t in titles), titles


def test_g_t05_loan_amount_and_rate_constrained(qapp):
    page = _loan_page(qapp)
    for field in (page.principal, page.rate):
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("14.6", 0)[0] == QValidator.State.Acceptable
        assert validator.validate("", 0)[0] == QValidator.State.Acceptable


def test_g_t05_contract_amount_and_lpr_constrained(qapp):
    page = _contract_page(qapp)
    for field in (page.total_amount, page.unpaid_amount, page.penalty_amount,
                  page.lpr_value, page.lpr_multiple):
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("3.45", 0)[0] == QValidator.State.Acceptable


def test_g_t05_contract_calc_buttons_are_auxiliary(qapp):
    page = _contract_page(qapp)
    assert "辅助" in page.calc_daily_btn.text()
    assert "辅助" in page.calc_lpr_btn.text()
    assert page.calc_daily_btn.objectName() == SECONDARY_BUTTON
    assert page.calc_lpr_btn.objectName() == SECONDARY_BUTTON
    assert page.calc_help.text()


def test_g_t05_tri_state_defaults_are_unconfirmed(qapp):
    assert _loan_page(qapp).get_has_iou() is None
    assert _contract_page(qapp).get_flags() == {"is_delivered": None, "is_signed": None}


def test_c2_t04_only_demand_method_blocks(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    page = _fill_loan(wizard, "", "微信")
    assert not _next(wizard).isEnabled()
    assert page.cond_hint.text()
    page.demand_date.setText("")                            # clear the partial record
    page.demand_method.setText("")
    qapp.processEvents()
    assert _next(wizard).isEnabled()


def test_c2_t05_clearing_both_reenables(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    page = _fill_loan(wizard, "2023年10月", "微信")
    assert _next(wizard).isEnabled()
    page.demand_date.setText("")
    qapp.processEvents()
    assert not _next(wizard).isEnabled()                    # now partial
    page.demand_method.setText("")
    qapp.processEvents()
    assert _next(wizard).isEnabled()


def test_c2_t06_real_next_reaches_evidence_without_demand(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "")
    _click(wizard, qapp, _next(wizard))
    assert wizard.currentId() == wizard.PAGE_EVIDENCE


def test_c2_t07_real_navigation_reaches_export(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "")
    _advance_to_export(wizard, qapp)


def test_c2_t08_real_finish_produces_three_documents(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "")
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert len(docs) == 3, [d.name for d in docs]


def test_c2_t09_no_fabricated_demand_event(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "")
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    for phrase in ("催讨", "催告"):
        assert phrase not in text, f"fabricated demand: {phrase!r}"


@pytest.mark.parametrize("iou,expected,forbidden", [
    (None, [], ["借条"]),
    (True, ["被告出具了借条。"], ["被告未出具借条"]),
    (False, ["被告未出具借条。"], ["被告出具了借条"]),
])
def test_c2_t10_iou_tri_state_still_correct(qapp, monkeypatch, tmp_path, dialog_recorder,
                                            iou, expected, forbidden):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "loan", qapp)
    _fill_loan(wizard, "", "", iou=iou)
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    for phrase in expected:
        assert phrase in text, f"missing {phrase!r} for iou={iou}"
    for phrase in forbidden:
        assert phrase not in text, f"unexpected {phrase!r} for iou={iou}"


# --- C3: divorce without children ------------------------------------------


def test_c3_t01_childless_divorce_next_enabled(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard)
    assert _next(wizard).isEnabled()


def test_c3_t02_real_next_reaches_evidence(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard)
    _click(wizard, qapp, _next(wizard))
    assert wizard.currentId() == wizard.PAGE_EVIDENCE


def test_c3_t03_real_next_reaches_export(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard)
    _advance_to_export(wizard, qapp)


def test_c3_t04_real_finish_produces_three_documents(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard)
    _advance_to_export(wizard, qapp)
    docs = _finish_and_collect(wizard, qapp, desktop)
    assert len(docs) == 3, [d.name for d in docs]


def test_c3_t05_childless_complaint_has_no_child_claims(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard)
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    assert "离婚" in text
    for phrase in ("子女", "抚养", "抚养费"):
        assert phrase not in text, f"fabricated child fact: {phrase!r}"


def test_c3_t06_child_identified_claims_preserved(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard, child_name="测试子女", child_birthday="2020-01-01",
                  custody="由原告抚养", support="3000")
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    assert "测试子女" in text
    assert "2020-01-01" in text
    assert "抚养费人民币3000元" in text


def test_c3_t07_child_without_birthday_navigates_without_fabricated_date(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard, child_name="测试子女")
    assert _next(wizard).isEnabled()
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    assert "测试子女" in text
    assert "出生" not in text or "2020" not in text


def test_c3_t08_support_without_child_blocks(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    page = _fill_divorce(wizard, support="3000")
    assert not _next(wizard).isEnabled()
    assert "子女姓名" in page.cond_hint.text()
    _raw_click(wizard, qapp, _next(wizard))
    assert wizard.currentId() == wizard.PAGE_DIVORCE_CLAIM


def test_c3_t09_birthday_without_child_blocks(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    page = _fill_divorce(wizard, child_birthday="2020-01-01")
    assert not _next(wizard).isEnabled()
    assert page.cond_hint.text()


def test_c3_t10_custody_without_child_blocks(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    page = _fill_divorce(wizard, custody="由原告抚养")
    assert not _next(wizard).isEnabled()
    assert page.cond_hint.text()


def test_c3_t11_childless_with_property_division(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    _fill_divorce(wizard, assets="房产归原告，车辆归被告")
    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    assert "房产归原告" in text
    assert "共同财产" in text
    for phrase in ("子女", "抚养"):
        assert phrase not in text


def test_c3_t12_backward_navigation_then_edit(qapp, monkeypatch, tmp_path, dialog_recorder):
    wizard, presenter, desktop = _start(tmp_path, monkeypatch, "divorce", qapp)
    page = _fill_divorce(wizard)
    _advance_to_export(wizard, qapp)

    _click(wizard, qapp, _back(wizard))                     # export -> evidence
    _click(wizard, qapp, _back(wizard))                     # evidence -> divorce claim
    assert wizard.currentId() == wizard.PAGE_DIVORCE_CLAIM

    page.child_name.setText("测试子女")
    page.child_birthday.setText("2020-01-01")
    page.support_monthly.setText("2000")
    qapp.processEvents()
    assert _next(wizard).isEnabled()

    _advance_to_export(wizard, qapp)
    text = _complaint(_finish_and_collect(wizard, qapp, desktop))
    assert "测试子女" in text
    assert "抚养费人民币2000元" in text


# --- P0: 当事人页渐进式校验与错误摘要 -------------------------------------


def test_p0_fresh_party_page_is_silent_and_blocks(qapp):
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()
    _click(wizard, qapp, _next(wizard))                     # welcome -> case selection
    select_case(wizard, "loan")
    qapp.processEvents()
    _click(wizard, qapp, _next(wizard))                     # -> party
    assert wizard.currentId() == wizard.PAGE_PARTY

    page = wizard.party_page
    # 首次进入：未触碰任何字段，不显示错误，且因当事人不完整而禁用下一步。
    assert page.msg_label.text() == ""
    assert not page.msg_label.isVisible()
    assert not _next(wizard).isEnabled()


def test_p0_error_revealed_after_edit_then_clears(qapp):
    wizard, _ = make_wizard()
    wizard.show()
    qapp.processEvents()
    _click(wizard, qapp, _next(wizard))                     # welcome -> case selection
    select_case(wizard, "loan")
    qapp.processEvents()
    _click(wizard, qapp, _next(wizard))                     # -> party
    page = wizard.party_page

    # 只有“离开”原告姓名字段后，渐进校验才第一次给出错误摘要。
    page.plaintiff_widgets[0]["name"].setText("原告甲（测试）")
    page.plaintiff_widgets[0]["name"].editingFinished.emit()
    qapp.processEvents()
    assert page._touched is True
    assert "被告" in page.msg_label.text()

    # 补齐被告后错误消失，下一步重新可用。
    page.defendant_widgets[0]["name"].setText("被告乙（测试）")
    page.defendant_widgets[0]["name"].editingFinished.emit()
    qapp.processEvents()
    assert page.msg_label.text() == ""
    assert _next(wizard).isEnabled()

    _click(wizard, qapp, _next(wizard))
    assert wizard.currentId() == wizard.PAGE_LOAN_CLAIM


# --- H: T06 物业 / 劳动 / 离婚表单分组、约束与常驻提示 -------------------


def _property_page(qapp):
    wizard, _ = make_wizard()
    return wizard.property_claim_page


def _labor_page(qapp):
    wizard, _ = make_wizard()
    return wizard.labor_claim_page


def _divorce_page(qapp):
    wizard, _ = make_wizard()
    return wizard.divorce_claim_page


def test_h_t06_property_form_is_grouped(qapp):
    titles = _group_titles(_property_page(qapp))
    for expected in ("物业与计费", "违约金与催缴", "金额核对", "管辖法院"):
        assert any(expected in t for t in titles), titles


def test_h_t06_property_amount_fields_constrained(qapp):
    page = _property_page(qapp)
    for field in (page.house_area, page.fee_rate, page.total_input):
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("115.5", 0)[0] == QValidator.State.Acceptable
        assert validator.validate("", 0)[0] == QValidator.State.Acceptable


def test_h_t06_property_calc_result_sits_in_amount_group(qapp):
    page = _property_page(qapp)
    groups = [g for g in page.findChildren(QGroupBox) if "金额核对" in g.title()]
    assert len(groups) == 1
    amount_group = groups[0]
    assert page.total_input.parent() is amount_group
    assert page.calc_label.parent() is amount_group


def test_h_t06_labor_form_is_grouped(qapp):
    titles = _group_titles(_labor_page(qapp))
    for expected in ("劳动关系", "欠薪与加班", "合同与社保", "管辖法院"):
        assert any(expected in t for t in titles), titles


def test_h_t06_labor_arbitration_notice_is_persistent(qapp):
    page = _labor_page(qapp)
    notice = page.arbitration_notice
    text = notice.text()
    assert text
    assert "仲裁前置" in text
    assert "依据" in text
    assert "整理时间" in text
    assert notice.objectName() == REMINDER_LABEL


def test_h_t06_labor_amount_fields_constrained(qapp):
    page = _labor_page(qapp)
    for field in (page.monthly_salary, page.overtime_hours, page.overtime_pay):
        validator = field.validator()
        assert validator is not None
        assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
        assert validator.validate("8000", 0)[0] == QValidator.State.Acceptable
        assert validator.validate("", 0)[0] == QValidator.State.Acceptable


def test_h_t06_divorce_form_is_grouped(qapp):
    titles = _group_titles(_divorce_page(qapp))
    for expected in ("婚姻与离婚原因", "子女与抚养", "财产分割", "管辖法院"):
        assert any(expected in t for t in titles), titles


def test_h_t06_divorce_child_help_explains_optional(qapp):
    page = _divorce_page(qapp)
    text = page.child_help.text()
    assert "无子女" in text
    assert "不填" in text


def test_h_t06_divorce_support_monthly_constrained(qapp):
    page = _divorce_page(qapp)
    validator = page.support_monthly.validator()
    assert validator is not None
    assert validator.validate("abc", 0)[0] == QValidator.State.Invalid
    assert validator.validate("3000", 0)[0] == QValidator.State.Acceptable
    assert validator.validate("", 0)[0] == QValidator.State.Acceptable
