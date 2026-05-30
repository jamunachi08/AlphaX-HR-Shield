"""Qiwa adapter — labor contracts, work permits, Saudization indicators.

Capabilities (wired once official credentials/endpoints are provided):
  * verify_contract(employee)   — confirm an authenticated Qiwa labor contract
  * work_permit_status(iqama)   — work-permit / Iqama validity for expats
  * establishment_nitaqat()     — pull the official Nitaqat band for the entity
"""
from __future__ import annotations

from .base import PortalAdapter, register


@register
class QiwaAdapter(PortalAdapter):
    portal = "qiwa"

    def test_connection(self) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("GET", "/ping")

    def verify_contract(self, employee_id: str) -> dict:
        self._require("base_url", "api_token")
        return self._request("GET", f"/contracts/{employee_id}")

    def work_permit_status(self, iqama_number: str) -> dict:
        self._require("base_url", "api_token")
        return self._request("GET", f"/work-permits/{iqama_number}")

    def establishment_nitaqat(self) -> dict:
        self._require("base_url", "establishment_id", "api_token")
        return self._request("GET", "/saudization/nitaqat")
