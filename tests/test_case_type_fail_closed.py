# File: tests/test_case_type_fail_closed.py
# Purpose: Unknown case types must fail closed everywhere (P1-02 / D-01).
# Encoding: UTF-8
"""Regression coverage for the supported-case registry.

An unknown, empty, missing or mistyped case identifier used to silently fall
back to a loan case in both model building and wizard routing. It must now
raise/fail closed instead, and the presenter must classify it as a validation
failure so no document for a wrong category can ever be exported.
"""

from types import SimpleNamespace

import pytest

from helpers import make_wizard, set_parties
from models.case_model import (
    ContractCaseModel,
    DivorceCaseModel,
    LaborCaseModel,
    LoanCaseModel,
    PropertyCaseModel,
)
from presenters.model_builder import (
    SUPPORTED_CASE_TYPES,
    UnsupportedCaseTypeError,
    _model_for,
    build_case_model,
    is_supported_case_type,
)


def _fake_view(case_type):
    return SimpleNamespace(
        field=lambda name: case_type if name == "case_type" else "",
        party_page=SimpleNamespace(get_party_data=lambda: {"plaintiffs": [], "defendants": []}),
        evidence_page=SimpleNamespace(get_evidence_items=lambda: []),
        loan_claim_page=SimpleNamespace(get_has_iou=lambda: None),
        contract_claim_page=SimpleNamespace(
            get_flags=lambda: {"is_delivered": None, "is_signed": None},
            get_penalty_calc_basis=lambda: None,
        ),
        labor_claim_page=SimpleNamespace(get_has_no_contract=lambda: False),
    )


def test_supported_registry_matches_five_case_types():
    assert SUPPORTED_CASE_TYPES == frozenset(
        {"loan", "contract", "property", "labor", "divorce"}
    )


@pytest.mark.parametrize(
    "case_type,cls",
    [
        ("loan", LoanCaseModel),
        ("contract", ContractCaseModel),
        ("property", PropertyCaseModel),
        ("labor", LaborCaseModel),
        ("divorce", DivorceCaseModel),
    ],
)
def test_valid_case_types_build_their_own_model(case_type, cls):
    assert isinstance(_model_for(case_type), cls)
    assert isinstance(build_case_model(_fake_view(case_type)), cls)


@pytest.mark.parametrize("bad", ["unknown", "", "LOAN", " loan", "loan ", None, 123, ["loan"], {"type": "loan"}])
def test_unknown_case_type_fails_closed_in_model_builder(bad):
    with pytest.raises(UnsupportedCaseTypeError):
        _model_for(bad)
    with pytest.raises(UnsupportedCaseTypeError):
        build_case_model(_fake_view(bad))


# --- C-02: every entry point must fail closed for unhashable values too -----

INVALID_CASE_TYPES = [None, "", "unknown", "LOAN", " loan", 123, ["loan"], {"type": "loan"}]


def test_supported_case_type_validator_accepts_exactly_five_identifiers():
    for valid in ("loan", "contract", "property", "labor", "divorce"):
        assert is_supported_case_type(valid) is True


@pytest.mark.parametrize("bad", INVALID_CASE_TYPES)
def test_supported_case_type_validator_rejects_without_raising(bad):
    assert is_supported_case_type(bad) is False


@pytest.mark.parametrize("bad", INVALID_CASE_TYPES)
def test_presenter_finish_fail_closed_for_every_invalid_type(
    qapp, monkeypatch, tmp_path, dialog_recorder, bad
):
    desktop = _redirect_desktop(monkeypatch, tmp_path)
    wizard, presenter = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name, _v=bad: _v if name == "case_type" else ""
    )
    set_parties(wizard)

    result = presenter.attempt_finish()  # must not raise (incl. unhashable)

    assert result == presenter.FINISH_VALIDATION_FAILED
    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))
    assert not wizard.result(), "the wizard must not close as if export succeeded"


@pytest.mark.parametrize("bad", INVALID_CASE_TYPES)
def test_wizard_routing_fail_closed_for_every_invalid_type(qapp, monkeypatch, bad):
    wizard, _ = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name, _v=bad: _v if name == "case_type" else ""
    )
    wizard.restart()
    wizard.next()  # welcome -> case selection
    wizard.next()  # -> party
    set_parties(wizard)

    target = wizard.nextId()  # must not raise (incl. unhashable)

    assert target == wizard.PAGE_CASE_SELECTION
    assert target not in (
        wizard.PAGE_LOAN_CLAIM,
        wizard.PAGE_CONTRACT_CLAIM,
        wizard.PAGE_PROPERTY_CLAIM,
        wizard.PAGE_LABOR_CLAIM,
        wizard.PAGE_DIVORCE_CLAIM,
    )


@pytest.mark.parametrize("bad", INVALID_CASE_TYPES)
def test_preview_fail_closed_for_every_invalid_type(qapp, monkeypatch, dialog_recorder, bad):
    wizard, _ = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name, _v=bad: _v if name == "case_type" else ""
    )

    wizard.export_page.show_preview()  # must not raise (incl. unhashable)

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not any(entry["kind"] == "critical" for entry in dialog_recorder)


def test_wizard_routing_never_reaches_a_claim_page_for_unknown_type(qapp, monkeypatch):
    """Routing must bounce an unknown identifier back to case selection."""
    wizard, _ = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name: "unknown" if name == "case_type" else ""
    )
    wizard.restart()
    wizard.next()  # welcome -> case selection
    assert wizard.nextId() == wizard.PAGE_PARTY
    wizard.next()  # -> party
    set_parties(wizard)  # satisfy party validation so navigation itself proceeds
    # The unknown identifier must never route to any claim page; the only
    # nextId() target is the case-selection page the user already visited.
    assert wizard.nextId() == wizard.PAGE_CASE_SELECTION
    wizard.next()  # Qt refuses to re-enter a visited page; the wizard stays put
    assert wizard.currentId() == wizard.PAGE_PARTY


def _redirect_desktop(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("os.path.expanduser", lambda *a, **k: str(home))
    return home / "Desktop"


def test_finish_with_unknown_case_type_is_a_validation_failure(
    qapp, monkeypatch, tmp_path, dialog_recorder
):
    desktop = _redirect_desktop(monkeypatch, tmp_path)
    wizard, presenter = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name: "unknown" if name == "case_type" else ""
    )
    set_parties(wizard)

    result = presenter.attempt_finish()

    assert result == presenter.FINISH_VALIDATION_FAILED
    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not (desktop.exists() and list(desktop.rglob("*.docx")))
    assert wizard.isVisible() or not wizard.result(), "wizard must stay usable"


def test_preview_with_unknown_case_type_recovers(qapp, monkeypatch, dialog_recorder):
    wizard, _ = make_wizard()
    monkeypatch.setattr(
        wizard, "field", lambda name: "unknown" if name == "case_type" else ""
    )

    wizard.export_page.show_preview()  # must not raise

    assert any(entry["kind"] == "warning" for entry in dialog_recorder)
    assert not any(entry["kind"] == "critical" for entry in dialog_recorder)
