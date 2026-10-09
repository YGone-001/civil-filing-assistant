# File: tests/test_security_status.py
# Purpose: Regression tests for advisory network status and best-effort cleanup.
# Encoding: UTF-8

import subprocess

import pytest

from models.case_model import LoanCaseModel, PartyInfo
from utils.security_check import NetworkStatus, SecurityGuard


def test_online_when_default_route_detected(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *a, **k: "0.0.0.0          0.0.0.0     192.168.1.1\n",
    )
    guard = SecurityGuard()
    assert guard.check_network_status() == NetworkStatus.ONLINE
    assert guard.is_offline is False


def test_offline_when_no_default_route(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *a, **k: "192.168.1.0    255.255.255.0    192.168.1.1\n",
    )
    guard = SecurityGuard()
    assert guard.check_network_status() == NetworkStatus.OFFLINE
    assert guard.is_offline is True


def test_unknown_when_check_fails(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")

    def _boom(*a, **k):
        raise FileNotFoundError("route command unavailable")

    monkeypatch.setattr(subprocess, "check_output", _boom)
    guard = SecurityGuard()
    status = guard.check_network_status()
    assert status == NetworkStatus.UNKNOWN
    # Unknown must never be reported as a verified offline state.
    assert guard.is_offline is False


def test_unknown_never_equals_offline():
    assert NetworkStatus.UNKNOWN != NetworkStatus.OFFLINE


def test_unix_default_route(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *a, **k: "default via 10.0.0.1 dev eth0\n",
    )
    assert SecurityGuard().check_network_status() == NetworkStatus.ONLINE


def test_wipe_memory_is_best_effort_but_clears_fields():
    model = LoanCaseModel()
    model.party_manager.add_party(
        0, PartyInfo("张三", "示例证件号", "示例地址", "示例电话")
    )
    model.principal_amount = "50000"
    model.loan_reason = "资金周转"

    SecurityGuard.wipe_memory(model)

    assert model.party_manager.plaintiffs[0].name != "张三"
    assert model.principal_amount == "0"
    assert model.loan_reason != "资金周转"
    assert model.evidences == []


def test_wipe_memory_handles_empty_model():
    # Must not raise on an unknown/empty object.
    SecurityGuard.wipe_memory(None)
    SecurityGuard.wipe_memory(LoanCaseModel())
