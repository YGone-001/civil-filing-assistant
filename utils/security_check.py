# File: utils/security_check.py
# Purpose: Advisory offline status check and best-effort in-process cleanup
# Encoding: UTF-8

import platform
import subprocess


class NetworkStatus:
    """Advisory network-route detection results.

    This is a lightweight hint, not a system-level isolation mechanism.
    """

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class SecurityGuard:
    def __init__(self):
        self.status = NetworkStatus.UNKNOWN
        self.is_offline = False

    def _set(self, status):
        self.status = status
        self.is_offline = (status == NetworkStatus.OFFLINE)
        return status

    @staticmethod
    def _has_default_route_windows(output):
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                return True
        return False

    @staticmethod
    def _has_default_route_unix(output):
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("default") or stripped.startswith("0.0.0.0"):
                return True
        return False

    def check_network_status(self):
        """Return an advisory :class:`NetworkStatus` for the default route.

        Only three honest outcomes are reported:

        * ``ONLINE``  - a default network route was detected.
        * ``OFFLINE`` - no default route was detected.
        * ``UNKNOWN`` - the check could not be completed (command missing,
          non-zero exit, or unexpected output).

        A failed check is reported as ``UNKNOWN`` and is never presented as a
        verified offline state.
        """
        try:
            if platform.system().lower() == "windows":
                output = subprocess.check_output(
                    ["route", "print", "0.0.0.0"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                if self._has_default_route_windows(output):
                    return self._set(NetworkStatus.ONLINE)
                return self._set(NetworkStatus.OFFLINE)

            output = subprocess.check_output(
                ["netstat", "-rn"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            if self._has_default_route_unix(output):
                return self._set(NetworkStatus.ONLINE)
            return self._set(NetworkStatus.OFFLINE)
        except Exception:
            return self._set(NetworkStatus.UNKNOWN)

    @staticmethod
    def wipe_memory(model):
        """Best-effort overwrite of sensitive model strings in this process.

        Python strings are immutable and may be interned or copied, so this
        does NOT guarantee that the original values are irreversibly erased
        from memory. It only shortens the time the current model object keeps
        the original strings, and it does not touch files already written to
        disk.
        """
        if not model:
            return

        # Wipe plaintiff
        if hasattr(model, 'party_manager'):
            for p in model.party_manager.plaintiffs:
                p.name = "X" * len(p.name) if p.name else ""
                p.id_number = "X" * len(p.id_number) if p.id_number else ""
                p.address = "X" * len(p.address) if p.address else ""
                p.phone = "X" * len(p.phone) if p.phone else ""
                if hasattr(p, 'legal_representative'):
                    p.legal_representative = "X" * len(p.legal_representative) if p.legal_representative else ""
                if hasattr(p, 'credit_code'):
                    p.credit_code = "X" * len(p.credit_code) if p.credit_code else ""

            for d in model.party_manager.defendants:
                d.name = "X" * len(d.name) if d.name else ""
                d.id_number = "X" * len(d.id_number) if d.id_number else ""
                d.address = "X" * len(d.address) if d.address else ""
                d.phone = "X" * len(d.phone) if d.phone else ""
                if hasattr(d, 'legal_representative'):
                    d.legal_representative = "X" * len(d.legal_representative) if d.legal_representative else ""
                if hasattr(d, 'credit_code'):
                    d.credit_code = "X" * len(d.credit_code) if d.credit_code else ""

        # Wipe claims
        if hasattr(model, 'principal_amount'):
            model.principal_amount = "0"
        if hasattr(model, 'interest_rate'):
            model.interest_rate = "0"
        if hasattr(model, 'interest_start_date'):
            model.interest_start_date = "X" * len(model.interest_start_date) if model.interest_start_date else ""
        if hasattr(model, 'payment_method'):
            model.payment_method = "X" * len(model.payment_method) if model.payment_method else ""
        if hasattr(model, 'collection_process'):
            model.collection_process = "X" * len(model.collection_process) if model.collection_process else ""
        if hasattr(model, 'court_name'):
            model.court_name = "X" * len(model.court_name) if model.court_name else ""

        for attr in [
            "loan_date",
            "loan_reason",
            "demand_date",
            "demand_method",
            "contract_date",
            "contract_name",
            "product_name",
            "total_amount",
            "delivery_date",
            "unpaid_amount",
            "penalty_amount",
            "penalty_start_date",
            "penalty_calc_standard",
            "liquidated_damages_formula",
            "property_addr",
            "house_area",
            "fee_rate",
            "period_start",
            "period_end",
            "late_fee_logic",
            "demand_record",
            "total_principal",
            "emp_join_date",
            "job_title",
            "monthly_salary",
            "unpaid_months",
            "emp_term_date",
            "overtime_hours",
            "overtime_pay",
            "social_sec_info",
            "marriage_date",
            "child_name",
            "child_birthday",
            "custody_preference",
            "support_monthly",
            "divorce_reason",
            "asset_description",
        ]:
            if hasattr(model, attr):
                v = getattr(model, attr)
                if isinstance(v, str):
                    setattr(model, attr, "X" * len(v) if v else "")
                else:
                    try:
                        setattr(model, attr, None)
                    except Exception:
                        pass

        if hasattr(model, "evidences") and isinstance(model.evidences, list):
            for ev in model.evidences:
                if hasattr(ev, "name") and isinstance(ev.name, str):
                    ev.name = "X" * len(ev.name) if ev.name else ""
                if hasattr(ev, "target") and isinstance(ev.target, str):
                    ev.target = "X" * len(ev.target) if ev.target else ""
            model.evidences.clear()
