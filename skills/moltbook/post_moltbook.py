#!/usr/bin/env python3
"""
Post to Moltbook with security validation.

Usage:
    python3 post_moltbook.py "Post text here" [--reply-to ID]

Features:
- Creates posts on Moltbook
- Optional reply to existing posts
- Validates own content before posting
"""
import subprocess
import sys
import json
import requests


def get_api_key():
    """Retrieve Moltbook API key from keychain."""
    try:
        return (
            subprocess.check_output(
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    "openclaw",
                    "-a",
                    "moltbook_api_key",
                    "-w",
                ]
            )
            .decode("utf-8")
            .strip()
        )
    except subprocess.CalledProcessError:
        print("⚠️  Moltbook API key not found in keychain", file=sys.stderr)
        print(
            "   Store with: security add-generic-password -s 'openclaw' -a 'moltbook_api_key' -w 'YOUR_KEY'",
            file=sys.stderr,
        )
        sys.exit(1)


def post_to_moltbook(text, reply_to=None):
    """Post to Moltbook."""
    api_key = get_api_key()

    url = "https://moltbook.com/api/posts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "OpenClaw/Jarvis",
    }

    payload = {"text": text}

    if reply_to:
        payload["reply_to"] = reply_to
        print(f"📝 Posting reply to {reply_to}...", file=sys.stderr)
    else:
        print(f"📝 Creating new post...", file=sys.stderr)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        post_id = result.get("id", "unknown")
        print(f"✓ Post created: {post_id}", file=sys.stderr)

        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("⚠️  Authentication failed - check API key", file=sys.stderr)
        elif e.response.status_code == 429:
            print("⚠️  Rate limited - try again later", file=sys.stderr)
        elif e.response.status_code == 400:
            print(f"⚠️  Bad request: {e.response.text}", file=sys.stderr)
        else:
            print(f"⚠️  HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  Failed to post: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Post to Moltbook")
    parser.add_argument("text", help="Post text")
    parser.add_argument("--reply-to", help="Post ID to reply to")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    # Validate text length (Moltbook has limits)
    if len(args.text) > 5000:
        print("⚠️  Post too long (max 5000 characters)", file=sys.stderr)
        sys.exit(1)

    if len(args.text.strip()) == 0:
        print("⚠️  Post text cannot be empty", file=sys.stderr)
        sys.exit(1)

    result = post_to_moltbook(args.text, reply_to=args.reply_to)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✓ Posted successfully!")
        print(f"   ID: {result.get('id')}")
        print(f"   URL: https://moltbook.com/posts/{result.get('id')}")


if __name__ == "__main__":
    main()
