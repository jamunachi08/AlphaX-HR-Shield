# AlphaX HR Shield

The ultimate KSA-focused HR compliance suite for **Frappe / ERPNext**. Runs
natively inside your bench — it reads `Employee` and payroll data directly from
the local database, so there are **no external API keys, no separate database,
and no Node service**.

## Modules

- **Document Compliance** — National ID / Iqama, Passport, Health Insurance and
  configurable custom identity documents, with per-document expiry thresholds,
  risk scoring and a colorful command-center dashboard.
- **Saudization (Nitaqat)** — live Saudization %, company-size detection, and
  band classification by economic activity.
- **End-of-Service Benefit (ESB)** — gratuity per Saudi Labor Law Articles 84
  & 85 (termination vs resignation tiers, pro-rated service).
- **GOSI** — contributory-wage and contribution calculator with configurable
  Saudi / non-Saudi rates, wage floor and ceiling. Defaults reflect the 2026
  schedule under the New Social Insurance Law; **verify against the official
  GOSI schedule for your workforce**.
- **Government Portal Integration** — a pluggable connector framework for
  **Mudad** (WPS), **Qiwa** (contracts / work permits) and **GOSI**, with
  encrypted credential storage and sync logging.

## Install

```bash
bench get-app alphax_hr_shield /path/to/alphax_hr_shield   # or a git URL
bench --site your-site install-app alphax_hr_shield
bench --site your-site migrate
```

Open **AlphaX HR Shield** from the desk workspace, or visit
`/app/alphax-hr-dashboard`.

## Requirements

- Frappe v15+ and the HR / HRMS app (provides the `Employee` doctype).
- Standard Employee fields used: `national_id`, `id_expiry_date`,
  `passport_number`, `valid_upto`, `health_insurance_no`, `date_of_joining`,
  `relieving_date`. Custom-identity fields are mapped in **AlphaX HR Settings**.

## Government portals — important

Mudad, Qiwa and GOSI are not open public APIs. Live connectivity requires
official onboarding and credentials issued by each authority. The integration
layer is production-shaped (credentials, adapters, sync log) and ready to wire
to the official endpoints once you have access; until configured, sync calls
fail safely rather than pretend to succeed.

## Compliance note

ESB, GOSI and Nitaqat figures are decision-support tools, not legal or payroll
advice. Rules and rates change — review against current Saudi Labor Law, MHRSD
and GOSI guidance before relying on outputs.
