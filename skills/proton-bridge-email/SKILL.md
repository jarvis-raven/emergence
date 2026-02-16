---
name: proton-bridge-email
description: "Send and receive email via Proton Bridge SMTP/IMAP. CRITICAL: Proton Bridge uses SSL mode (direct TLS), NOT STARTTLS. Use SMTP_SSL for sending."
homepage: https://proton.me/mail/bridge
metadata:
  {
    "openclaw":
      {
        "emoji": "📧",
        "requires": { "apps": ["Proton Mail Bridge"] }
      }
  }
---

# Proton Bridge Email

**⚠️ CRITICAL:** Proton Bridge SMTP runs with `ssl=true` - use **`SMTP_SSL`** (direct TLS), NOT `SMTP` + `starttls()`!

## Prerequisites

1. Proton Mail Bridge running (`open -a "Proton Mail Bridge"`)
2. Password stored in keychain: `PROTON_BRIDGE_PASS_JARVIS`

## Sending Email

**Use the helper script:**
```bash
python3 ~/.openclaw/workspace/scripts/send_email.py \
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

## Files

- Helper script: `~/.openclaw/workspace/scripts/send_email.py`
- Config notes: `~/.openclaw/workspace/TOOLS.md`
- Correspondence: `~/.openclaw/workspace/memory/correspondence/`
