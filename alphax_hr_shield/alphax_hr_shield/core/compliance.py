"""Core compliance logic — ported from artifacts/api-server/src/lib/compliance.ts.

Pure functions: expiry status, days-to-expiry, per-doc thresholds, risk score,
and nationality normalization. No Frappe imports here so it stays unit-testable.
"""
from __future__ import annotations

import datetime
from typing import Optional

DOC_TYPES = [
    {"doc_type": "national_id", "label": "National ID / Iqama", "icon": "id-card"},
    {"doc_type": "passport", "label": "Passport", "icon": "passport"},
    {"doc_type": "health_insurance", "label": "Health Insurance", "icon": "heart-pulse"},
    {"doc_type": "custom_identity", "label": "Custom Identity", "icon": "file-badge"},
    {"doc_type": "driving_license", "label": "Driving License", "icon": "car"},
]

ExpiryStatus = str  # "expired" | "critical" | "warning" | "ok" | "missing"


def _to_date(value) -> Optional[datetime.date]:
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def get_days_until_expiry(expiry) -> int:
    d = _to_date(expiry)
    if d is None:
        return -9999
    return (d - datetime.date.today()).days


def get_expiry_status(expiry, threshold_days: int) -> ExpiryStatus:
    d = _to_date(expiry)
    if d is None:
        return "missing"
    days = get_days_until_expiry(d)
    if days < 0:
        return "expired"
    if days <= 30:
        return "critical"
    if days <= threshold_days:
        return "warning"
    return "ok"


def get_doc_threshold(doc_type: str, thresholds: dict) -> int:
    """thresholds: {"global_days": int, "by_type": {doc_type: days}}."""
    by_type = thresholds.get("by_type") or {}
    return by_type.get(doc_type) or thresholds.get("global_days") or 90


def compute_risk_score(emp: dict, thresholds: dict) -> int:
    docs = [
        ("national_id", emp.get("national_id_expiry")),
        ("passport", emp.get("passport_expiry")),
        ("health_insurance", emp.get("health_insurance_expiry")),
        ("custom_identity", emp.get("custom_identity_expiry")),
    ]
    scores = {"expired": 100, "critical": 75, "warning": 40, "ok": 0, "missing": 20}
    total = sum(scores[get_expiry_status(e, get_doc_threshold(dt, thresholds))] for dt, e in docs)
    return round(total / len(docs)) if docs else 0


_NAT_MAP = {
    # Saudi
    "saudi": "Saudi", "saudi arabia": "Saudi", "saudi arabian": "Saudi",
    "سعودي": "Saudi", "سعودية": "Saudi", "سعودي الجنسية": "Saudi",
    # Egyptian
    "egypt": "Egyptian", "egyptian": "Egyptian", "مصري": "Egyptian", "مصرية": "Egyptian",
    # Indian
    "india": "Indian", "indian": "Indian", "هندي": "Indian", "هندية": "Indian",
    # Bangladeshi
    "bangladesh": "Bangladeshi", "bangladeshi": "Bangladeshi", "bengali": "Bangladeshi",
    "بنجلاديشي": "Bangladeshi", "بنغلاديشي": "Bangladeshi", "بنجلاديش": "Bangladeshi",
    # Nepali
    "nepal": "Nepali", "nepali": "Nepali", "nepalese": "Nepali",
    "نيبالي": "Nepali", "نيبالية": "Nepali",
    # Pakistani
    "pakistan": "Pakistani", "pakistani": "Pakistani", "باكستاني": "Pakistani", "باكستانية": "Pakistani",
    # Yemeni
    "yemen": "Yemeni", "yemeni": "Yemeni", "يمني": "Yemeni", "يمنية": "Yemeni",
    # Filipino
    "philippines": "Filipino", "filipino": "Filipino", "فلبيني": "Filipino", "فلبينية": "Filipino",
    # others
    "djibouti": "Djiboutian", "djiboutian": "Djiboutian",
}

# Display labels (Arabic) keyed by canonical nationality, for RTL reports.
NATIONALITY_AR = {
    "Saudi": "سعودي", "Egyptian": "مصري", "Indian": "هندي", "Bangladeshi": "بنجلاديشي",
    "Nepali": "نيبالي", "Pakistani": "باكستاني", "Yemeni": "يمني", "Filipino": "فلبيني",
    "Djiboutian": "جيبوتي", "Unknown": "غير محدد",
}


def normalize_nationality(nat: Optional[str]) -> str:
    if not nat:
        return "Unknown"
    return _NAT_MAP.get(str(nat).strip().lower(), str(nat).strip())


def is_saudi_nationality(nat: Optional[str], saudi_values=None) -> bool:
    """True if the nationality resolves to Saudi. Robust to EN/AR spellings and
    to an optional explicit saudi_values list from settings."""
    if normalize_nationality(nat) == "Saudi":
        return True
    if saudi_values and nat:
        low = str(nat).strip().lower()
        return any(str(v).strip().lower() == low for v in saudi_values)
    return False
