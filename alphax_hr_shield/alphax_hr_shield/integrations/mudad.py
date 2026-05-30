"""Mudad adapter — Wage Protection System (WPS) file submission & payroll.

Capabilities (wired once official credentials/endpoints are provided):
  * generate_wps_file(month) — build the WPS payload from local payroll
  * submit_wps(payload)      — push it to Mudad
  * payment_status(ref)      — poll WPS payment/processing status
"""
from __future__ import annotations

from .base import PortalAdapter, register, NotConfigured


@register
class MudadAdapter(PortalAdapter):
    portal = "mudad"

    def test_connection(self) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("GET", "/health")

    def generate_wps_file(self, salary_rows: list) -> dict:
        """Build a WPS-shaped payload from already-computed salary rows.
        Pure transformation — safe to run without credentials so you can preview."""
        total = sum(float(r.get("net_pay", 0)) for r in salary_rows)
        return {
            "establishment_id": self.conn.get("establishment_id"),
            "record_count": len(salary_rows),
            "total_amount": round(total, 2),
            "records": [
                {
                    "iban": r.get("iban"),
                    "employee_id": r.get("employee_id"),
                    "basic": r.get("basic"),
                    "housing": r.get("housing"),
                    "allowances": r.get("allowances"),
                    "deductions": r.get("deductions"),
                    "net_pay": r.get("net_pay"),
                }
                for r in salary_rows
            ],
        }

    def submit_wps(self, payload: dict) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("POST", "/wps/submit", json=payload)

    def payment_status(self, reference: str) -> dict:
        self._require("base_url", "api_token")
        return self._request("GET", f"/wps/status/{reference}")
