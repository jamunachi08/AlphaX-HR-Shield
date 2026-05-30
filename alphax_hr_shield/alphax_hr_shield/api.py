"""AlphaX HR Shield — unified whitelisted API.

All configuration is read from child tables (Field Mappings, Status Values,
GOSI Rates, Document Thresholds, Nitaqat Bands, GCC Nationalities) so nothing is
hard-coded and you can add rows freely.
"""
from __future__ import annotations

import json
import frappe

from .core import compliance as comp
from .core import esb as esb_core
from .core import gosi as gosi_core
from .core import workforce as wf
from .core import saudization as sd
from . import data as data_layer
from .integrations import get_adapter


# --------------------------------------------------------------------------- #
# Settings loaders (all child-table driven)
# --------------------------------------------------------------------------- #
def _rows(doc, table):
    return [r if isinstance(r, dict) else r.as_dict() for r in (getattr(doc, table, None) or [])]


def _thresholds() -> dict:
    s = frappe.get_single("AlphaX HR Settings")
    by_type = {}
    for r in _rows(s, "doc_thresholds"):
        if r.get("document_type"):
            by_type[r["document_type"]] = r.get("threshold_days")
    return {"global_days": s.global_days or 90, "by_type": by_type}


def _status_map() -> dict:
    s = frappe.get_single("AlphaX HR Settings")
    m = {}
    for r in _rows(s, "status_values"):
        if r.get("concept") and r.get("value") and r.get("meaning"):
            m.setdefault(r["concept"], []).append((r["value"], r["meaning"]))
    return m


def _saudi_values() -> list:
    s = frappe.get_single("AlphaX HR Settings")
    try:
        return json.loads(s.saudi_nationality_values or '["Saudi"]')
    except Exception:
        return ["Saudi"]


def _saud_cfg() -> tuple:
    s = frappe.get_single("AlphaX Saudization Settings")
    try:
        saudi_values = json.loads(s.saudi_nationality_values or '["Saudi"]')
    except Exception:
        saudi_values = ["Saudi"]
    gcc_values = [r.get("nationality") for r in _rows(s, "gcc_nationalities") if r.get("nationality")]
    bands = [{"band_name": r.get("band_name"), "min_percent": r.get("min_percent")}
             for r in _rows(s, "nitaqat_bands") if r.get("band_name")]
    cfg = {
        "saudi_values": saudi_values,
        "gcc_values": gcc_values or None,
        "gcc_counts": bool(s.gcc_counts),
        "gcc_factor": s.gcc_factor if s.gcc_factor is not None else 1.0,
        "partial_wage_threshold": s.partial_wage_threshold or 0,
        "full_wage_threshold": s.full_wage_threshold or 0,
        "partial_factor": s.partial_factor if s.partial_factor is not None else 1.0,
    }
    return cfg, (bands or None)


def _gosi_rates() -> dict:
    s = frappe.get_single("AlphaX GOSI Settings")
    by_group = {}
    for r in _rows(s, "gosi_rates"):
        if r.get("nationality_group"):
            by_group[r["nationality_group"]] = {"employee": r.get("employee_rate") or 0,
                                                 "employer": r.get("employer_rate") or 0}
    return {"wage_floor": s.wage_floor or 0, "wage_ceiling": s.wage_ceiling or 0, "by_group": by_group}


def _group_of(nat, cfg):
    return sd.nationality_group(nat, cfg["saudi_values"], cfg["gcc_values"])


def _active_employees():
    """Active workforce, resolved via the configurable status dictionary so it
    works whether status is stored as 'Active', 'نشط', or a custom value."""
    sm = _status_map()
    out = []
    for e in data_layer.fetch_employees(status="all"):
        m = wf.meaning_of("status", e.get("status"), sm)
        if m is None or m == "active":  # treat unknown/blank as active by default
            out.append(e)
    return out


