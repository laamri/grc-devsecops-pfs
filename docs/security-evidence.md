# Security evidence register

SCRUM-43 adds a `security-evidence` job to the CI workflow. It collects the
reports produced by the backend tests, frontend validation, secret/dependency
scans, and Semgrep SAST into one `security-evidence-<run-id>` artifact.

Each archive also contains:

- `metadata/run.json`, linking the evidence to repository, workflow run,
  attempt, event, branch, commit, and UTC collection time;
- `SHA256SUMS`, for integrity verification of every collected file;
- the workflow definitions and Terraform files used by the tested revision;
- `README.md`, which describes the evidence layout and missing-report behavior.

The job runs with `if: always()` after the control jobs, so failed controls are
preserved as evidence rather than silently losing the archive. A failed control
must still be triaged in Jira; collecting its report does not bypass a quality
gate. Retention is 90 days in GitHub Actions, after which approved exports can
be copied to the project's secured compliance evidence store.
