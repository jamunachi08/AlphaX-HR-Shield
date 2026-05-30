"""Saudization / Nitaqat band logic — ported from routes/nitaqat.ts.

Thresholds are the published MHRSD-style band cutoffs keyed by economic activity
and company-size bucket. These are configuration, not law — verify against the
current official Nitaqat schedule for your activity before relying on them.
"""
from __future__ import annotations

from .compliance import normalize_nationality, is_saudi_nationality

NITAQAT_THRESHOLDS = {
    "general": {
        "5-9":    {"platinum": 40, "high_green": 30, "mid_green": 20, "low_green": 10, "yellow": 5},
        "10-24":  {"platinum": 40, "high_green": 32, "mid_green": 22, "low_green": 12, "yellow": 6},
        "25-49":  {"platinum": 45, "high_green": 36, "mid_green": 26, "low_green": 16, "yellow": 8},
        "50-499": {"platinum": 50, "high_green": 40, "mid_green": 30, "low_green": 20, "yellow": 10},
        "500+":   {"platinum": 55, "high_green": 45, "mid_green": 35, "low_green": 25, "yellow": 12},
    },
    "construction": {
        "5-9":    {"platinum": 30, "high_green": 22, "mid_green": 14, "low_green": 6, "yellow": 3},
        "10-24":  {"platinum": 30, "high_green": 22, "mid_green": 14, "low_green": 6, "yellow": 3},
        "25-49":  {"platinum": 35, "high_green": 26, "mid_green": 18, "low_green": 9, "yellow": 4},
        "50-499": {"platinum": 40, "high_green": 31, "mid_green": 22, "low_green": 12, "yellow": 6},
        "500+":   {"platinum": 45, "high_green": 36, "mid_green": 26, "low_green": 15, "yellow": 7},
    },
    "manufacturing": {
        "5-9":    {"platinum": 35, "high_green": 27, "mid_green": 18, "low_green": 9, "yellow": 4},
        "10-24":  {"platinum": 35, "high_green": 27, "mid_green": 18, "low_green": 9, "yellow": 4},
        "25-49":  {"platinum": 40, "high_green": 31, "mid_green": 22, "low_green": 12, "yellow": 6},
        "50-499": {"platinum": 45, "high_green": 36, "mid_green": 26, "low_green": 16, "yellow": 8},
        "500+":   {"platinum": 50, "high_green": 40, "mid_green": 30, "low_green": 20, "yellow": 10},
    },
    "trade": {
        "5-9":    {"platinum": 40, "high_green": 30, "mid_green": 20, "low_green": 10, "yellow": 5},
        "10-24":  {"platinum": 40, "high_green": 32, "mid_green": 22, "low_green": 12, "yellow": 6},
        "25-49":  {"platinum": 45, "high_green": 36, "mid_green": 26, "low_green": 16, "yellow": 8},
        "50-499": {"platinum": 50, "high_green": 40, "mid_green": 30, "low_green": 20, "yellow": 10},
        "500+":   {"platinum": 55, "high_green": 45, "mid_green": 35, "low_green": 25, "yellow": 12},
    },
    "finance": {
        "5-9":    {"platinum": 60, "high_green": 50, "mid_green": 40, "low_green": 30, "yellow": 15},
        "10-24":  {"platinum": 60, "high_green": 50, "mid_green": 40, "low_green": 30, "yellow": 15},
        "25-49":  {"platinum": 65, "high_green": 55, "mid_green": 45, "low_green": 35, "yellow": 17},
        "50-499": {"platinum": 70, "high_green": 60, "mid_green": 50, "low_green": 40, "yellow": 20},
        "500+":   {"platinum": 75, "high_green": 65, "mid_green": 55, "low_green": 45, "yellow": 22},
    },
    "agriculture": {
        "5-9":    {"platinum": 20, "high_green": 14, "mid_green": 9, "low_green": 4, "yellow": 2},
        "10-24":  {"platinum": 20, "high_green": 14, "mid_green": 9, "low_green": 4, "yellow": 2},
        "25-49":  {"platinum": 25, "high_green": 18, "mid_green": 12, "low_green": 6, "yellow": 3},
        "50-499": {"platinum": 30, "high_green": 22, "mid_green": 15, "low_green": 8, "yellow": 4},
        "500+":   {"platinum": 35, "high_green": 26, "mid_green": 18, "low_green": 10, "yellow": 5},
    },
}

BAND_COLORS = {
    "platinum": ("Platinum", "#E5E4E2"),
    "high_green": ("High Green", "#16a34a"),
    "mid_green": ("Mid Green", "#22c55e"),
    "low_green": ("Low Green", "#86efac"),
    "yellow": ("Yellow", "#eab308"),
    "red": ("Red", "#ef4444"),
    "exempt": ("Exempt", "#94a3b8"),
}


def get_size_category(total: int) -> str:
    if total <= 4:
        return "exempt"
    if total <= 9:
        return "5-9"
    if total <= 24:
        return "10-24"
    if total <= 49:
        return "25-49"
    if total <= 499:
        return "50-499"
    return "500+"


def get_thresholds(activity: str, size_category: str) -> dict:
    activity_t = NITAQAT_THRESHOLDS.get(activity, NITAQAT_THRESHOLDS["general"])
    return activity_t.get(size_category, activity_t["50-499"])


def classify_band(pct: float, thresholds: dict) -> dict:
    for band in ("platinum", "high_green", "mid_green", "low_green", "yellow"):
        if pct >= thresholds[band]:
            label, color = BAND_COLORS[band]
            return {"band": band, "band_label": label, "band_color": color}
    label, color = BAND_COLORS["red"]
    return {"band": "red", "band_label": label, "band_color": color}


def is_saudi(nationality, saudi_values) -> bool:
    return is_saudi_nationality(nationality, saudi_values)
