# File: utils/batch_manager.py
# Purpose: Output directory, filename cleaning and robust batch export
# Encoding: UTF-8

import datetime
import os
import shutil
import tempfile
import uuid
import zipfile


def _rename_dir(src, dst):
    """Publish a fully built export directory with a single same-filesystem rename."""
    os.rename(src, dst)


class BatchExportManager:
    def __init__(self, generator):
        self.generator = generator

    @staticmethod
    def _sanitize_component(s):
        """Return a filesystem-safe name component for a party name."""
        text = (s or "").strip()
        if not text:
            return "Unknown"
        for ch in '\\/:*?"<>|\r\n\t':
            text = text.replace(ch, "_")
        # Windows rejects trailing dots/spaces and very long names.
        text = text.strip(" .")
        if not text:
            return "Unknown"
        return text[:80]

    @staticmethod
    def _unique_path(directory, filename):
        """Return a path that does not overwrite an existing file."""
        base, ext = os.path.splitext(filename)
        candidate = os.path.join(directory, filename)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(directory, f"{base}_{counter}{ext}")
            counter += 1
        return candidate

    @staticmethod
    def _verify_docx(path):
        """Raise if *path* is missing or is not a usable .docx package."""
        if not os.path.exists(path):
            raise IOError(f"未生成文件：{path}")
        if not zipfile.is_zipfile(path):
            raise IOError(f"生成的文件不是有效的 docx 包：{path}")
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                raise IOError(f"docx 包缺少 word/document.xml：{path}")
            broken = archive.testzip()
            if broken is not None:
                raise IOError(f"docx 包损坏（条目 {broken}）：{path}")

    def run_batch_export(self, model, base_path):
        """Generate the three documents and return ``(target_dir, files)``.

        The whole set is built inside a private temporary directory located on
        the *target* filesystem, and only published with a single same-filesystem
        directory rename once every file has been generated and verified. A
        failure therefore can never leave a partial or abandoned ``.part``
        file, and existing completed exports are never overwritten: the final
        case directory receives a numeric suffix when a collision would occur.
        """
        p_name = "Plaintiff"
        d_name = "Defendant"
        if getattr(model, "party_manager", None):
            if model.party_manager.plaintiffs:
                p_name = model.party_manager.plaintiffs[0].name or p_name
            if model.party_manager.defendants:
                d_name = model.party_manager.defendants[0].name or d_name

        p_safe = self._sanitize_component(p_name)
        d_safe = self._sanitize_component(d_name)

        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d")
        stamp = now.strftime("%Y%m%d_%H%M%S")

        folder_name = f"{p_safe}_vs_{d_safe}_{date_str}"
        os.makedirs(base_path, exist_ok=True)

        # Resolve a unique final directory up front; a numeric suffix is used
        # only when a previous export already occupies the name.
        target_dir = self._unique_path(base_path, folder_name)

        prefix = f"{p_safe}_vs_{d_safe}_{stamp}"
        specs = [
            (self.generator.export_complaint, f"{prefix}_民事起诉状.docx"),
            (self.generator.export_evidence_list, f"{prefix}_证据清单.docx"),
            (self.generator.export_address_form, f"{prefix}_送达地址确认书.docx"),
        ]
        filenames = [filename for _export_fn, filename in specs]

        # Stage in a private directory on the destination filesystem so the
        # final publish is a single atomic rename, not three separate ones.
        staging_dir = tempfile.mkdtemp(
            prefix=".cfa_staging_", suffix=f"_{uuid.uuid4().hex[:8]}", dir=base_path
        )
        try:
            for export_fn, filename in specs:
                path = os.path.join(staging_dir, filename)
                export_fn(model, path)
                self._verify_docx(path)
            _rename_dir(staging_dir, target_dir)
        except Exception:
            # Discard every partially built file; no incomplete set survives.
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

        files = [os.path.join(target_dir, name) for name in filenames]
        return target_dir, files
