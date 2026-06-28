#!/usr/bin/env python3
"""Send a test report email through SMTP (e.g. Proton SMTP submission).

This mirrors what the TID-SecureCI workflow's "Email report" step does, so you
can validate your SMTP/Proton credentials and confirm you receive the report
BEFORE pushing the workflow to GitHub.

Credentials are read from environment variables ONLY -- nothing is written to
disk, so no secrets end up in the repo:

  SMTP_SERVER        SMTP host (Proton: smtp.protonmail.ch)
  SMTP_PORT          SMTP port (default 587, STARTTLS; 465 = implicit TLS)
  SMTP_USERNAME      SMTP user (Proton: your full Proton address)
  SMTP_PASSWORD      SMTP password (Proton: the SMTP submission token)
  MAIL_FROM          From address (default: SMTP_USERNAME)
  REPORT_RECIPIENT   Where to send the test (default: MAIL_FROM)

It attaches report/report.html and report/report.md if they exist; otherwise it
sends a short placeholder body so you can still confirm delivery.

Usage:
  export SMTP_SERVER=smtp.protonmail.ch SMTP_PORT=587
  export SMTP_USERNAME=you@yourdomain.com SMTP_PASSWORD=YOUR_PROTON_TOKEN
  export MAIL_FROM=you@yourdomain.com REPORT_RECIPIENT=you@yourdomain.com
  python3 scripts/test_report_email.py
"""

import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"ERROR: environment variable {name} is required.")
    return value


def main() -> int:
    server = require("SMTP_SERVER")
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = require("SMTP_USERNAME")
    password = require("SMTP_PASSWORD")
    mail_from = os.environ.get("MAIL_FROM", "").strip() or username
    if "@" not in mail_from:
        sys.exit(
            f"ERROR: MAIL_FROM must be a full email address (got '{mail_from}'). "
            "For Proton it must match SMTP_USERNAME, e.g. ops@tidhq.net."
        )
    recipient = os.environ.get("REPORT_RECIPIENT", "").strip() or mail_from

    msg = EmailMessage()
    msg["From"] = f"TIDHQ.NETWORK SecureCI <{mail_from}>"
    msg["To"] = recipient
    msg["Subject"] = "TIDHQ.NETWORK | SecureCI email test"

    html = Path("report/report.html")
    md = Path("report/report.md")

    if html.exists():
        msg.set_content(
            "This is a TID-SecureCI email test. The HTML report is attached."
        )
        msg.add_alternative(html.read_text(encoding="utf-8"), subtype="html")
    else:
        msg.set_content(
            "This is a TID-SecureCI email test. No report/report.html was found, "
            "so this is a plain placeholder. If you received this, your SMTP "
            "credentials work."
        )

    for path in (html, md):
        if path.exists():
            data = path.read_bytes()
            subtype = "html" if path.suffix == ".html" else "markdown"
            msg.add_attachment(
                data, maintype="text", subtype=subtype, filename=path.name
            )

    print(f"Connecting to {server}:{port} as {username} ...")
    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port, context=context, timeout=30) as s:
                s.login(username, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(server, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=context)
                s.ehlo()
                s.login(username, password)
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        sys.exit(
            f"ERROR: authentication failed: {e}\n"
            "For Proton, SMTP_PASSWORD must be the SMTP submission TOKEN "
            "(not your login password), and SMTP_USERNAME/MAIL_FROM must match "
            "the address the token was issued for."
        )
    except Exception as e:  # noqa: BLE001 - surface any send failure clearly
        sys.exit(f"ERROR: failed to send: {e}")

    print(f"Sent test report to {recipient}. Check that inbox (and spam).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
