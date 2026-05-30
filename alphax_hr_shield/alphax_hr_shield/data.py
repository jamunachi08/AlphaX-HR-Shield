"""Local data layer — reads Employee/salary data straight from the Frappe DB,
driven by configurable child-table mappings (no fixed columns).

Field Mappings (AlphaX HR Settings → Field Mappings): concept → Employee
fieldname. Anything not mapped falls back to built-in candidate auto-detection.
Only columns that actually exist on Employee are ever queried, so a missing
field degrades to None instead of raising "Unknown column".
"""
from __future__ import annotations

import frappe

MANDATORY = ["name"]

# Built-in auto-detect candidates (used when a concept has no explicit mapping).
FIELD_MAP = {
    "employee_name": ["employee_name"],
    "department": ["department"],
    "designation": ["designation"],
    "status": ["status"],
    "date_of_joining": ["date_of_joining"],
    "relieving_date": ["relieving_date"],
    "nationality": ["employee_nationality", "nationality", "custom_nationality"],
    "national_id": ["national_id", "custom_national_id", "iqama_number", "custom_iqama", "custom_iqama_number"],
    "national_id_expiry": ["id_expiry_date", "iqama_expiry_date", "custom_iqama_expiry"],
    "passport_number": ["passport_number"],
    "passport_expiry": ["valid_upto", "passport_expiry_date"],
    "health_insurance_no": ["health_insurance_no", "custom_health_insurance_no"],
    "contract_status": ["custom_contract_status", "contract_status", "custom_aqd"],
    "work_permit_status": ["custom_work_permit_status", "work_permit_status", "custom_rukhsa_amal"],
    "work_permit_expiry": ["custom_work_permit_expiry", "work_permit_expiry_date"],
    "insurance_status": ["custom_insurance_status", "gosi_status", "custom_taminat_status"],
    "iqama_status": ["custom_iqama_status", "iqama_status", "custom_residence_status"],
    "exit_status": ["custom_exit_status", "exit_type", "custom_khuruj", "custom_final_exit"],
    "basic_salary": ["custom_basic_salary", "basic_salary"],
    "housing_allowance": ["custom_housing_allowance", "housing_allowance"],
    "custom_identity_no": [],
    "custom_identity_expiry": [],
}

# All concepts that map to a single value on the normalized employee dict.
_VALUE_CONCEPTS = [k for k in FIELD_MAP]


def _rows(doc, table_field):
    rows = getattr(doc, table_field, None) or []
    out = []
    for r in rows:
        out.append(r if isinstance(r, dict) else r.as_dict())
    return out


def settings_doc():
    return frappe.get_single("AlphaX HR Settings")


def settings() -> dict:
    return settings_doc().as_dict()


def field_mapping(doc=None) -> dict:
    """concept -> explicit Employee fieldname, from the Field Mappings child table."""
    doc = doc or settings_doc()
    m = {}
    for r in _rows(doc, "field_mappings"):
        if r.get("concept") and r.get("employee_fieldname"):
            m[r["concept"]] = r["employee_fieldname"]
    return m


def _existing_candidates(doc):
    meta = frappe.get_meta("Employee")
    explicit = field_mapping(doc)
    fields = list(MANDATORY)
    resolved = {}
    for concept in _VALUE_CONCEPTS:
        candidates = []
        if explicit.get(concept):
            candidates.append(explicit[concept])
        candidates += FIELD_MAP.get(concept, [])
        chosen = None
        for cand in candidates:
            if cand and meta.has_field(cand):
                chosen = cand
                break
        resolved[concept] = chosen
        if chosen and chosen not in fields:
            fields.append(chosen)
    return fields, resolved


def normalize_employee(emp: dict, resolved: dict) -> dict:
    def val(concept):
        fn = resolved.get(concept)
        return emp.get(fn) if fn else None
    return {
        "id": emp.get("name"),
        "name": val("employee_name") or emp.get("name"),
        "department": val("department"),
        "designation": val("designation"),
        "nationality": val("nationality"),
        "status": val("status") or "Active",
        "date_of_joining": val("date_of_joining"),
        "relieving_date": val("relieving_date"),
        "national_id": val("national_id"),
        "national_id_expiry": val("national_id_expiry"),
        "passport_number": val("passport_number"),
        "passport_expiry": val("passport_expiry"),
        "health_insurance_no": val("health_insurance_no"),
        "health_insurance_expiry": None,
        "custom_identity_no": val("custom_identity_no"),
        "custom_identity_expiry": val("custom_identity_expiry"),
        "contract_status": val("contract_status"),
        "work_permit_status": val("work_permit_status"),
        "work_permit_expiry": val("work_permit_expiry"),
        "insurance_status": val("insurance_status"),
        "iqama_status": val("iqama_status"),
        "exit_status": val("exit_status"),
        "basic_salary": val("basic_salary"),
        "housing_allowance": val("housing_allowance"),
    }


def fetch_employees(status: str = "Active", department: str | None = None,
                    nationality: str | None = None) -> list:
    doc = settings_doc()
    fields, resolved = _existing_candidates(doc)
    filters = {}
    if status and status != "all" and resolved.get("status"):
        filters[resolved["status"]] = status
    if department and resolved.get("department"):
        filters[resolved["department"]] = department
    rows = frappe.get_all("Employee", filters=filters, fields=fields, limit_page_length=0)
    employees = [normalize_employee(r, resolved) for r in rows]
    if nationality:
        nat = nationality.lower()
        employees = [e for e in employees if (e.get("nationality") or "").lower() == nat]
    return employees


def fetch_all_active_employees() -> list:
    return fetch_employees(status="Active")


def employee_nationality(employee_id: str):
    meta = frappe.get_meta("Employee")
    doc = settings_doc()
    explicit = field_mapping(doc)
    cands = ([explicit["nationality"]] if explicit.get("nationality") else []) + FIELD_MAP["nationality"]
    for cand in cands:
        if cand and meta.has_field(cand):
            return frappe.db.get_value("Employee", employee_id, cand)
    return None


def resolve_wage(employee_id: str, emp: dict | None = None) -> dict:
    """Best-effort basic + housing for GOSI/ESB.

    Order: mapped Employee salary fields -> latest Salary Structure Assignment
    'base' -> 0. Never raises if payroll isn't configured."""
    basic = float((emp or {}).get("basic_salary") or 0)
    housing = float((emp or {}).get("housing_allowance") or 0)
    if basic:
        return {"basic": basic, "housing": housing}
    try:
        ssa = frappe.get_all("Salary Structure Assignment",
                             filters={"employee": employee_id, "docstatus": 1},
                             fields=["base"], order_by="from_date desc", limit_page_length=1)
        if ssa:
            basic = float(ssa[0].get("base") or 0)
    except Exception:
        pass
    return {"basic": basic, "housing": housing}
