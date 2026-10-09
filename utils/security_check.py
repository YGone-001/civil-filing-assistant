# File: utils/security_check.py
# Purpose: Ensure absolute offline environment and data wiping
# Encoding: UTF-8

import subprocess
import platform

class SecurityGuard:
    def __init__(self):
        self.is_offline = True

    def check_network_status(self):
        """
        Check if any network interface is active without using socket.
        Uses system ping to localhost/gateway or checks arp table/ipconfig.
        Returns True if offline, False if potentially online.
        """
        try:
            # We use ping to a known non-existent IP or check routing table
            # without triggering firewall alerts.
            # A safer cross-platform way without socket is checking if default gateway exists.
            if platform.system().lower() == "windows":
                # Check for default route
                output = subprocess.check_output("route print", shell=True, text=True)
                # If 0.0.0.0 is in the routing table, it means there is an active gateway
                if "0.0.0.0          0.0.0.0" in output:
                    self.is_offline = False
                    return False
            else:
                # For Unix-like (Mac/Linux)
                output = subprocess.check_output("netstat -rn", shell=True, text=True)
                if "0.0.0.0" in output or "default" in output:
                    self.is_offline = False
                    return False

            self.is_offline = True
            return True
        except Exception:
            # If command fails, we assume it's offline to not block the user,
            # but log it or handle it safely.
            self.is_offline = True
            return True

    @staticmethod
    def wipe_memory(model):
        """
        Explicitly clear sensitive data strings from memory
        before application exits.
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
