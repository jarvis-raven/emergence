#!/usr/bin/env python3
"""
Send email via Proton Bridge SMTP (SSL mode).

Proton Bridge runs SMTP on port 1025 with SSL=true (direct TLS),
NOT STARTTLS. Use SMTP_SSL, not SMTP + starttls().
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
    print(f"Connecting to Proton Bridge SMTP (SSL mode)...")
    server = smtplib.SMTP_SSL('127.0.0.1', 1025, timeout=10)
    
    print(f"Authenticating...")
    server.login(from_addr, password)
    
    print(f"Sending email to {to}...")
    server.send_message(msg)
    
    server.quit()
    print(f"✓ Email sent successfully")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: send_email.py <to> <subject> <body>")
        sys.exit(1)
    
    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    
    send_email(to, subject, body)
