# File: tests/test_transactional_export.py
# Purpose: Failure-injection tests for the transactional three-document export.
# Encoding: UTF-8
"""Verify that a three-document export is staged and published atomically.

A single completed export directory is built inside a private temporary
directory on the destination filesystem and only published with one
same-filesystem rename. These tests inject failures at every step and assert
that no partial, corrupt, or abandoned output survives.
"""

import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import utils.batch_manager as bm
from utils.batch_manager import BatchExportManager


def _write_docx(path):
    """Write a genuine, well-formed .docx package."""
    from docx import Document

    Document().save(str(path))


def _make_model():
    plaintiff = SimpleNamespace(name="原告甲（测试）")
    defendant = SimpleNamespace(name="被告乙（测试）")
    return SimpleNamespace(
        party_manager=SimpleNamespace(plaintiffs=[plaintiff], defendants=[defendant])
    )


def _generator():
    """A generator whose three exports each write a real .docx by default."""
    gen = SimpleNamespace()

    def ok(model, path):
        _write_docx(path)

    gen.export_complaint = ok
    gen.export_evidence_list = ok
    gen.export_address_form = ok
    return gen


def _no_staging_left(tmp_path):
    assert not any(p.name.startswith(".cfa_staging_") for p in tmp_path.iterdir())


def test_first_document_failure_leaves_nothing(tmp_path):
    gen = _generator()

    def fail(model, path):
        raise RuntimeError("起诉状生成失败")

    gen.export_complaint = fail

    with pytest.raises(RuntimeError):
        BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_second_document_failure_leaves_nothing(tmp_path):
    gen = _generator()

    def fail(model, path):
        raise RuntimeError("证据清单生成失败")

    gen.export_evidence_list = fail

    with pytest.raises(RuntimeError):
        BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_third_document_failure_leaves_nothing(tmp_path):
    gen = _generator()

    def fail(model, path):
        raise RuntimeError("送达地址确认书生成失败")

    gen.export_address_form = fail

    with pytest.raises(RuntimeError):
        BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_partial_set_cleaned_when_later_document_fails(tmp_path):
    """Documents already written to staging must not survive a later failure."""
    gen = _generator()

    def fail(model, path):
        _write_docx(path)  # this one writes fine
        # leave the other stages untouched so the failure is on the last one

    def fail_address(model, path):
        raise RuntimeError("最后一个文件写入失败")

    gen.export_address_form = fail_address

    with pytest.raises(RuntimeError):
        BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    # The earlier documents were written but must be discarded with the staging dir.
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_corrupt_docx_is_detected_and_cleaned(tmp_path):
    gen = _generator()

    def corrupt(model, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not a real docx package")

    gen.export_evidence_list = corrupt

    with pytest.raises(IOError):
        BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_final_publish_failure_cleans_staging(tmp_path, monkeypatch):
    def boom(src, dst):
        raise OSError("模拟发布目录失败")

    monkeypatch.setattr(bm, "_rename_dir", boom)
    gen = _generator()

    with pytest.raises(OSError):
        bm.BatchExportManager(gen).run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)


def test_existing_output_preserved_and_not_overwritten(tmp_path):
    gen = _generator()
    manager = BatchExportManager(gen)

    first_dir, first_files = manager.run_batch_export(_make_model(), str(tmp_path))
    second_dir, second_files = manager.run_batch_export(_make_model(), str(tmp_path))

    assert first_dir != second_dir
    assert os.path.isdir(first_dir) and os.path.isdir(second_dir)
    assert len(first_files) == 3 and len(second_files) == 3
    # Nothing was overwritten: both complete sets coexist.
    assert len(list(tmp_path.rglob("*.docx"))) == 6


def test_retry_after_failure_produces_complete_set(tmp_path):
    gen = _generator()
    calls = {"n": 0}

    def flaky(model, path):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("首次失败")
        _write_docx(path)

    gen.export_complaint = flaky
    manager = BatchExportManager(gen)

    with pytest.raises(RuntimeError):
        manager.run_batch_export(_make_model(), str(tmp_path))
    assert list(tmp_path.rglob("*.docx")) == []
    _no_staging_left(tmp_path)

    target_dir, files = manager.run_batch_export(_make_model(), str(tmp_path))
    assert len(files) == 3
    assert len(list(tmp_path.rglob("*.docx"))) == 3


# --- C3: true partial-byte-write failure injection -------------------------


PARTIAL_WRITE_GENERATORS = [
    "export_complaint",
    "export_evidence_list",
    "export_address_form",
]


def _assert_valid_docx(path):
    path = Path(path)
    assert path.exists(), f"missing document: {path}"
    assert zipfile.is_zipfile(path), f"not a valid docx package: {path}"
    with zipfile.ZipFile(path) as archive:
        assert "word/document.xml" in archive.namelist(), f"missing document.xml: {path}"
        assert archive.testzip() is None, f"corrupt docx package: {path}"


def _published_dirs(base):
    """Completed case directories (excluding private staging directories)."""
    return sorted(
        p for p in Path(base).iterdir()
        if p.is_dir() and not p.name.startswith(".cfa_staging_")
    )


@pytest.mark.parametrize("failing_attr", PARTIAL_WRITE_GENERATORS)
def test_partial_write_then_raise_is_rolled_back(tmp_path, failing_attr):
    """A generator that writes partial bytes to its destination and then raises
    must not leave a partial document, a published case directory or staging."""
    gen = _generator()
    manager = BatchExportManager(gen)

    # A previously completed export must survive the later failed transaction.
    first_dir, first_files = manager.run_batch_export(_make_model(), str(tmp_path))
    assert len(first_files) == 3
    assert len(_published_dirs(tmp_path)) == 1

    def partial_then_fail(model, path):
        with open(path, "wb") as stream:
            stream.write(b"partial document bytes")  # bytes really hit the disk
        raise OSError("simulated interrupted document write")

    setattr(gen, failing_attr, partial_then_fail)

    with pytest.raises(OSError):
        manager.run_batch_export(_make_model(), str(tmp_path))

    # 1. The original exception propagated (asserted by pytest.raises above).
    # 2. No new case directory was published.
    assert len(_published_dirs(tmp_path)) == 1
    # 3. No final DOCX is visible beyond the earlier completed export.
    docs_after = sorted(tmp_path.rglob("*.docx"))
    assert len(docs_after) == 3, [str(d) for d in docs_after]
    assert sorted(str(d) for d in docs_after) == sorted(str(Path(f)) for f in first_files)
    # 4/5. The partially written file was removed together with the staging dir.
    _no_staging_left(tmp_path)

    # 8/9. A subsequent healthy export produces exactly three valid documents.
    healthy = _generator()
    retry_dir, retry_files = BatchExportManager(healthy).run_batch_export(_make_model(), str(tmp_path))
    assert retry_dir != first_dir
    assert len(retry_files) == 3
    for f in retry_files:
        _assert_valid_docx(f)
    assert len(list(tmp_path.rglob("*.docx"))) == 6
    assert len(_published_dirs(tmp_path)) == 2
