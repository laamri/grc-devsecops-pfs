# DAST evidence and operating procedure

SCRUM-34 adds the `.github/workflows/dast.yml` workflow. It runs an OWASP ZAP
baseline scan against an explicitly authorized test-environment URL. The scan
is passive/baseline-only and does not run active attack rules.

## Running the scan

1. Configure the repository variable `DAST_TARGET_URL` with the approved test
   URL, or provide `target_url` when starting the workflow manually.
2. Start **DAST - Test Environment** from GitHub Actions. A weekly run is also
   scheduled for the configured repository variable.
3. Download the `dast-reports-<run-id>` artifact. It contains the HTML and JSON
   reports, tied to the workflow run and commit.

The workflow rejects missing, non-HTTP(S), or whitespace-containing targets.
Only URLs approved by the project owner may be configured. The quality gate
fails when the ZAP report contains a High or Critical finding. Medium/Low
findings remain in the report for triage.

## False positives and safety

Do not scan production or an environment without written authorization. Record
false positives in the Jira issue and retain the finding, rationale, reviewer,
and expiry date in the evidence record; do not hide a whole rule or lower the
severity gate. The baseline scan is intentionally bounded to avoid destructive
requests.
