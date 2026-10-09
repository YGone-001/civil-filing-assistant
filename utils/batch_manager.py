import os
import datetime


class BatchExportManager:
    def __init__(self, generator):
        self.generator = generator

    def _sanitize_component(self, s):
        text = (s or "").strip()
        if not text:
            return "Unknown"
        bad = '\\/:*?"<>|'
        for ch in bad:
            text = text.replace(ch, "_")
        return text

    def run_batch_export(self, model, base_path):
        p_name = "Plaintiff"
        d_name = "Defendant"
        if getattr(model, "party_manager", None):
            if model.party_manager.plaintiffs:
                p_name = model.party_manager.plaintiffs[0].name or p_name
            if model.party_manager.defendants:
                d_name = model.party_manager.defendants[0].name or d_name

        date_str = datetime.datetime.now().strftime('%Y%m%d')
        datetime_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        folder_name = f"{self._sanitize_component(p_name)}_vs_{self._sanitize_component(d_name)}_{date_str}"
        target_dir = os.path.join(base_path, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        complaint_path = os.path.join(target_dir, f"{self._sanitize_component(p_name)}_vs_{self._sanitize_component(d_name)}_{datetime_str}_民事起诉状.docx")
        evidence_path = os.path.join(target_dir, f"{self._sanitize_component(p_name)}_vs_{self._sanitize_component(d_name)}_{datetime_str}_证据清单.docx")
        address_path = os.path.join(target_dir, f"{self._sanitize_component(p_name)}_vs_{self._sanitize_component(d_name)}_{datetime_str}_送达地址确认书.docx")

        self.generator.export_complaint(model, complaint_path)
        self.generator.export_evidence_list(model, evidence_path)
        self.generator.export_address_form(model, address_path)

        return target_dir
