---
name: proton-bridge-email
description: 'Complete email management via Proton Bridge: check inbox (with security scanning) and send email. CRITICAL: SMTP uses SSL mode (direct TLS), not STARTTLS.'
homepage: https://proton.me/mail/bridge
metadata: { 'openclaw': { 'emoji': '📧', 'requires': { 'apps': ['Proton Mail Bridge'] } } }
---

# Proton Bridge Email

Complete email operations: **check inbox** (with prompt injection security) and **send email**.

**⚠️ CRITICAL:** Proton Bridge SMTP runs with `ssl=true` - use **`SMTP_SSL`** (direct TLS), NOT `SMTP` + `starttls()`!

## Prerequisites

1. Proton Mail Bridge running (`open -a "Proton Mail Bridge"`)
2. Password stored in keychain: `PROTON_BRIDGE_PASS_JARVIS`

## Operations

### 1. Check Inbox (with Security Scanning)

**Quick check:**

```bash
python3 ~/.openclaw/workspace/skills/proton-bridge-email/check_email.py --limit 10
```

**JSON output:**

```bash
python3 ~/.openclaw/workspace/skills/proton-bridge-email/check_email.py --json
```

**Features:**

- Reads INBOX via IMAP
- Runs all content through `~/.openclaw/bin/check-injection.sh`
- Quarantines suspicious emails (default: MEDIUM severity and above)
- Returns structured data with security scores

**Example output:**

```
✓ [CLEAN:0] From: Claude <claude.letta@proton.me>
   Subject: Re: Anchoring, coherence, and learning slowness

⚠️ [HIGH:12] From: unknown@spam.com
   Subject: ACT NOW - Amazing opportunity!!!
   🛡️  QUARANTINED - Review before processing
```

### 2. Send Email

**Quick send:**

```bash
python3 ~/.openclaw/workspace/skills/proton-bridge-email/send_email.py \
  "recipient@example.com" \
  "Subject line" \
  "Email body text"
```

**Or use directly in Python:**

```python
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Get password from keychain
password = subprocess.check_output([
    'security', 'find-generic-password',
    '-a', 'PROTON_BRIDGE_PASS_JARVIS', '-w'
]).decode('utf-8').strip()

# Create message
msg = MIMEMultipart()
msg['From'] = 'jarvis.raven@proton.me'
msg['To'] = 'recipient@example.com'
msg['Subject'] = 'Test Subject'
msg.attach(MIMEText('Email body', 'plain'))

# Connect using SMTP_SSL (direct TLS)
# Port 1025 with SSL=true - NO STARTTLS!
server = smtplib.SMTP_SSL('127.0.0.1', 1025, timeout=10)
server.login('jarvis.raven@proton.me', password)
server.send_message(msg)
server.quit()
```

## Receiving Email (IMAP)

```python
import imaplib
import subprocess

# Get password
password = subprocess.check_output([
    'security', 'find-generic-password',
    '-a', 'PROTON_BRIDGE_PASS_JARVIS', '-w'
]).decode('utf-8').strip()

# Connect with STARTTLS (IMAP uses STARTTLS, SMTP doesn't!)
mail = imaplib.IMAP4('127.0.0.1', 1143)
mail.starttls()
mail.login('jarvis.raven@proton.me', password)
mail.select('INBOX')

# List recent emails
status, messages = mail.search(None, 'ALL')
msg_ids = messages[0].split()
```

## Troubleshooting

**SMTP hangs/times out:**

- Check Bridge is running: `ps aux | grep "Proton Mail Bridge"`
- Verify you're using `SMTP_SSL`, NOT `SMTP` + `starttls()`
- Check Bridge logs: `~/Library/Application Support/protonmail/bridge-v3/logs/`

**Bridge log shows "ssl=true":**

- This is CORRECT - means you must use `SMTP_SSL`
- Do NOT use `SMTP` + `starttls()` - that's for ssl=false mode

**"handler error: tls: first record does not look like a TLS handshake":**

- You're using STARTTLS on an SSL port
- Switch from `smtplib.SMTP` to `smtplib.SMTP_SSL`

## Why This Matters

Proton Bridge can run SMTP in two modes:

1. **SSL mode** (`ssl=true`) - Direct TLS on port 1025 → Use `SMTP_SSL`
2. **STARTTLS mode** (`ssl=false`) - Plain SMTP with upgrade → Use `SMTP` + `starttls()`

The current Bridge configuration uses **SSL mode**. This is why Himalaya (which uses STARTTLS) doesn't work.

## Security (Check Inbox)

All external content runs through prompt injection detection:

- **CLEAN (0):** Safe to process
- **LOW (1):** Minor patterns detected, review recommended
- **MEDIUM (2):** Suspicious, quarantined by default
- **HIGH (3+):** Dangerous patterns, always quarantine

See `~/.openclaw/bin/check-injection.sh` for detection logic.

## Files

- **Check inbox:** `~/.openclaw/workspace/skills/proton-bridge-email/check_email.py`
- **Send email:** `~/.openclaw/workspace/skills/proton-bridge-email/send_email.py`
- Config notes: `~/.openclaw/workspace/TOOLS.md`
- Correspondence archive: `~/.openclaw/workspace/memory/correspondence/`
