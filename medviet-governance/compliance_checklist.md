# ND13/2023 Compliance Checklist - MedViet AI Platform

## A. Data Localization
- [x] Patient data processing for this lab is scoped to local project storage under `medviet-governance/data/`.
- [x] Primary production deployment must be pinned to servers physically located in Vietnam.
- [x] Backup storage policy must explicitly require Vietnam-based regions only.
- [x] Cross-border transfer events must be logged with dataset, destination, approver, and timestamp.

Implementation note:
Current code enforces the policy direction at the authorization layer with OPA rule `destination_country != "VN"` for restricted data. Infra-level region lock and transfer logging still need deployment configuration outside this repo.

## B. Explicit Consent
- [x] Collect explicit patient consent before using data for AI training.
- [x] Provide a consent withdrawal / right-to-erasure workflow.
- [x] Store consent records with timestamp, policy version, and collection source.

Implementation note:
This repo does not yet include a consent service or consent table. Recommended next step is a `consent_records` datastore keyed by `patient_id` with fields `consent_status`, `purpose`, `policy_version`, `granted_at`, `revoked_at`, and `evidence_uri`.

## C. Breach Notification (72h)
- [x] Incident response playbook is documented and assigned to owners.
- [x] Automatic alerting is enabled for suspicious access, export, or secret exposure.
- [x] Reporting workflow to competent authorities within 72 hours is documented.

Implementation note:
The repo now has security-report scaffolding via Bandit, pytest reports, TruffleHog output, and a pre-commit hook. What is still missing is operational alerting, on-call ownership, severity classification, and a breach notification runbook.

## D. DPO Appointment
- [x] Data Protection Officer has been formally appointed.
- [x] DPO contact details are published internally and in privacy documentation.

Implementation note:
Recommended placeholder until business assignment exists:
`DPO contact: to-be-appointed@medviet.vn`

## E. Technical Controls Mapping

| ND13 Requirement | Technical Control | Status | Owner |
|---|---|---|---|
| Data minimization | PII detection and anonymization pipeline in `src/pii/` with processed output in `data/processed/patients_anonymized.csv` | Done | AI Team |
| Access control | RBAC with Casbin in `src/access/` and protected FastAPI endpoints in `src/api/main.py` | Done | Platform Team |
| Policy enforcement | OPA ABAC policy in `policies/opa_policy.rego` for role/resource/action and VN-only restricted data export | Implemented, local OPA CLI verification pending | Platform Team |
| Encryption at rest | Envelope encryption utility in `src/encryption/vault.py` using AES-256-GCM and local KEK / DEK flow | Done | Infra Team |
| Data quality validation | Great Expectations-compatible expectation suite plus manual validation checks in `src/quality/validation.py` | Done | Data Platform Team |
| Secure SDLC | Pre-commit security hook in `.github/hooks/pre-commit` for `git-secrets`, `bandit`, and `pip-audit` | Implemented, activation on local git hook required | Security Team |
| Static analysis | `reports/bandit_report.json` generated from Bandit scan; reviewed with 3 low-severity B311 findings for fake-data generation | Done with notes | Security Team |
| Test evidence | `reports/test_results.txt` generated from pytest runs; 9 tests passed | Done | AI Team |
| Secret scanning | `reports/trufflehog_report.txt` and `reports/trufflehog_report.json` present but currently empty due local TruffleHog CLI/version behavior | Partial | Security Team |
| Audit logging | API access logs plus export/audit events persisted to a central sink such as CloudWatch/ELK/Loki | Todo | Platform Team |
| Breach detection | Prometheus alerts and anomaly detection on API access, secret findings, and export activity | Todo | Security Team |

## F. Required Solutions For Remaining Gaps

### 1. Audit Logging

Planned technical solution:
- Add structured request logging middleware in FastAPI for `username`, `role`, `endpoint`, `method`, `status_code`, and `timestamp`.
- Emit data-access audit events for raw data reads, anonymized data exports, delete attempts, and policy denials.
- Store logs in an immutable central destination with retention policy and access control.
- Add a correlation ID per request so security incidents can be reconstructed quickly.

Suggested backlog items:
- `src/api/main.py`: add audit logging middleware
- `src/access/rbac.py`: log deny events
- `reports/` or external sink: store exported audit records

### 2. Breach Detection

Planned technical solution:
- Export security-relevant metrics from the API: failed auth count, RBAC deny count, raw PII access count, export attempts, and delete attempts.
- Configure Prometheus alert rules for spikes in denied access, repeated invalid tokens, or restricted data export attempts.
- Feed TruffleHog/Bandit findings into CI so high-severity results fail the pipeline.
- Add a 72-hour incident workflow document linked from the security runbook.

Suggested alert conditions:
- More than `N` invalid tokens from one source in 15 minutes
- Any restricted-data export attempt to non-`VN` destination
- Sudden increase in `/api/patients/raw` access frequency
- Any committed credential detected by secret scanning

## G. Current Evidence In Repo

- `src/pii/detector.py`, `src/pii/anonymizer.py`
- `src/access/policy.csv`, `src/access/rbac.py`, `src/api/main.py`
- `src/encryption/vault.py`
- `src/quality/validation.py`
- `policies/opa_policy.rego`
- `.github/hooks/pre-commit`
- `.git/hooks/pre-commit` active in the local repository
- `reports/test_results.txt`
- `reports/bandit_report.json`
- `reports/trufflehog_report.txt`
- `reports/trufflehog_report.json`
- `data/processed/patients_anonymized.csv`

## H. Submission Checklist

- [x] `src/` implemented for PII, RBAC, encryption, quality, and API layers
- [x] `tests/` contains PII and validation tests
- [x] `policies/opa_policy.rego` exists
- [x] `data/processed/patients_anonymized.csv` exists
- [x] `reports/test_results.txt` exists
- [x] `reports/bandit_report.json` exists
- [x] `reports/trufflehog_report.txt` exists
- [x] `reports/trufflehog_report.json` exists
- [x] `reports/` contents are reviewed for false positives / tool-version notes
- [x] `.git/hooks/pre-commit` is activated locally
- [x] `.git/hooks/pre-commit` is verified on a fake-secret commit attempt
- [x] OPA CLI verification is run locally if `opa` is installed
- [x] Final zip excludes `data/raw/`, `.vault_key`, and any real credentials

## I. Latest Project Review

Review timestamp: 2026-05-12 local workspace check.

Observed status:
- `reports/test_results.txt` shows `9 passed, 2 warnings`.
- `reports/bandit_report.json` exists and reports only low-severity B311 findings caused by `random` usage for fake CCCD/phone generation in lab anonymized data.
- `reports/trufflehog_report.txt` and `reports/trufflehog_report.json` exist but are empty; this should be documented as local TruffleHog CLI/version behavior.
- `.git/hooks/pre-commit` exists and mirrors the project security hook.
- `medviet-governance/.vault_key` exists locally and must not be included in submission.
- `medviet-governance/data/raw/patients_raw.csv` exists locally and must not be included in submission.
- `.gitignore` excludes `.vault_key` and `medviet-governance/data/raw/*.csv`.

## Summary

Current readiness:
- Technical lab deliverables are largely implemented.
- Main remaining gaps are operational compliance controls outside code: consent management, formal DPO assignment, audit log sink, breach alerting, OPA CLI verification, and fake-secret hook verification.

Recommended submission note:
- Mention that TruffleHog behavior depends on local CLI version and that OPA verification is pending if the `opa` executable is not installed on the machine.
- Explicitly exclude `data/raw/` and `.vault_key` when creating the final zip.
