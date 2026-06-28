# Try It — Run a Scan and Get a Report

This guide is for **anyone who wants to test TID-SecureCI** by pointing it at a
GitHub repository and getting a security report back. It covers the one-line
command, the click-only web method, and how to let **other people** run their own
scans.

If you just want the single command, it's here:

```bash
gh workflow run scan-external.yml \
  -R TIDHQ-NETWORK/TID-SecureCI \
  -f target_repository=OWNER/REPO \
  -f report_recipient=you@example.com
```

Everything below explains the options, the no-CLI path, and how to share it.

---

## What you need

- A target repo to scan — **any public `owner/repo`** works (e.g. a library you're
  evaluating). Private targets need a read token; see [Private targets](#private-targets).
- An **email address** to receive the report (`report_recipient`).
- To trigger it from the CLI: the [GitHub CLI](https://cli.github.com) installed and
  signed in (`gh auth login`), plus permission to run workflows in
  `TIDHQ-NETWORK/TID-SecureCI`. No special access? Use the [web method](#option-b--no-cli-the-web-ui).

> Email is sent from the TIDHQ Proton account that is already configured on the
> SecureCI repo, so testers only supply **where** the report should go.

---

## Option A — one command (GitHub CLI)

```bash
# Scan a public repo and email the report to yourself
gh workflow run scan-external.yml \
  -R TIDHQ-NETWORK/TID-SecureCI \
  -f target_repository=matthart1983/netwatch \
  -f report_recipient=you@example.com
```

Optional: pin a branch, tag, or commit (leave blank to use the default branch):

```bash
gh workflow run scan-external.yml \
  -R TIDHQ-NETWORK/TID-SecureCI \
  -f target_repository=matthart1983/netwatch \
  -f target_ref=main \
  -f report_recipient=you@example.com
```

### Inputs

| Input | Required | Meaning |
| --- | --- | --- |
| `target_repository` | yes | The `owner/repo` to scan |
| `target_ref` | no | Branch, tag, or SHA. Blank = the target's default branch |
| `report_recipient` | no | Where the report is emailed. Blank = the TIDHQ owner address |

### Watch it and download the results

```bash
# Get the run that just started
RUN=$(gh run list -R TIDHQ-NETWORK/TID-SecureCI -w scan-external.yml -L1 --json databaseId -q '.[0].databaseId')

# Follow it live
gh run watch "$RUN" -R TIDHQ-NETWORK/TID-SecureCI

# Download the report + raw SARIF + SBOM
gh run download "$RUN" -R TIDHQ-NETWORK/TID-SecureCI
```

When it finishes you get:

- 📧 an **emailed report** (branded HTML + Markdown, with a Detailed Findings table
  and raw scanner output attached);
- 📦 **artifacts** on the run — `tid-secureci-report` (HTML/Markdown) plus the raw
  SARIF and SBOM files;
- 📊 a **findings table** on the run's Summary page.

> Scanning a repo you don't own? Findings **don't** post to that repo's Security tab
> (you have no write access there). You get them by email, in the artifacts, and on
> the run summary.

---

## Option B — no CLI (the web UI)

Anyone with access to the repo can run it from a browser:

1. Open **[Actions](https://github.com/TIDHQ-NETWORK/TID-SecureCI/actions) → Scan
   External Repo**.
2. Click **Run workflow**.
3. Fill in:
   - **target_repository** — `owner/repo` to scan
   - **target_ref** — leave blank for the default branch
   - **report_recipient** — your email
4. Click **Run workflow**. Open the run to watch progress; the report emails when it
   finishes and is attached to the run as artifacts.

---

## Letting other people test it

There are two ways to give others a way to get reports.

### 1. Invite them to run the hosted workflow (simplest)

Give the person **read/write (or "Actions") access** to
`TIDHQ-NETWORK/TID-SecureCI`, then point them at this page. They use Option A or B
above and put **their own email** in `report_recipient`. The report is emailed to
them; the TIDHQ owner address is BCC'd so you keep a copy of every scan.

This is the best path for **demos and evaluations** — testers need nothing but a
target repo and an email.

### 2. They add the scanner to their own repo (self-serve)

If someone wants TID-SecureCI running on **their** repo on every push/PR, they add a
caller workflow at `.github/workflows/scan.yml` (copy
[`examples/github/scan.yml`](../examples/github/scan.yml)):

```yaml
name: Secure Scan
on:
  pull_request:
  push:
    branches: [main, master]
  workflow_dispatch:
permissions:
  contents: read
  security-events: write
  pull-requests: write
  actions: read
jobs:
  secureci:
    uses: TIDHQ-NETWORK/TID-SecureCI/.github/workflows/tid-secureci.yml@master
    secrets: inherit
    with:
      enforce: false
      report_recipient: them@example.com
```

Two things to know:

- The SecureCI repo must **allow their repo to use the workflow**
  (`SecureCI repo → Settings → Actions → General → Access`).
- **Email only works when the caller can read the SMTP secrets.** Repos **inside the
  TIDHQ-NETWORK org** inherit org-level secrets; repos **outside** the org cannot use
  the TIDHQ Proton token via `secrets: inherit`. Outside users either set their own
  SMTP secrets or just use the artifacts + Security tab (email is skipped, the rest
  runs unchanged). See [EMAIL-SETUP.md](EMAIL-SETUP.md).

---

## Private targets

To scan a **private** repository, pass a token that can read it. Set it once as a
secret and uncomment the `checkout_token` line in
[`examples/github/scan-external.yml`](../examples/github/scan-external.yml):

```bash
gh secret set CROSS_REPO_READ_TOKEN -R TIDHQ-NETWORK/TID-SecureCI
```

```yaml
    secrets:
      checkout_token: ${{ secrets.CROSS_REPO_READ_TOKEN }}
```

Use a fine-grained PAT or app token with **read** access to the target's contents.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `could not find any workflows named scan-external.yml` | Run with `-R TIDHQ-NETWORK/TID-SecureCI`; the workflow lives in that repo |
| `HTTP 403` / can't dispatch | You need write/Actions permission on `TIDHQ-NETWORK/TID-SecureCI`, or use the web UI |
| Run is red with `not our ref` | The `target_ref` doesn't exist in the target — leave it blank or pass a real branch/SHA |
| No email arrived | SMTP isn't configured for that caller, or `report_recipient` was empty — check spam, then [EMAIL-SETUP.md](EMAIL-SETUP.md) |
| Findings missing from the target's Security tab | Expected for repos you don't own — read the email/artifacts instead |

A deeper walkthrough (reading the report, severity, every input) is in
[SCANNING-GUIDE.md](SCANNING-GUIDE.md).
