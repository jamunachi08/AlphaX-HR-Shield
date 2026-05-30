"""GOSI adapter — verify reported wages and pull official contribution figures.

Capabilities (wired once official credentials/endpoints are provided):
  * reported_wage(employee)      — wage GOSI has on record (reconcile vs payroll)
  * contributions(employee)      — official monthly contribution figures
  * register_change(payload)     — push joiners/leavers/wage updates
"""
from __future__ import annotations

from .base import PortalAdapter, register


@register
class GOSIAdapter(PortalAdapter):
    portal = "gosi"

    def test_connection(self) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("GET", "/status")

    def reported_wage(self, employee_id: str) -> dict:
        self._require("base_url", "api_token")
        return self._request("GET", f"/employees/{employee_id}/wage")

    def contributions(self, employee_id: str) -> dict:
        self._require("base_url", "api_token")
        return self._request("GET", f"/employees/{employee_id}/contributions")

    def register_change(self, payload: dict) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("POST", "/employees/changes", json=payload)
