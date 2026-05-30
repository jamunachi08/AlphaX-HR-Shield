"""Government portal integration framework.

This is a pluggable adapter layer. Each portal (Mudad / Qiwa / GOSI) gets an
adapter that reads its credentials and base URL from an "AlphaX Gov Connection"
record and talks to the portal's official API.

IMPORTANT — these portals are not open public APIs. Live connectivity requires
official onboarding and credentials issued by the relevant authority (Takamol
for Qiwa, the wage-protection operator for Mudad, GOSI for social insurance).
Until those are configured, calls raise NotConfigured so nothing fails silently
or pretends to have synced.
"""
from __future__ import annotations

from typing import Optional


class NotConfigured(Exception):
    """Raised when a portal connection is missing credentials or an endpoint."""


class PortalAdapter:
    portal = "base"

    def __init__(self, connection: dict):
        self.conn = connection or {}
        self.base_url = (self.conn.get("base_url") or "").rstrip("/")
        self.environment = self.conn.get("environment") or "sandbox"

    # --- helpers -----------------------------------------------------------
    def _require(self, *keys: str):
        missing = [k for k in keys if not self.conn.get(k)]
        if missing:
            raise NotConfigured(
                f"{self.portal}: configure {', '.join(missing)} on the "
                f"AlphaX Gov Connection record before syncing."
            )

    def _request(self, method: str, path: str, **kwargs):
        """Thin HTTP wrapper. Used once an official endpoint + token exist."""
        self._require("base_url")
        import requests
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        token = self.conn.get("api_token")
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # --- capabilities (override per portal) --------------------------------
    def test_connection(self) -> dict:
        raise NotConfigured(f"{self.portal}: no live endpoint configured yet.")


REGISTRY = {}


def register(cls):
    REGISTRY[cls.portal] = cls
    return cls


def get_adapter(portal: str, connection: dict) -> PortalAdapter:
    cls = REGISTRY.get(portal)
    if not cls:
        raise NotConfigured(f"No adapter registered for portal '{portal}'.")
    return cls(connection)