def _employee_docs(emp: dict, t: dict) -> list:
    pairs = [
        ("national_id", "National ID / Iqama", emp.get("national_id"), emp.get("national_id_expiry")),
        ("passport", "Passport", emp.get("passport_number"), emp.get("passport_expiry")),
        ("health_insurance", "Health Insurance", emp.get("health_insurance_no"), emp.get("health_insurance_expiry")),
        ("work_permit", "Work Permit", emp.get("work_permit_status"), emp.get("work_permit_expiry")),
        ("custom_identity", "Custom Identity", emp.get("custom_identity_no"), emp.get("custom_identity_expiry")),
    ]
    out = []
    for doc_type, label, number, expiry in pairs:
        threshold = comp.get_doc_threshold(doc_type, t)
        out.append({"doc_type": doc_type, "doc_label": label, "doc_number": number,
                    "expiry_date": str(expiry) if expiry else None,
                    "status": comp.get_expiry_status(expiry, threshold),
                    "days_until_expiry": comp.get_days_until_expiry(expiry)})
    return out


# --------------------------------------------------------------------------- #
# Compliance & documents
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def employees(status: str = "Active", department: str = None, nationality: str = None):
    t = _thresholds()
    result = []
    for e in data_layer.fetch_employees(status, department, nationality):
        result.append({**e, "nationality": comp.normalize_nationality(e.get("nationality")),
                       "risk_score": comp.compute_risk_score(e, {"global_days": t["global_days"]}),
                       "documents": _employee_docs(e, t)})
    result.sort(key=lambda r: r["risk_score"], reverse=True)
    return result


@frappe.whitelist()
def dashboard():
    t = _thresholds()
    emps = _active_employees()
    labels = {"national_id": "National ID / Iqama", "passport": "Passport",
              "health_insurance": "Health Insurance", "work_permit": "Work Permit",
              "custom_identity": "Custom Identity"}
    by_type = {k: {"doc_type": k, "label": v, "expired": 0, "critical": 0,
                   "warning": 0, "ok": 0, "missing": 0} for k, v in labels.items()}
    expiring = []
    for e in emps:
        for doc in _employee_docs(e, t):
            b = by_type.get(doc["doc_type"])
            if b:
                b[doc["status"]] += 1
            if doc["status"] in ("expired", "critical", "warning"):
                expiring.append({"employee_id": e["id"], "employee_name": e["name"],
                                 "department": e.get("department"), "doc_type": doc["doc_type"],
                                 "doc_label": doc["doc_label"], "expiry_date": doc["expiry_date"],
                                 "days_until_expiry": doc["days_until_expiry"], "status": doc["status"]})
    expiring.sort(key=lambda x: x["days_until_expiry"])
    return {"total_employees": len(emps), "by_doc_type": list(by_type.values()),
            "expiring": expiring, "thresholds": t}


# --------------------------------------------------------------------------- #
# Saudization (weighted, GCC-aware, configurable bands)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def nitaqat():
    cfg, bands = _saud_cfg()
    emps = _active_employees()
    rows = []
    for e in emps:
        w = data_layer.resolve_wage(e["id"], e)
        rows.append({"nationality": e.get("nationality"), "wage": w["basic"] + w["housing"]})
    r = sd.compute(rows, cfg, bands)
    # Back-compat keys used by older UI + clearer new keys
    r["saudization_pct"] = r["weighted_pct"]
    r["band_label"] = r["band"]
    r["non_saudis"] = r["non_gcc"] + 0
    r["saudis"] = r["saudi"]
    r["bands"] = bands or sd.DEFAULT_BANDS
    r["economic_activity"] = frappe.get_single("AlphaX HR Settings").economic_activity or "general"
    return r


# --------------------------------------------------------------------------- #
# Workforce compliance report
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def workforce_report():
    saudi_values = _saudi_values()
    status_map = _status_map()
    company = None
    try:
        company = frappe.defaults.get_global_default("company")
    except Exception:
        pass
    employees = data_layer.fetch_employees(status="all")
    for e in employees:
        e["nationality"] = comp.normalize_nationality(e.get("nationality"))
    return wf.build_report(employees, saudi_values, status_map=status_map, company=company)


# --------------------------------------------------------------------------- #
# End-of-Service Benefit
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def esb_estimate(employee: str, last_wage: float = None, reason: str = "termination", end_date: str = None):
    emp = frappe.db.get_value("Employee", employee,
                              ["employee_name", "date_of_joining", "relieving_date"], as_dict=True)
    if not emp:
        frappe.throw(f"Employee {employee} not found")
    from frappe.utils import getdate, nowdate
    start = getdate(emp.date_of_joining)
    end = getdate(end_date or emp.relieving_date or nowdate())
    years = esb_core.years_between(start, end)
    if last_wage is None:
        w = data_layer.resolve_wage(employee)
        last_wage = w["basic"] + w["housing"]
    res = esb_core.compute_esb(years, float(last_wage), reason)
    return {"employee": employee, "employee_name": emp.employee_name,
            "date_of_joining": str(start), "end_date": str(end), **res.__dict__}


