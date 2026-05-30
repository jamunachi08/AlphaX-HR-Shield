"""after_install / after_migrate — seed child-table defaults (idempotent).

Everything here is just a starting point; users add/edit rows in the Settings.
"""
import json
import frappe


def after_install():
    seed_defaults()


def seed_defaults():
    _seed_hr_settings()
    _seed_gosi_settings()
    _seed_saudization_settings()
    frappe.db.commit()


def _has_rows(doc, table):
    return bool(getattr(doc, table, None))


def _seed_hr_settings():
    if not frappe.db.exists("DocType", "AlphaX HR Settings"):
        return
    s = frappe.get_single("AlphaX HR Settings")
    s.global_days = s.global_days or 90
    s.economic_activity = s.economic_activity or "general"
    if not s.saudi_nationality_values:
        s.saudi_nationality_values = '["Saudi","Saudi Arabia","Saudi Arabian","سعودي"]'

    if not _has_rows(s, "doc_thresholds"):
        for dt, days in [("national_id", 90), ("passport", 90), ("health_insurance", 60),
                         ("work_permit", 60), ("custom_identity", 90)]:
            s.append("doc_thresholds", {"document_type": dt, "threshold_days": days})

    if not _has_rows(s, "status_values"):
        defaults = [
            ("status", "نشط", "active"), ("status", "active", "active"),
            ("status", "مستبعد", "excluded"), ("status", "غير نشط", "inactive"),
            ("contract_status", "ساري", "active"), ("contract_status", "active", "active"),
            ("contract_status", "منتهي", "expired"), ("contract_status", "لا يوجد", "missing"),
            ("work_permit_status", "ساري", "active"), ("work_permit_status", "نشط", "active"),
            ("work_permit_status", "منتهية", "expired"), ("work_permit_status", "لا يوجد", "missing"),
            ("insurance_status", "نشط", "active"), ("insurance_status", "مسجل", "active"),
            ("insurance_status", "غير مسجل", "not_registered"), ("insurance_status", "غير نشط", "inactive"),
            ("iqama_status", "صالحة", "active"), ("iqama_status", "منتهية", "expired"),
            ("iqama_status", "غير متوفرة", "missing"),
            ("exit_status", "خروج نهائي", "final_exit"), ("exit_status", "خرج ولم يعد", "final_exit"),
            ("exit_status", "مستبعد", "excluded"),
        ]
        for concept, value, meaning in defaults:
            s.append("status_values", {"concept": concept, "value": value, "meaning": meaning})
    s.save(ignore_permissions=True)


def _seed_gosi_settings():
    if not frappe.db.exists("DocType", "AlphaX GOSI Settings"):
        return
    g = frappe.get_single("AlphaX GOSI Settings")
    g.wage_floor = g.wage_floor or 1500
    g.wage_ceiling = g.wage_ceiling or 45000
    if not _has_rows(g, "gosi_rates"):
        # 2026 schedule defaults — edit per the official GOSI schedule.
        g.append("gosi_rates", {"nationality_group": "Saudi", "employee_rate": 10.25,
                                "employer_rate": 12.25, "note": "Pension 9.5 + SANED 0.75 (+2 hazard employer)"})
        g.append("gosi_rates", {"nationality_group": "GCC", "employee_rate": 10.25,
                                "employer_rate": 12.25, "note": "Often mirrored to Saudi — verify"})
        g.append("gosi_rates", {"nationality_group": "Non-GCC", "employee_rate": 0,
                                "employer_rate": 2, "note": "Occupational hazard only"})
    g.save(ignore_permissions=True)


def _seed_saudization_settings():
    if not frappe.db.exists("DocType", "AlphaX Saudization Settings"):
        return
    s = frappe.get_single("AlphaX Saudization Settings")
    if not s.saudi_nationality_values:
        s.saudi_nationality_values = '["Saudi","Saudi Arabia","Saudi Arabian","سعودي"]'
    if s.gcc_counts is None:
        s.gcc_counts = 1
    s.gcc_factor = s.gcc_factor or 1.0
    s.partial_wage_threshold = s.partial_wage_threshold or 3000
    s.full_wage_threshold = s.full_wage_threshold or 4000
    s.partial_factor = s.partial_factor or 0.5

    if not _has_rows(s, "gcc_nationalities"):
        for n in ["United Arab Emirates", "Kuwait", "Bahrain", "Qatar", "Oman",
                  "الإمارات", "الكويت", "البحرين", "قطر", "عمان"]:
            s.append("gcc_nationalities", {"nationality": n})

    if not _has_rows(s, "nitaqat_bands"):
        for name, pct in [("Platinum", 40), ("High Green", 30), ("Mid Green", 20),
                          ("Low Green", 10), ("Yellow", 5)]:
            s.append("nitaqat_bands", {"band_name": name, "min_percent": pct})
    s.save(ignore_permissions=True)
