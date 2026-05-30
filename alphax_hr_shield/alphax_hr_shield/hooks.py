app_name = "alphax_hr_shield"
app_title = "AlphaX HR Shield"
app_publisher = "AlphaX"
app_description = "Ultimate KSA-focused HR compliance suite for Frappe/ERPNext: document expiry, Saudization (Nitaqat), End-of-Service Benefit, GOSI, and government-portal integration (Mudad, Qiwa, GOSI)."
app_email = "hr@alphax.example"
app_license = "MIT"

# Branded, colorful theme + dashboard helpers loaded into the desk
app_include_css = "/assets/alphax_hr_shield/css/alphax_hr.css"
app_include_js = "/assets/alphax_hr_shield/js/alphax_hr.js"

# Frappe's own scheduler replaces the old node-cron loop
scheduler_events = {
    "hourly": [
        "alphax_hr_shield.tasks.run_due_alert_rules",
    ],
    "cron": {
        # 02:00 on the 1st of each month — capture a Saudization snapshot for trends
        "0 2 1 * *": [
            "alphax_hr_shield.tasks.capture_monthly_snapshot",
        ],
    },
}

after_install = "alphax_hr_shield.install.after_install"
after_migrate = "alphax_hr_shield.install.seed_defaults"
