# File: tests/test_draft_crypto.py
# Purpose: Windows DPAPI binding behaviour and fail-closed protection.
# Encoding: UTF-8
"""Confidentiality tests for the only encryption primitive in the product.

The binding is exercised against the real ``crypt32`` on Windows (the project's
only supported desktop target). Failure paths that cannot be produced on a
healthy developer machine - a different Windows user, a broken profile, a
refused native call - are driven with controlled fakes and are labelled as
simulated in the test names, never reported as a real cross-user verification.
"""

import os

import pytest

import drafts.windows_protection as protection
from drafts.errors import ProtectionFailed, ProtectionUnavailable


class _FakeFunction:
    """A Win32 entry point stub that returns a fixed BOOL result."""

    def __init__(self, result):
        self.result = result
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        return self.result


class _FakeCrypt32:
    def __init__(self, result):
        self.CryptProtectData = _FakeFunction(result)
        self.CryptUnprotectData = _FakeFunction(result)


class _FakeKernel32:
    def __init__(self):
        self.freed = 0

    def LocalFree(self, *_args):
        self.freed += 1
        return 0


def _forced_protector(result):
    """Return a protector whose native calls always return *result*."""
    dpapi = protection.WindowsDpapi()
    dpapi._crypt32 = _FakeCrypt32(result)
    dpapi._kernel32 = _FakeKernel32()
    dpapi._load_attempted = True
    return dpapi


def _require_windows_dpapi():
    if not protection.get_default_protector().available():
        pytest.skip("Windows DPAPI is not available in this environment")


# --------------------------------------------------------------------------- #
# Real round trip
# --------------------------------------------------------------------------- #


def test_protect_and_unprotect_round_trip():
    _require_windows_dpapi()
    payload = "草稿内容：原告甲（测试）".encode("utf-8")
    blob = protection.get_default_protector().protect(payload)
    assert protection.get_default_protector().unprotect(blob) == payload


def test_protection_uses_the_documented_dpapi_blob_signature():
    _require_windows_dpapi()
    blob = protection.get_default_protector().protect(b"x")
    # 0x01 0x00 0x00 0x00 followed by the "DAPI" magic: the documented
    # CRYPTPROTECT_PROMPT / DPAPI blob header, i.e. this really is DPAPI and
    # not a homegrown cipher.
    assert blob[:4] == b"\x01\x00\x00\x00"
    assert blob[4:8] == b"\xd0\x8c\x9d\xdf"


def test_ciphertext_does_not_contain_the_plaintext():
    _require_windows_dpapi()
    marker = b"PLAINTEXT-MARKER-0123456789"
    blob = protection.get_default_protector().protect(b"prefix" + marker + b"suffix")
    assert marker not in blob


def test_protection_is_not_deterministic():
    """DPAPI salts each blob, so equal payloads must not produce equal bytes."""
    _require_windows_dpapi()
    first = protection.get_default_protector().protect(b"same payload")
    second = protection.get_default_protector().protect(b"same payload")
    assert first != second


# --------------------------------------------------------------------------- #
# Failure injection
# --------------------------------------------------------------------------- #


def test_corrupted_ciphertext_is_rejected():
    _require_windows_dpapi()
    blob = bytearray(protection.get_default_protector().protect(b"payload"))
    blob[len(blob) // 2] ^= 0xFF
    with pytest.raises(ProtectionFailed):
        protection.get_default_protector().unprotect(bytes(blob))


def test_truncated_ciphertext_is_rejected():
    _require_windows_dpapi()
    blob = protection.get_default_protector().protect(b"payload")
    with pytest.raises(ProtectionFailed):
        protection.get_default_protector().unprotect(blob[: len(blob) // 2])


def test_arbitrary_bytes_are_not_accepted_as_a_blob():
    _require_windows_dpapi()
    with pytest.raises(ProtectionFailed):
        protection.get_default_protector().unprotect(b"\x00" * 64)


def test_different_entropy_cannot_decrypt_a_blob(monkeypatch):
    """The application-domain entropy really participates in the protection."""
    _require_windows_dpapi()
    blob = protection.get_default_protector().protect(b"payload")
    monkeypatch.setattr(protection, "_PROTECTION_ENTROPY", b"another-domain/v1")
    with pytest.raises(ProtectionFailed):
        protection.WindowsDpapi().unprotect(blob)


def test_empty_payload_is_refused():
    with pytest.raises(ProtectionFailed):
        protection.get_default_protector().protect(b"")


def test_oversized_payload_is_refused_before_the_native_call():
    with pytest.raises(ProtectionFailed):
        protection.get_default_protector().protect(
            b"x" * (protection.MAX_PROTECTED_INPUT + 1)
        )


def test_unsupported_platform_fails_closed(monkeypatch):
    """A non-Windows platform must refuse, never fall back to plaintext."""
    monkeypatch.setattr(os, "name", "posix")
    dpapi = protection.WindowsDpapi()
    with pytest.raises(ProtectionUnavailable):
        dpapi.protect(b"payload")
    with pytest.raises(ProtectionUnavailable):
        dpapi.unprotect(b"payload")


def test_unavailable_platform_is_reported_by_available(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert protection.WindowsDpapi().available() is False


def test_refused_native_encrypt_call_raises_protection_failed():
    """Simulated: DPAPI returns FALSE (e.g. an unusable user profile)."""
    dpapi = _forced_protector(0)
    with pytest.raises(ProtectionFailed):
        dpapi.protect(b"payload")
    assert dpapi._crypt32.CryptProtectData.calls == 1


def test_refused_native_decrypt_call_raises_protection_failed():
    """Simulated: decryption is refused (e.g. a blob from another user)."""
    dpapi = _forced_protector(0)
    with pytest.raises(ProtectionFailed):
        dpapi.unprotect(b"payload")
    assert dpapi._crypt32.CryptUnprotectData.calls == 1


def test_failed_native_call_never_returns_plaintext():
    dpapi = _forced_protector(0)
    with pytest.raises(ProtectionFailed) as excinfo:
        dpapi.unprotect(b"payload")
    assert "payload" not in str(excinfo.value)


def test_protection_error_messages_never_echo_payload_content():
    _require_windows_dpapi()
    secret = b"SECRET-NAME-0123456789"
    blob = bytearray(protection.get_default_protector().protect(secret))
    blob[-1] ^= 0xFF
    with pytest.raises(ProtectionFailed) as excinfo:
        protection.get_default_protector().unprotect(bytes(blob))
    assert secret.decode() not in str(excinfo.value)
