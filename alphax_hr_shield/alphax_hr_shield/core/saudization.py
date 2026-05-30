"""Weighted Saudization — closer to how HRSD/Qiwa actually computes the ratio.

Plain headcount % understates compliance because the official Nitaqat formula:
  * counts GCC nationals toward the Saudi figure (optionally with a factor), and
  * weights low-wage / part-time Saudis fractionally:
      - wage >= full_wage_threshold      -> counts as 1.0
      - partial_wage_threshold <= wage   -> counts as partial_factor (e.g. 0.5)
      - below partial_wage_threshold     -> 0 (or your configured floor)

All parameters are configuration (from AlphaX Saudization Settings), never
hard-coded law. Bands are resolved from a configurable list of (band_name,
min_percent) rows, so you can match the current official schedule for your
activity and size without code changes.
"""
from __future__ import annotations

from .compliance import normalize_nationality

DEFAULT_GCC = ["United Arab Emirates", "Kuwait", "Bahrain", "Qatar", "Oman",
               "الإمارات", "الكويت", "البحرين", "قطر", "عمان", "عُمان",
               "Emirati", "Kuwaiti", "Bahraini", "Qatari", "Omani"]

# Fallback band ladder if none configured (generic mixed-activity reference).
DEFAULT_BANDS = [
    {"band_name": "Platinum", "min_percent": 40},
    {"band_name": "High Green", "min_percent": 30},
    {"band_name": "Mid Green", "min_percent": 20},
    {"band_name": "Low Green", "min_percent": 10},
    {"band_name": "Yellow", "min_percent": 5},
]
BAND_COLORS = {
    "Platinum": "#9333ea", "High Green": "#16a34a", "Mid Green": "#22c55e",
    "Low Green": "#86efac", "Yellow": "#eab308", "Red": "#ef4444",
}


def nationality_group(nat, saudi_values, gcc_values) -> str:
    """Returns 'Saudi' | 'GCC' | 'Non-GCC' | 'Unknown'."""
    if not nat:
        return "Unknown"
    canon = normalize_nationality(nat)
    raw = str(nat).strip().lower()
    if canon == "Saudi" or any(str(v).strip().lower() == raw for v in (saudi_values or [])):
        return "Saudi"
    for v in (gcc_values or DEFAULT_GCC):
        if str(v).strip().lower() == raw or str(v).strip().lower() == canon.lower():
            return "GCC"
    return "Non-GCC"


def saudi_weight(wage, cfg) -> float:
    """Weight a single Saudi headcount by wage, per the configured thresholds."""
    full = cfg.get("full_wage_threshold") or 0
    partial = cfg.get("partial_wage_threshold") or 0
    pfactor = cfg.get("partial_factor")
    pfactor = 1.0 if pfactor is None else pfactor
    w = wage or 0
    if not full and not partial:
        return 1.0
    if full and w >= full:
        return 1.0
    if partial and w >= partial:
        return pfactor
    return 0.0


def classify_band(percent, bands=None):
    bands = bands or DEFAULT_BANDS
    ordered = sorted(bands, key=lambda b: b.get("min_percent", 0), reverse=True)
    for b in ordered:
        if percent >= (b.get("min_percent") or 0):
            name = b.get("band_name", "?")
            return {"band": name, "band_color": BAND_COLORS.get(name, "#64748b"),
                    "min_percent": b.get("min_percent")}
    return {"band": "Red", "band_color": BAND_COLORS["Red"], "min_percent": 0}


def compute(employees, cfg, bands=None) -> dict:
    """employees: list of dicts with keys: nationality, wage (optional), group(optional).
    cfg: dict with saudi_values, gcc_values, gcc_counts, gcc_factor, wage thresholds."""
    saudi_values = cfg.get("saudi_values") or ["Saudi"]
    gcc_values = cfg.get("gcc_values") or DEFAULT_GCC
    gcc_counts = cfg.get("gcc_counts", True)
    gcc_factor = cfg.get("gcc_factor")
    gcc_factor = 1.0 if gcc_factor is None else gcc_factor

    total = len(employees)
    saudi_n = gcc_n = nongcc_n = 0
    weighted_saudi = 0.0
    for e in employees:
        grp = e.get("group") or nationality_group(e.get("nationality"), saudi_values, gcc_values)
        if grp == "Saudi":
            saudi_n += 1
            weighted_saudi += saudi_weight(e.get("wage"), cfg)
        elif grp == "GCC":
            gcc_n += 1
            if gcc_counts:
                weighted_saudi += gcc_factor
        else:
            nongcc_n += 1

    headcount_pct = round(saudi_n / total * 100, 2) if total else 0.0
    weighted_pct = round(weighted_saudi / total * 100, 2) if total else 0.0
    band = classify_band(weighted_pct, bands)
    return {
        "total": total, "saudi": saudi_n, "gcc": gcc_n, "non_gcc": nongcc_n,
        "headcount_pct": headcount_pct,
        "weighted_saudi": round(weighted_saudi, 2),
        "weighted_pct": weighted_pct,
        **band,
    }
