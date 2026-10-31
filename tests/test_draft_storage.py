# File: tests/test_draft_storage.py
# Purpose: Encrypted envelope format, size bounds and atomic write behaviour.
# Encoding: UTF-8
"""Storage-layer tests.

The envelope is the only part of a draft file that is readable without the
Windows user's key, so it is validated exhaustively: magic, version, declared
length, exact total size, and the decrypted payload size. The write path is
tested for the two guarantees the feature depends on - an existing draft
survives a failed replacement, and no temporary artifact outlives a failure.
"""

import os

import pytest

import drafts.windows_protection as protection
from drafts import storage
from drafts.errors import (
    DraftFileTooLargeError,
    DraftFormatError,
    DraftStorageError,
    ProtectionUnavailable,
)


class _RecordingProtector:
    """A stand-in protector with a trailing checksum, so corruption is visible.

    It performs no encryption on purpose: the confidentiality property is
    asserted against the real DPAPI protector below, while this fake keeps the
    envelope/IO tests independent of the platform.
    """

    def __init__(self):
        self.protected = 0
        self.unprotected = 0

    def protect(self, data):
        self.protected += 1
        body = bytes(data)
        return b"FAKE" + body + bytes([sum(body) % 256])

    def unprotect(self, blob):
        self.unprotected += 1
        if len(blob) < 5 or not blob.startswith(b"FAKE"):
            raise DraftFormatError("测试保护器无法识别该密文。")
        body = blob[4:-1]
        if blob[-1] != sum(body) % 256:
            raise DraftFormatError("测试保护器校验失败。")
        return body


class _FailingProtector:
    def __init__(self):
        self.protect_calls = 0

    def protect(self, data):
        self.protect_calls += 1
        raise ProtectionUnavailable("当前环境不支持 Windows 用户级数据保护。")


def _temp_artifacts(directory):
    return [name for name in os.listdir(directory) if name.startswith(".cfadraft-")]


# --------------------------------------------------------------------------- #
# Envelope
# --------------------------------------------------------------------------- #


def test_envelope_header_layout_is_stable():
    envelope = storage.build_envelope(b"cipher")
    assert envelope[:8] == b"CFADRAFT"
    assert envelope[8] == 1
    assert envelope[9:13] == (6).to_bytes(4, "big")
    assert envelope[13:] == b"cipher"
    assert storage.HEADER_SIZE == 13


def test_parse_envelope_returns_the_ciphertext():
    assert storage.parse_envelope(storage.build_envelope(b"cipher")) == b"cipher"


def test_empty_ciphertext_is_rejected_when_building():
    with pytest.raises(DraftFormatError):
        storage.build_envelope(b"")


def test_unsupported_envelope_version_is_rejected():
    envelope = bytearray(storage.build_envelope(b"cipher"))
    envelope[8] = 9
    with pytest.raises(DraftFormatError) as excinfo:
        storage.parse_envelope(bytes(envelope))
    assert "版本" in str(excinfo.value)


def test_foreign_file_magic_is_rejected():
    with pytest.raises(DraftFormatError):
        storage.parse_envelope(b"NOTADRAFT" + b"\x00" * 8)


def test_truncated_header_is_rejected():
    with pytest.raises(DraftFormatError):
        storage.parse_envelope(b"CFADRA")


def test_truncated_body_is_rejected():
    envelope = storage.build_envelope(b"0123456789")
    with pytest.raises(DraftFormatError):
        storage.parse_envelope(envelope[:-1])


def test_trailing_bytes_are_rejected():
    envelope = storage.build_envelope(b"0123456789")
    with pytest.raises(DraftFormatError):
        storage.parse_envelope(envelope + b"\x00")


def test_zero_length_declaration_is_rejected():
    with pytest.raises(DraftFormatError):
        storage.parse_envelope(b"CFADRAFT\x01\x00\x00\x00\x00")


# --------------------------------------------------------------------------- #
# Round trip through the file system
# --------------------------------------------------------------------------- #


def test_save_then_load_returns_the_same_plaintext(tmp_path):
    path = tmp_path / "case.cfdraft"
    protector = _RecordingProtector()
    storage.save_draft_file(str(path), b'{"a":1}', protector=protector)
    assert storage.load_draft_file(str(path), protector=protector) == b'{"a":1}'
    assert protector.protected == 1
    assert protector.unprotected == 1


def test_saved_file_starts_with_the_magic(tmp_path):
    path = tmp_path / "case.cfdraft"
    storage.save_draft_file(str(path), b"body", protector=_RecordingProtector())
    assert path.read_bytes()[:8] == b"CFADRAFT"


def test_real_draft_file_contains_no_plaintext_markers(tmp_path):
    """End-to-end confidentiality: the bytes on disk never show case text."""
    protector = protection.get_default_protector()
    if not protector.available():
        pytest.skip("Windows DPAPI is not available in this environment")
    path = tmp_path / "case.cfdraft"
    marker = "机密姓名测试甲".encode("utf-8")
    storage.save_draft_file(str(path), b'{"name":"' + marker + b'"}', protector=protector)
    raw = path.read_bytes()
    assert raw[:8] == b"CFADRAFT"
    assert marker not in raw
    assert b'"name"' not in raw
    assert storage.load_draft_file(str(path), protector=protector) == b'{"name":"' + marker + b'"}'


def test_saving_leaves_no_temporary_artifact(tmp_path):
    storage.save_draft_file(str(tmp_path / "a.cfdraft"), b"x", protector=_RecordingProtector())
    assert _temp_artifacts(str(tmp_path)) == []
    assert sorted(os.listdir(tmp_path)) == ["a.cfdraft"]


