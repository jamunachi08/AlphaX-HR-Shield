"""GOSI contribution calculator.

Rates come from the AlphaX GOSI Settings → GOSI Rates child table, one row per
nationality group (Saudi / GCC / Non-GCC), so they're fully editable and you can
add groups. Contributory wage = basic + housing, bounded by floor & ceiling.
Defaults (seeded on install) reflect the 2026 schedule — verify against the
official GOSI schedule for your workforce.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GOSIResult:
    nationality_group: str
    contributory_wage: float
    employee_rate: float
    employer_rate: float
    employee_contribution: float
    employer_contribution: float
    total_contribution: float


def contributory_wage(basic, housing, floor, ceiling) -> float:
    wage = (basic or 0) + (housing or 0)
    wage = max(wage, floor or 0)
    if ceiling:
        wage = min(wage, ceiling)
    return wage


def compute_gosi(basic, housing, nationality_group, rates: dict) -> GOSIResult:
    """rates: {"wage_floor","wage_ceiling","by_group":{group:{"employee","employer"}}}."""
    floor = rates.get("wage_floor", 0)
    ceiling = rates.get("wage_ceiling", 0)
    cw = contributory_wage(basic, housing, floor, ceiling)

    by_group = rates.get("by_group") or {}
    grp = by_group.get(nationality_group) or by_group.get("Non-GCC") or {"employee": 0, "employer": 0}
    emp_rate = (grp.get("employee") or 0) / 100.0
    empr_rate = (grp.get("employer") or 0) / 100.0

    emp = round(cw * emp_rate, 2)
    empr = round(cw * empr_rate, 2)
    return GOSIResult(
        nationality_group=nationality_group,
        contributory_wage=round(cw, 2),
        employee_rate=round(emp_rate * 100, 3),
        employer_rate=round(empr_rate * 100, 3),
        employee_contribution=emp,
        employer_contribution=empr,
        total_contribution=round(emp + empr, 2),
    )
