#!/usr/bin/env python3
"""
Send email via Proton Bridge SMTP (SSL mode).

Proton Bridge runs SMTP on port 1025 with SSL=true (direct TLS),
NOT STARTTLS. Use SMTP_SSL, not SMTP + starttls().

Usage:
  # Body as argument (short messages only)
  send_email.py <to> <subject> "short body"
  
  # Body from stdin (recommended for long/multiline)
  echo "email body" | send_email.py <to> <subject> --stdin
  cat message.txt | send_email.py <to> <subject> --stdin
  
  # Body from file
  send_email.py <to> <subject> --file message.txt
"""
import smtplib
import subprocess
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_password():
    """Retrieve password from macOS keychain."""
    return subprocess.check_output([
        'security', 'find-generic-password',
        '-a', 'PROTON_BRIDGE_PASS_JARVIS', '-w'
    ]).decode('utf-8').strip()

def send_email(to: str, subject: str, body: str, from_addr: str = 'jarvis.raven@proton.me'):
    """Send email via Proton Bridge SMTP."""
    password = get_password()
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # Connect using SMTP_SSL (direct TLS), NOT SMTP + starttls
    print(f"Connecting to Proton Bridge SMTP (SSL mode)...", file=sys.stderr)
    server = smtplib.SMTP_SSL('127.0.0.1', 1025, timeout=10)
    
    print(f"Authenticating...", file=sys.stderr)
    server.login(from_addr, password)
    
    print(f"Sending email to {to}...", file=sys.stderr)
    server.send_message(msg)
    
    server.quit()
    print(f"✓ Email sent successfully to {to}", file=sys.stderr)
    print(f"  Subject: {subject}", file=sys.stderr)
    print(f"  Body length: {len(body)} chars", file=sys.stderr)
    
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: send_email.py <to> <subject> [body | --stdin | --file <path>]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  send_email.py user@example.com 'Subject' 'Short body'", file=sys.stderr)
        print("  cat message.txt | send_email.py user@example.com 'Subject' --stdin", file=sys.stderr)
        print("  send_email.py user@example.com 'Subject' --file message.txt", file=sys.stderr)
        sys.exit(1)
    
    to = sys.argv[1]
    subject = sys.argv[2]
    
    # Determine body source
    if len(sys.argv) >= 4:
        if sys.argv[3] == '--stdin':
            # Read body from stdin
            body = sys.stdin.read()
        elif sys.argv[3] == '--file' and len(sys.argv) >= 5:
            # Read body from file
            with open(sys.argv[4], 'r') as f:
                body = f.read()
        else:
            # Body as argument (legacy mode, not recommended for long text)
            body = sys.argv[3]
    else:
        # No body provided, read from stdin
        print("Reading body from stdin...", file=sys.stderr)
        body = sys.stdin.read()
    
    if not body or not body.strip():
        print("⚠ Warning: Email body is empty!", file=sys.stderr)
        confirm = input("Send anyway? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.", file=sys.stderr)
            sys.exit(1)
    
    send_email(to, subject, body)

if __name__ == '__main__':
    main()
