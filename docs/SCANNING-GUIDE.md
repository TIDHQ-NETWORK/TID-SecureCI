# Scanning Guide

This guide explains, end to end, how to use TID-SecureCI to **scan a GitHub app
for vulnerabilities and receive a report** — by email, in the GitHub Security
tab, and as downloadable artifacts. It is written so that someone new to
security scanning can follow it, and it defines every term it uses in the
[Glossary](#glossary) at the end.

If you only want the short version, see the
[three-step quickstart in the README](../README.md#scan-your-app-in-three-steps).

## What you get out of it

When a scan finishes you receive, for the exact commit that was scanned:

- an **emailed report** (a branded HTML + Markdown summary with the raw scanner
  output attached) — optional, only when email is configured;
- **code-scanning alerts** in the repository's **Security** tab, line by line;
- **workflow artifacts** containing the raw SARIF and SBOM files;
- a **findings table** on the workflow run's summary page;
- **dependency-review** feedback on pull requests.

## How it works (one paragraph)

TID-SecureCI lives in **one** repository (`TIDHQ-NETWORK/TID-SecureCI`)
and exposes a **reusable workflow**. Your app repository adds a tiny **caller
workflow** that says "run TID-SecureCI against me." On each trigger, the pipeline
checks out the target code, runs several independent scanners in parallel,
uploads results to GitHub, builds a single consolidated report, and (if email is
configured) sends it to you. Nothing is installed in your app repo beyond the
small caller file.

## Prerequisites

- A **GitHub account or organization** that owns both the SecureCI repo and the
  app you want to scan.
- The SecureCI repo must **allow other repos to use its workflow**:
  `SecureCI repo -> Settings -> Actions -> General -> Access ->` allow access
  from your other repositories.
- For email reports: a mailbox that supports **SMTP submission**. Proton Mail
  business is the documented path; see [EMAIL-SETUP.md](EMAIL-SETUP.md).

## Step 1 — Decide what to scan

There are two modes:

| Mode | When to use | What to set |
| --- | --- | --- |
| **Self-scan** | The workflow lives in the same repo you want to scan | Nothing extra — the target defaults to the caller repo and commit |
| **Remote-scan** | You want to scan a *different* repo from the one running the workflow | Set `target_repository`, `target_ref`, and a `checkout_token` with read access to that repo |

Most users self-scan: you add the caller workflow to the app you care about, and
it scans itself on every push and pull request.

## Step 2 — Add the caller workflow to your app

Create `.github/workflows/scan.yml` in your **app** repository. Replace
`YOUR-ORG` with your GitHub org (`TIDHQ-NETWORK`), and adjust the image line
or delete it if your app does not build a container image.

```yaml
name: Secure Scan

on:
  pull_request:
  push:
    branches: [main, master]
  workflow_dispatch:        # lets you run it on demand from the Actions tab
  schedule:
    - cron: "21 4 * * *"    # a daily scan, 04:21 UTC

permissions:
  contents: read
  security-events: write    # required so findings can be written to the Security tab
  pull-requests: write      # the dependency-review job (PR events) needs this
  actions: read             # the sbom job needs this

jobs:
  secureci:
    uses: TIDHQ-NETWORK/TID-SecureCI/.github/workflows/tid-secureci.yml@master
    secrets: inherit        # passes SMTP/email secrets through to the scan
    with:
      enforce: false                       # report only; do not fail the build (yet)
      fail_severity: HIGH,CRITICAL         # which severities count as blocking
      report_recipient: you@example.com    # email this scan's report here
      report_name: My App Security Scan    # title on the report cover page
      # image_ref: ghcr.io/TIDHQ-NETWORK/my-app:${{ github.sha }}  # only if you build an image
```

A ready-made copy lives at [examples/github/scan.yml](../examples/github/scan.yml).

### What each field means

- **`uses:`** — points at the SecureCI reusable workflow, pinned to the `master`
  branch. Pin to a branch or tag that exists in the SecureCI repo.
- **`secrets: inherit`** — forwards your repo/org secrets (the SMTP credentials)
  into the scan so it can email the report.
- **`enforce`** — `false` means findings are reported but the workflow still
  passes. Set `true` later to make findings **block** merges/builds.
- **`fail_severity`** — the severity threshold that matters when `enforce` is on
  (default `HIGH,CRITICAL`).
- **`report_recipient`** — where this scan's email report is sent. If you leave it
  out, the report goes to the TIDHQ owner address.
- **`image_ref`** — an optional built container image for Trivy to scan. Leave it
  out if you have no image.

The full list of knobs is in the [README's Workflow Inputs table](../README.md#workflow-inputs).

## Step 3 — Turn on GitHub's native scanning (recommended)

These live in your **app** repo and complement TID-SecureCI rather than replace
it. Turn them on at `App repo -> Settings -> Code security`:

- **CodeQL default setup** — GitHub's own deep code analysis.
- **Dependabot alerts** + **security updates** — automatic dependency advisories
  and fix PRs.
- **Secret scanning** + **push protection** — blocks committed/known secrets.

## Step 4 — Configure email reports (optional)

Email sends only when both the `smtp_server` and `report_owner` secrets are set.
Set them once at the org level so every caller inherits them. Full steps,
including how to create a Proton SMTP token, are in
[EMAIL-SETUP.md](EMAIL-SETUP.md).

Before relying on a workflow run, you can validate your SMTP credentials locally:

```bash
export SMTP_SERVER=smtp.protonmail.ch SMTP_PORT=587
export SMTP_USERNAME=you@yourdomain.com SMTP_PASSWORD=YOUR_PROTON_TOKEN
export MAIL_FROM=you@yourdomain.com REPORT_RECIPIENT=you@yourdomain.com
python3 scripts/test_report_email.py
```

> `MAIL_FROM` must be a **full email address** that matches your SMTP account
> (e.g. `you@yourdomain.com`), not a bare domain. The helper now rejects an
> invalid `MAIL_FROM` up front instead of failing at the mail server.

## Step 5 — Run the scan

The scan runs automatically on the triggers you configured:

- **`push`** to a tracked branch,
- **`pull_request`** (also adds dependency-review comments),
- **`schedule`** (the nightly cron),
- **`workflow_dispatch`** — run it on demand from `Actions -> Secure Scan -> Run
  workflow`.

## Step 6 — Where the results land

| Output | Where to find it |
| --- | --- |
| Line-level alerts | App repo -> **Security** -> **Code scanning alerts** |
| Raw scanner output (SARIF) | **Actions** -> the run -> **Artifacts** |
| Consolidated report (HTML + Markdown) | the `tid-secureci-report` artifact, and your inbox if email is on |
| Software inventory (SBOM) | the SBOM artifacts (`*.spdx.json`, `*.cdx.json`) |
| At-a-glance findings table | the workflow run's **Summary** page |
| Dependency-review feedback | inline on the **pull request** |

## Scanning your other repos

For each additional app you own, do the same as Step 2: drop a
`.github/workflows/scan.yml` caller into that repo and make sure it can read the
email secrets (org-level secrets cover every repo at once; for a personal
account or a public repo, set them per repo — see the note in
[EMAIL-SETUP.md](EMAIL-SETUP.md)). Each repo then scans and reports itself.

## Scanning a different repository (remote scan)

To scan a repo *other than* the one running the workflow, pass the target:

```yaml
    with:
      target_repository: TIDHQ-NETWORK/some-other-app
      target_ref: main            # optional; blank = default branch
    secrets:
      checkout_token: ${{ secrets.CROSS_REPO_READ_TOKEN }}   # only for PRIVATE targets
```

- **Public target** → no token needed; the default `GITHUB_TOKEN` can read any
  public repo.
- **Private target** → pass `checkout_token`, a fine-grained PAT or app token
  with **read** access to that repo's contents.

## Vetting a third-party app before you use it

A common use: you're considering an open-source GitHub app/library and want a
security read on it *before* you adopt it. You don't own it, but if it's public
you can still scan it on demand.

1. In a repo you own (one that has the email secrets), add the ready-made
   [examples/github/scan-external.yml](../examples/github/scan-external.yml). It
   uses `workflow_dispatch` with an input for the target repo.
2. Go to **Actions -> Scan External Repo -> Run workflow**, type the
   `owner/repo` you want to vet, and run it.
3. You get the same consolidated report by email, plus artifacts.

Two things to know when scanning a repo you don't own:

- **Results don't post to the *target's* Security tab** — you have no write
  access there. Findings come via the **emailed report**, the **workflow
  artifacts** (raw SARIF + SBOM), and the run summary in *your* repo.
- **Keep `enforce: false`** — you're assessing someone else's code, not gating
  your own build, so there's nothing to "block."

This turns the pipeline into a quick due-diligence tool: point it at a candidate
dependency or app, read the Findings Snapshot and SBOM, and decide whether the
code is something you want to depend on.

## Understanding the scanners

Each scanner answers a different question. Running them together is the point —
no single tool sees everything.

| Scanner | What it looks for | Example finding |
| --- | --- | --- |
| **Semgrep** | Insecure code patterns (SAST) + custom AI/ML guardrails | `pickle.load` on untrusted data, `shell=True`, `trust_remote_code=True` |
| **Gitleaks** | Secrets committed to git history | An API key or token in an old commit |
| **OSV-Scanner** | Known-vulnerable dependencies in manifests/lockfiles | A CVE in a pinned npm/PyPI/Cargo package |
| **Trivy** | Filesystem & image vulns, misconfig, secrets, licenses | A vulnerable OS package in a container image |
| **Checkov** | Infrastructure-as-Code misconfiguration | An S3 bucket left public in Terraform |
| **Syft (SBOM)** | A complete inventory of what's in the build | The full list of packages and versions |
| **Dependency review** | Risky dependency changes in a PR | A PR that adds a high-severity vulnerable package |

The custom Semgrep rules are AI/ML-aware: they flag unsafe model loading
(`torch.load`, `joblib.load`, `pickle.load`), `trust_remote_code=True`, and
shell-injection patterns in Python and JavaScript/TypeScript.

## Understanding vulnerabilities and severity

Findings are graded by **severity**, which estimates how damaging and how
exploitable an issue is:

| Severity | Meaning | Typical action |
| --- | --- | --- |
| **CRITICAL** | Easily exploited, severe impact (e.g. remote code execution) | Fix immediately |
| **HIGH** | Serious, exploitable under realistic conditions | Fix promptly |
| **MEDIUM** | Real but limited or harder to exploit | Plan a fix |
| **LOW** | Minor or defense-in-depth | Fix opportunistically |

Two inputs control how severity affects your build:

- **`fail_severity`** (default `HIGH,CRITICAL`) — which severities are treated as
  blocking.
- **`enforce`** — whether blocking findings actually **fail** the workflow.
  Start with `enforce: false` so you can review and tune for a few cycles, then
  switch to `enforce: true` to gate merges.

Trivy additionally uses **`--ignore-unfixed`**, so it reports vulnerabilities that
have an available fix and skips ones with no upstream patch yet — this keeps the
signal actionable.

## Reading the report

The emailed/artifact report has a fixed structure:

1. **Cover page** — branding, repository, report ID, date, classification.
2. **Preface** — what the report is and the reminder that authoritative,
   line-level results live in the Security tab.
3. **Scan Overview** — repository, ref, trigger, enforce mode, severity gate.
4. **Findings Snapshot** — a per-scanner count of findings plus a total.
5. **Job Status** — pass/fail of each scan job.
6. **Where To Look** — links to the Security tab and artifacts.
7. **Reading The Results** — a plain-language note on what each scanner covers.
8. **Scan Map** — a diagram of how source flows through the scanners to outputs.

The **Findings Snapshot counts every result in each SARIF artifact** — including
informational and lower-severity items — so the headline number is a *volume*
indicator, not a count of must-fix issues. Use the Security tab to triage by
severity. A finding count of `0` for a scanner can also mean "nothing to scan"
(for example, OSV finds no lockfiles), not necessarily "perfectly clean."

## Tuning noise and false positives

1. Run with `enforce: false` for a few cycles.
2. Triage alerts in the Security tab; dismiss false positives with a reason.
3. Disable a scanner you don't need with its `enable_*: false` input.
4. Once the signal is clean, set `enforce: true` and add branch protection
   requiring the `Secure Scan / secureci` check before merge.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| No email arrived | `smtp_server` or `report_owner` not set | Set both secrets; email is skipped otherwise |
| `Sender address rejected: need fully-qualified address` | `MAIL_FROM` is a bare domain or malformed | Use a full address that matches `SMTP_USERNAME` |
| Authentication failed | Wrong Proton password | Use the SMTP **submission token**, not your login password |
| "did not find lockfiles" | No manifests for OSV to read | Expected; not an error |
| Findings not in Security tab | Missing `security-events: write` | Add it to the caller's `permissions` |
| `startup_failure` / "nested job is requesting ... but is only allowed none" | Caller `permissions` missing a grant the reusable jobs need | Grant `pull-requests: write` and `actions: read` (plus `contents: read`, `security-events: write`) |
| Remote scan checkout fails with `not our ref` | A `target_ref` was passed that doesn't exist in the target repo | Leave `target_ref` blank to use the target's default branch, or pass a real ref |
| External-repo findings only by email/artifact | Code-scanning SARIF upload is skipped for repos you don't own | Expected; read the emailed report, artifacts, and run summary instead of the Security tab |
| Can't scan another repo | No `checkout_token` | Pass a read-scoped token for the target |

## Glossary

- **SAST (Static Application Security Testing)** — analyzing source code for
  security flaws without running it. Semgrep is the SAST tool here.
- **SARIF (Static Analysis Results Interchange Format)** — the standard JSON
  format scanners emit so GitHub can show findings in the Security tab.
- **SBOM (Software Bill of Materials)** — a machine-readable inventory of every
  component and version in a build. Produced here as SPDX and CycloneDX.
- **SPDX / CycloneDX** — two common SBOM file formats.
- **CVE (Common Vulnerabilities and Exposures)** — a public identifier for a
  specific known vulnerability, e.g. `CVE-2024-12345`.
- **CWE (Common Weakness Enumeration)** — a category of weakness (e.g. SQL
  injection) that many CVEs map to.
- **Severity** — the graded impact/exploitability of a finding: CRITICAL, HIGH,
  MEDIUM, LOW.
- **Secret** — a credential (API key, token, password, private key) that must
  never be committed. Gitleaks and Trivy/Checkov look for these.
- **IaC (Infrastructure as Code)** — infrastructure defined in files (Terraform,
  Kubernetes, Dockerfiles). Checkov and Trivy scan these for misconfiguration.
- **Misconfiguration** — an insecure setting in code or infra (e.g. a public
  storage bucket) rather than a software bug.
- **Manifest / lockfile** — files that declare dependencies (`package.json`,
  `Cargo.lock`, `requirements.txt`). OSV maps these to known vulnerabilities.
- **Reusable workflow** — a GitHub Actions workflow that other repos call with
  `uses:`. TID-SecureCI is one.
- **Caller workflow** — the small workflow in your app repo that invokes the
  reusable workflow.
- **Enforce mode** — whether findings fail the workflow (`enforce: true`) or are
  report-only (`enforce: false`).
- **Severity gate (`fail_severity`)** — which severities count as blocking when
  enforce is on.
- **SMTP submission token** — a Proton-issued password used to send mail from CI
  (Proton Bridge does not work in CI).
- **CodeQL** — GitHub's native deep code-analysis engine; complements this
  pipeline.
- **Dependabot** — GitHub's native dependency-alert and auto-update bot.
- **Dependency review** — a PR-time check that flags risky dependency changes.
