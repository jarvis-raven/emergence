#!/usr/bin/env python3
"""
Check Proton Bridge email inbox with prompt injection security.

Usage:
    python3 check_email.py [--limit N] [--quarantine]

Features:
- Reads INBOX via IMAP (STARTTLS)
- Runs all external content through check-injection.sh
- Quarantines suspicious emails
- Returns structured data
"""
import imaplib
import subprocess
import email
import sys
import json
from email.header import decode_header
from datetime import datetime


def get_password():
    """Retrieve password from macOS keychain."""
    return (
        subprocess.check_output(
            ["security", "find-generic-password", "-a", "PROTON_BRIDGE_PASS_JARVIS", "-w"]
        )
        .decode("utf-8")
        .strip()
    )


def check_injection(text):
    """Run content through security checker."""
    try:
        result = subprocess.run(
            ["/Users/jarvis/.openclaw/bin/check-injection.sh", "--json"],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=5,
        )
        return json.loads(result.stdout.decode("utf-8"))
    except Exception as e:
        print(f"⚠️  Security check failed: {e}", file=sys.stderr)
        return {"severity": "UNKNOWN", "score": 0, "exit_code": 0}


def decode_header_value(header_value):
    """Decode email header safely."""
    if not header_value:
        return ""

    decoded_parts = decode_header(header_value)
    result = []

    for content, encoding in decoded_parts:
        if isinstance(content, bytes):
            try:
                result.append(content.decode(encoding or "utf-8", errors="replace"))
            except BaseException:
                result.append(content.decode("utf-8", errors="replace"))
        else:
            result.append(str(content))

    return "".join(result)


def extract_body(msg):
    """Extract email body text."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="replace")
                except BaseException:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
        except BaseException:
            pass

    return body.strip()


def check_emails(limit=10, quarantine_threshold=2):
    """Check inbox and return structured results."""
    password = get_password()

    # Connect to IMAP
    print("📬 Connecting to Proton Bridge IMAP...", file=sys.stderr)
    mail = imaplib.IMAP4("127.0.0.1", 1143)
    mail.starttls()
    mail.login("jarvis.raven@proton.me", password)
    mail.select("INBOX")

    # Search for all emails
    status, messages = mail.search(None, "ALL")
    msg_ids = messages[0].split()

    total = len(msg_ids)
    print(f"📊 Found {total} emails in INBOX", file=sys.stderr)

    # Get last N emails
    results = []
    check_ids = msg_ids[-limit:] if limit else msg_ids

    for msg_id in reversed(check_ids):
        status, msg_data = mail.fetch(msg_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decode headers
                subject = decode_header_value(msg.get("Subject", ""))
                from_addr = decode_header_value(msg.get("From", ""))
                date = msg.get("Date", "")

                # Extract body
                body = extract_body(msg)

                # Security check on subject + body
                combined_text = f"{subject}\n\n{body}"
                security = check_injection(combined_text)

                # Determine if quarantined
                quarantined = security["exit_code"] >= quarantine_threshold

                result = {
                    "id": msg_id.decode(),
                    "from": from_addr,
                    "subject": subject,
                    "date": date,
                    "body_length": len(body),
                    "security": security,
                    "quarantined": quarantined,
                }

                results.append(result)

    mail.logout()

    return {"total_emails": total, "checked": len(results), "results": results}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check Proton Bridge email inbox")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent emails to check")
    parser.add_argument(
        "--quarantine-threshold",
        type=int,
        default=2,
        help="Exit code threshold for quarantine (default: 2=MEDIUM)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")

    args = parser.parse_args()

    data = check_emails(limit=args.limit, quarantine_threshold=args.quarantine_threshold)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        # Human-readable output
        print(f"\n📬 Email Check Results")
        print(f"Total in inbox: {data['total_emails']}")
        print(f"Checked: {data['checked']}")
        print()

        clean_count = sum(1 for r in data["results"] if not r["quarantined"])
        quarantine_count = sum(1 for r in data["results"] if r["quarantined"])

        print(f"✓ Clean: {clean_count}")
        if quarantine_count > 0:
            print(f"⚠️  Quarantined: {quarantine_count}")
        print()

        for result in data["results"]:
            status_icon = "⚠️" if result["quarantined"] else "✓"
            severity = result["security"]["severity"]
            score = result["security"]["score"]

            print(f"{status_icon} [{severity}:{score}] From: {result['from']}")
            print(f"   Subject: {result['subject']}")
            print(f"   Date: {result['date']}")

            if result["quarantined"]:
                print(f"   🛡️  QUARANTINED - Review before processing")

            print()


if __name__ == "__main__":
    main()
