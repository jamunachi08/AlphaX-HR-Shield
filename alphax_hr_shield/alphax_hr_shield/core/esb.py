"""End-of-Service Benefit (ESB / gratuity) — Saudi Labor Law Articles 84 & 85.

Article 84 base award (employer-initiated termination, contract expiry, etc.):
  * half a month's wage for each of the first five years of service
  * one month's wage for each year beyond five
  * fractional years are paid pro-rata

Article 85 (employee resignation) applies a fraction of the Article 84 award
based on length of service:
  * under 2 years   -> nothing
  * 2 to under 5    -> one third
  * 5 to under 10   -> two thirds
  * 10 years or more-> the full award

The "wage" used is the employee's last wage. Which salary components count can
vary by contract, so the caller passes the resolved monthly wage.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ESBResult:
    years_of_service: float
    last_wage: float
    article84_award: float
    applied_fraction: float
    award: float
    basis: str


def years_between(start, end) -> float:
    """Service length in (fractional) years using a 365-day convention."""
    return max((end - start).days / 365.0, 0.0)


def article84_award(years: float, last_wage: float) -> float:
    first_five = min(years, 5.0) * 0.5
    beyond_five = max(years - 5.0, 0.0) * 1.0
    return (first_five + beyond_five) * last_wage


def resignation_fraction(years: float) -> float:
    if years < 2:
        return 0.0
    if years < 5:
        return 1.0 / 3.0
    if years < 10:
        return 2.0 / 3.0
    return 1.0


def compute_esb(years: float, last_wage: float, reason: str = "termination") -> ESBResult:
    """reason: 'termination' (full Article 84) or 'resignation' (Article 85)."""
    base = article84_award(years, last_wage)
    if reason == "resignation":
        fraction = resignation_fraction(years)
        basis = "Article 85 (resignation)"
    else:
        fraction = 1.0
        basis = "Article 84 (termination / end of contract)"
    return ESBResult(
        years_of_service=round(years, 3),
        last_wage=last_wage,
        article84_award=round(base, 2),
        applied_fraction=round(fraction, 4),
        award=round(base * fraction, 2),
        basis=basis,
    )
