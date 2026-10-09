# File: tests/test_evidence_export_utils.py
# Purpose: Tests for filename safety, docx verification, and evidence lists.
# Encoding: UTF-8

import zipfile

import pytest

from utils.batch_manager import BatchExportManager
from utils.evidence_library import EvidenceLibrary


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('a/b\\c:d*e?f"g<h>i|j', "a_b_c_d_e_f_g_h_i_j"),
        ("带\n换行\t制表", "带_换行_制表"),
        ("trailing...", "trailing"),
        ("  spaces  ", "spaces"),
        ("", "Unknown"),
        ("   ", "Unknown"),
        ("...", "Unknown"),
    ],
)
def test_sanitize_component(raw, expected):
    assert BatchExportManager._sanitize_component(raw) == expected


def test_sanitize_component_truncates_to_80():
    assert len(BatchExportManager._sanitize_component("x" * 200)) == 80


def test_unique_path_avoids_overwrite(tmp_path):
    original = tmp_path / "complaint.docx"
    original.write_text("existing", encoding="utf-8")

    candidate = BatchExportManager._unique_path(str(tmp_path), "complaint.docx")
    assert candidate != str(original)
    assert candidate.endswith("complaint_1.docx")


def test_verify_docx_rejects_missing_file(tmp_path):
    with pytest.raises(IOError):
        BatchExportManager._verify_docx(str(tmp_path / "missing.docx"))


def test_verify_docx_rejects_non_zip(tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_text("not a zip", encoding="utf-8")
    with pytest.raises(IOError):
        BatchExportManager._verify_docx(str(bad))


def test_verify_docx_rejects_zip_without_document_xml(tmp_path):
    bad = tmp_path / "empty.docx"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("hello.txt", "nothing useful")
    with pytest.raises(IOError):
        BatchExportManager._verify_docx(str(bad))


@pytest.mark.parametrize("case_type", ["loan", "contract", "property", "labor", "divorce"])
def test_evidence_library_returns_pairs(case_type):
    items = EvidenceLibrary.get_default_evidence(case_type)
    assert len(items) >= 1
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in items)
    assert all(pair[0].strip() for pair in items)


def test_evidence_library_unknown_case_type_is_empty_or_safe():
    items = EvidenceLibrary.get_default_evidence("does-not-exist")
    assert isinstance(items, list)
