"""Scheduled tasks — Frappe scheduler (see scheduler_events in hooks.py)."""
from datetime import datetime
import frappe
from .api import dashboard


def run_due_alert_rules():
    current_hour = datetime.now().hour
    rules = frappe.get_all("AlphaX Alert Rule", filters={"enabled": 1},
                           fields=["name", "schedule_hour", "trigger_statuses",
                                   "doc_types", "email_to", "webhook_url"])
    snapshot = None
    for rule in rules:
        sched = rule.get("schedule_hour")
        if sched is not None and sched != current_hour:
            continue
        if snapshot is None:
            snapshot = dashboard()
        try:
            _run_rule(rule, snapshot)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"AlphaX alert failed: {rule['name']}")


def _run_rule(rule, snapshot):
    statuses = [x.strip() for x in (rule.get("trigger_statuses") or "expired,critical").split(",")]
    doc_types = rule.get("doc_types")
    doc_types = [d.strip() for d in doc_types.split(",")] if doc_types else None
    matched = [d for d in snapshot["expiring"]
               if d["status"] in statuses and (doc_types is None or d["doc_type"] in doc_types)]
    if not matched:
        return
    if rule.get("email_to"):
        rows = "".join(
            f"<tr><td>{m['employee_name']}</td><td>{m['doc_label']}</td>"
            f"<td>{m['expiry_date']}</td><td>{m['days_until_expiry']}</td>"
            f"<td>{m['status']}</td></tr>" for m in matched)
        frappe.sendmail(
            recipients=[e.strip() for e in rule["email_to"].split(",") if e.strip()],
            subject=f"[AlphaX HR Shield] {len(matched)} expiring document(s)",
            message=f"<h3>{len(matched)} document(s) need attention</h3>"
                    "<table border='1' cellpadding='6'><tr><th>Employee</th><th>Document</th>"
                    f"<th>Expiry</th><th>Days</th><th>Status</th></tr>{rows}</table>")
    if rule.get("webhook_url"):
        try:
            import requests
            requests.post(rule["webhook_url"], json={"matched": matched}, timeout=10)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "AlphaX webhook failed")
    frappe.db.set_value("AlphaX Alert Rule", rule["name"],
                        {"last_triggered_at": frappe.utils.now(),
                         "last_result_summary": f"{len(matched)} matched"})
    frappe.db.commit()


def capture_monthly_snapshot():
    """Monthly Saudization snapshot for trend tracking (see scheduler_events)."""
    try:
        from .api import capture_snapshot
        company = None
        try:
            company = frappe.defaults.get_global_default("company")
        except Exception:
            pass
        capture_snapshot(company=company)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AlphaX monthly snapshot failed")