def test_overwriting_replaces_the_file_in_place(tmp_path):
    path = tmp_path / "a.cfdraft"
    storage.save_draft_file(str(path), b"first", protector=_RecordingProtector())
    storage.save_draft_file(str(path), b"second", protector=_RecordingProtector())
    assert storage.load_draft_file(str(path), protector=_RecordingProtector()) == b"second"
    assert sorted(os.listdir(tmp_path)) == ["a.cfdraft"]


def test_oversized_plaintext_is_refused_before_writing(tmp_path):
    path = tmp_path / "a.cfdraft"
    with pytest.raises(DraftFileTooLargeError):
        storage.save_draft_file(
            str(path), b"x" * (storage.MAX_PLAINTEXT_BYTES + 1), protector=_RecordingProtector()
        )
    assert not path.exists()


def test_empty_plaintext_is_refused(tmp_path):
    with pytest.raises(DraftStorageError):
        storage.save_draft_file(
            str(tmp_path / "a.cfdraft"), b"", protector=_RecordingProtector()
        )


def test_missing_destination_directory_is_reported(tmp_path):
    with pytest.raises(DraftStorageError):
        storage.save_draft_file(
            str(tmp_path / "missing" / "a.cfdraft"), b"x", protector=_RecordingProtector()
        )


# --------------------------------------------------------------------------- #
# Failure behaviour
# --------------------------------------------------------------------------- #


def test_failed_protection_preserves_the_existing_draft(tmp_path):
    path = tmp_path / "a.cfdraft"
    storage.save_draft_file(str(path), b"original", protector=_RecordingProtector())
    before = path.read_bytes()

    failing = _FailingProtector()
    with pytest.raises(ProtectionUnavailable):
        storage.save_draft_file(str(path), b"replacement", protector=failing)

    assert path.read_bytes() == before
    assert failing.protect_calls == 1
    assert _temp_artifacts(str(tmp_path)) == []


def test_failed_replacement_leaves_no_temporary_artifact(tmp_path, monkeypatch):
    """Simulated: the final rename fails after the temporary file was written."""
    path = tmp_path / "a.cfdraft"
    storage.save_draft_file(str(path), b"original", protector=_RecordingProtector())
    before = path.read_bytes()

    def _broken_replace(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(storage.os, "replace", _broken_replace)
    with pytest.raises(DraftStorageError):
        storage.save_draft_file(str(path), b"replacement", protector=_RecordingProtector())

    assert path.read_bytes() == before
    assert _temp_artifacts(str(tmp_path)) == []


def test_failed_load_reports_a_readable_error(tmp_path):
    with pytest.raises(DraftStorageError):
        storage.load_draft_file(str(tmp_path / "absent.cfdraft"))


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.cfdraft"
    path.write_bytes(b"")
    with pytest.raises(DraftFormatError):
        storage.load_draft_file(str(path))


def test_oversized_file_is_rejected_without_reading_it_all(tmp_path):
    path = tmp_path / "big.cfdraft"
    path.write_bytes(b"CFADRAFT\x01" + b"\x00" * storage.MAX_FILE_BYTES)
    with pytest.raises(DraftFileTooLargeError):
        storage.load_draft_file(str(path))


def test_corrupted_body_fails_closed(tmp_path):
    path = tmp_path / "a.cfdraft"
    storage.save_draft_file(str(path), b"payload", protector=_RecordingProtector())
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 0xFF
    path.write_bytes(bytes(raw))
    with pytest.raises(DraftFormatError):
        storage.load_draft_file(str(path), protector=_RecordingProtector())


def test_load_does_not_trust_a_forged_length(tmp_path):
    path = tmp_path / "forged.cfdraft"
    path.write_bytes(b"CFADRAFT\x01" + (999).to_bytes(4, "big") + b"short")
    with pytest.raises(DraftFormatError):
        storage.load_draft_file(str(path), protector=_RecordingProtector())


def test_oversized_decrypted_payload_is_rejected(tmp_path):
    """A protector that inflates the payload must not bypass the bound."""

    class _InflatingProtector:
        def protect(self, data):
            return bytes(data)

        def unprotect(self, blob):
            return b"x" * (storage.MAX_PLAINTEXT_BYTES + 1)

    path = tmp_path / "inflated.cfdraft"
    storage.save_draft_file(str(path), b"x", protector=_InflatingProtector())
    with pytest.raises(DraftFileTooLargeError):
        storage.load_draft_file(str(path), protector=_InflatingProtector())


# --------------------------------------------------------------------------- #
# Layering and log hygiene
# --------------------------------------------------------------------------- #


def test_lower_draft_layers_do_not_import_qt():
    """Storage, schema and protection must stay widget-free."""
    from pathlib import Path

    import drafts.errors as errors_module
    import drafts.schema as schema_module
    import drafts.windows_protection as protection_module

    for module in (errors_module, schema_module, storage, protection_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "PySide6" not in source, module.__name__
        assert "import Qt" not in source, module.__name__


def test_draft_code_never_logs_or_prints_payload_content():
    """A draft must not leak case data into routine logs."""
    from pathlib import Path

    import drafts.schema as schema_module
    import drafts.windows_protection as protection_module
    import presenters.draft_presenter as presenter_module
    import views.draft_io as adapter_module

    for module in (schema_module, storage, protection_module, presenter_module, adapter_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "import logging" not in source, module.__name__
        assert "print(" not in source, module.__name__


def test_draft_modules_import_in_a_fresh_process():
    """The new package must import without a QApplication and without a wizard."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    modules = (
        "drafts",
        "drafts.errors",
        "drafts.schema",
        "drafts.storage",
        "drafts.windows_protection",
        "views.draft_io",
        "presenters.draft_presenter",
    )
    script = "import importlib\n" + "".join(
        f"importlib.import_module({name!r})\n" for name in modules
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