# --------------------------------------------------------------------------- #
# GOSI
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def gosi_estimate(employee: str = None, basic: float = None, housing: float = None, nationality_group: str = None):
    rates = _gosi_rates()
    cfg, _ = _saud_cfg()
    if employee:
        nat = data_layer.employee_nationality(employee)
        if not nationality_group:
            nationality_group = _group_of(nat, cfg)
        if basic is None or housing is None:
            w = data_layer.resolve_wage(employee)
            basic = basic if basic is not None else w["basic"]
            housing = housing if housing is not None else w["housing"]
    res = gosi_core.compute_gosi(float(basic or 0), float(housing or 0),
                                 nationality_group or "Non-GCC", rates)
    return {"employee": employee, **res.__dict__}


@frappe.whitelist()
def gosi_run():
    rates = _gosi_rates()
    cfg, _ = _saud_cfg()
    rows, tot_e, tot_r = [], 0.0, 0.0
    for e in _active_employees():
        w = data_layer.resolve_wage(e["id"], e)
        grp = _group_of(e.get("nationality"), cfg)
        r = gosi_core.compute_gosi(w["basic"], w["housing"], grp, rates)
        tot_e += r.employee_contribution
        tot_r += r.employer_contribution
        rows.append({"employee": e["id"], "employee_name": e["name"], **r.__dict__})
    return {"rows": rows, "total_employee": round(tot_e, 2), "total_employer": round(tot_r, 2),
            "grand_total": round(tot_e + tot_r, 2)}


# --------------------------------------------------------------------------- #
# Snapshots & trends
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def capture_snapshot(company: str = None):
    from frappe.utils import nowdate
    cfg, bands = _saud_cfg()
    emps = _active_employees()
    rows = []
    for e in emps:
        w = data_layer.resolve_wage(e["id"], e)
        rows.append({"nationality": e.get("nationality"), "wage": w["basic"] + w["housing"]})
    r = sd.compute(rows, cfg, bands)
    doc = frappe.get_doc({
        "doctype": "AlphaX Saudization Snapshot", "snapshot_date": nowdate(), "company": company,
        "total_headcount": r["total"], "saudi_headcount": r["saudi"], "gcc_headcount": r["gcc"],
        "headcount_percent": r["headcount_pct"], "weighted_percent": r["weighted_pct"],
        "nitaqat_band": r["band"],
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"snapshot": doc.name, **r}


@frappe.whitelist()
def get_trend(limit: int = 12):
    rows = frappe.get_all("AlphaX Saudization Snapshot",
                          fields=["snapshot_date", "weighted_percent", "headcount_percent",
                                  "total_headcount", "saudi_headcount", "nitaqat_band"],
                          order_by="snapshot_date asc", limit_page_length=int(limit))
    return rows


# --------------------------------------------------------------------------- #
# Government portal integration
# --------------------------------------------------------------------------- #
def _connection(name: str) -> dict:
    doc = frappe.get_doc("AlphaX Gov Connection", name)
    return {"portal": doc.portal, "base_url": doc.base_url, "environment": doc.environment,
            "establishment_id": doc.establishment_id,
            "api_token": doc.get_password("api_token") if doc.api_token else None}


@frappe.whitelist()
def gov_test_connection(connection: str):
    conn = _connection(connection)
    adapter = get_adapter(conn["portal"], conn)
    try:
        result = adapter.test_connection()
        status, message = "success", "Connected"
    except Exception as e:
        result, status, message = None, "error", str(e)
    _log_sync(connection, conn["portal"], "test_connection", status, message)
    return {"status": status, "message": message, "result": result}


def _log_sync(connection, portal, action, status, message, reference=None):
    frappe.get_doc({"doctype": "AlphaX Gov Sync Log", "connection": connection, "portal": portal,
                    "action": action, "status": status, "message": (message or "")[:500],
                    "reference": reference}).insert(ignore_permissions=True)
    frappe.db.commit()
