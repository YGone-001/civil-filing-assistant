# File: utils/batch_manager.py
# Purpose: Output directory, filename cleaning and robust batch export
# Encoding: UTF-8

import datetime
import os
import zipfile


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

        Documents are written to temporary ``*.part`` files and only published
        with their final names once every file has been generated and verified,
        so a failure never leaves a misleading partial set. Existing files are
        never overwritten; instead a numeric suffix is added.
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
        target_dir = os.path.join(base_path, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        prefix = f"{p_safe}_vs_{d_safe}_{stamp}"
        specs = [
            (self.generator.export_complaint, f"{prefix}_民事起诉状.docx"),
            (self.generator.export_evidence_list, f"{prefix}_证据清单.docx"),
            (self.generator.export_address_form, f"{prefix}_送达地址确认书.docx"),
        ]

        staged = []  # (temp_path, final_path)
        try:
            for export_fn, filename in specs:
                final_path = self._unique_path(target_dir, filename)
                temp_path = final_path + ".part"
                export_fn(model, temp_path)
                self._verify_docx(temp_path)
                staged.append((temp_path, final_path))

            published = []
            for temp_path, final_path in staged:
                os.replace(temp_path, final_path)
                published.append(final_path)
        except Exception:
            # Remove any half-written temp files so no partial set survives.
            for temp_path, _final_path in staged:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            raise

        return target_dir, published
