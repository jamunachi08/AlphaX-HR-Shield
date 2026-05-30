"""Workforce compliance report engine — KSA-style "موظفون نشطون / غير نشطين /
خروج نهائي / حالة العقود" analysis.

Pure logic: takes a list of normalized employee dicts and produces statistics,
a nationality breakdown, categorized lists (Saudi, expat, needs-insurance,
final-exit, no-contract/permit, inactive-but-insured, expired-permit), and an
action summary.

Status values vary per site and language, so classification uses token matching
across Arabic and English keywords instead of exact equality.
"""
from __future__ import annotations

from .compliance import normalize_nationality, is_saudi_nationality

# Built-in fallback tokens per meaning (used when no configured value matches).
# Order matters: negative/!=active meanings are checked before 'active' so that
# e.g. "غير مسجل" (contains "مسجل") resolves to not_registered, not active.
DEFAULT_TOKENS = [
    ("not_registered", ["غير مسجل", "not registered", "unregistered"]),
    ("final_exit", ["خروج نهائي", "final exit", "خرج ولم يعد", "exited"]),
    ("excluded", ["مستبعد", "excluded", "terminated", "left"]),
    ("inactive", ["غير نشط", "inactive", "متوقف", "suspended"]),
    ("expired", ["منتهي", "منتهية", "expired"]),
    ("missing", ["لا يوجد", "بدون", "غير متوفر", "missing", "not available", "none"]),
    ("active", ["نشط", "ساري", "سارية", "active", "valid", "صالح", "صالحة", "مسجل", "registered"]),
]


def meaning_of(concept, value, status_map=None):
    """Resolve a raw status value to a canonical meaning.
    Checks the configured Status-Value dictionary first, then built-in tokens."""
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    # configured values for this concept (exact-substring match)
    for v, meaning in (status_map or {}).get(concept, []):
        if v and str(v).strip().lower() in raw:
            return meaning
    for meaning, tokens in DEFAULT_TOKENS:
        if any(t.lower() in raw for t in tokens):
            return meaning
    return None


def _is_empty(value) -> bool:
    return value is None or str(value).strip() == ""


# --- per-employee predicates --------------------------------------------- #
def is_saudi(e, saudi_values):
    return is_saudi_nationality(e.get("nationality"), saudi_values)

def active_status(e, sm=None):
    return meaning_of("status", e.get("status"), sm) == "active"

def final_exit(e, sm=None):
    return meaning_of("exit_status", e.get("exit_status"), sm) == "final_exit" \
        or meaning_of("status", e.get("status"), sm) == "final_exit"

def excluded(e, sm=None):
    return final_exit(e, sm) or meaning_of("exit_status", e.get("exit_status"), sm) == "excluded" \
        or meaning_of("status", e.get("status"), sm) == "excluded"

def active_contract(e, sm=None):
    return meaning_of("contract_status", e.get("contract_status"), sm) == "active"

def missing_contract(e, sm=None):
    return _is_empty(e.get("contract_status")) or meaning_of("contract_status", e.get("contract_status"), sm) == "missing"

def active_permit(e, sm=None):
    return meaning_of("work_permit_status", e.get("work_permit_status"), sm) == "active"

def expired_permit(e, sm=None):
    return meaning_of("work_permit_status", e.get("work_permit_status"), sm) == "expired"

def missing_permit(e, sm=None):
    return _is_empty(e.get("work_permit_status")) or meaning_of("work_permit_status", e.get("work_permit_status"), sm) == "missing"

def insured(e, sm=None):
    return meaning_of("insurance_status", e.get("insurance_status"), sm) == "active"

def not_registered(e, sm=None):
    m = meaning_of("insurance_status", e.get("insurance_status"), sm)
    return m in ("not_registered", "inactive")


def build_report(employees: list, saudi_values: list, status_map: dict = None, company: str = None) -> dict:
    sm = status_map or {}
    saudis, expats = [], []
    for e in employees:
        (saudis if is_saudi(e, saudi_values) else expats).append(e)

    active = [e for e in employees if active_status(e, sm)]
    inactive = [e for e in employees if not active_status(e, sm)]
    needs_insurance = [e for e in employees if not_registered(e, sm)]
    no_contract_or_permit = [e for e in employees if missing_contract(e, sm) or missing_permit(e, sm)]
    inactive_insured_active = [e for e in employees
                               if (not active_status(e, sm)) and insured(e, sm) and active_contract(e, sm)]
    final_exit_active = [e for e in employees if final_exit(e, sm) and active_contract(e, sm)]
    final_exit_list = [e for e in employees if excluded(e, sm)]
    expired_or_missing_permit = [e for e in employees if expired_permit(e, sm) or missing_permit(e, sm)]

    # nationality breakdown (expats), sorted desc
    counts = {}
    for e in expats:
        nat = normalize_nationality(e.get("nationality"))
        counts[nat] = counts.get(nat, 0) + 1
    breakdown = sorted(({"nationality": k, "count": v} for k, v in counts.items()),
                       key=lambda x: x["count"], reverse=True)

    total = len(employees)
    stats = {
        "total": total,
        "saudi": len(saudis),
        "non_saudi": len(expats),
        "saudi_pct": round(len(saudis) / total * 100, 2) if total else 0,
        "non_saudi_pct": round(len(expats) / total * 100, 2) if total else 0,
        "active": len(active),
        "inactive": len(inactive),
        "active_pct": round(len(active) / total * 100, 2) if total else 0,
        "inactive_pct": round(len(inactive) / total * 100, 2) if total else 0,
        "needs_insurance": len(needs_insurance),
        "needs_insurance_pct": round(len(needs_insurance) / total * 100, 2) if total else 0,
        "final_exit_active_contract": len(final_exit_active),
        "final_exit_active_contract_pct": round(len(final_exit_active) / total * 100, 2) if total else 0,
    }

    actions = [
        {"n": 1, "title": "تسجيل التأمينات",
         "desc": "تسجيل جميع الموظفين غير المسجلين في منظومة التأمينات الاجتماعية",
         "count": len(needs_insurance)},
        {"n": 2, "title": "تسوية الخروج النهائي",
         "desc": "إنهاء إجراءات الموظفين المغادرين وإلغاء الإقامات وتسوية المستحقات",
         "count": len(final_exit_active)},
        {"n": 3, "title": "تجديد الوثائق المنتهية",
         "desc": "مراجعة وتجديد رخص العمل والإقامات المنتهية لضمان الامتثال",
         "count": len(expired_or_missing_permit)},
        {"n": 4, "title": "استخراج العقود ورخص العمل المفقودة",
         "desc": "استخراج عقود ورخص عمل للموظفين الذين لا يوجد لديهم عقد أو رخصة",
         "count": len(no_contract_or_permit)},
    ]

    return {
        "company": company,
        "stats": stats,
        "nationality_breakdown": breakdown,
        "sections": {
            "saudi_employees": saudis,
            "expat_employees": expats,
            "needs_insurance": needs_insurance,
            "final_exit": final_exit_list,
            "no_contract_or_permit": no_contract_or_permit,
            "inactive_insured_active_contract": inactive_insured_active,
            "final_exit_active_contract": final_exit_active,
            "expired_or_missing_permit": expired_or_missing_permit,
        },
        "actions": actions,
    }
