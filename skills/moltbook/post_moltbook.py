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
        return subprocess.check_output([
            'security', 'find-generic-password',
            '-s', 'openclaw',
            '-a', 'moltbook_api_key',
            '-w'
        ]).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        print("⚠️  Moltbook API key not found in keychain", file=sys.stderr)
        print("   Store with: security add-generic-password -s 'openclaw' -a 'moltbook_api_key' -w 'YOUR_KEY'", file=sys.stderr)
        sys.exit(1)

def post_to_moltbook(title=None, content=None, submolt="general", comment_on=None, reply_to=None):
    """Post to Moltbook v1 API.
    
    Args:
        title: Post title (required for new posts)
        content: Post content/body
        submolt: Submolt to post in (default: general)
        comment_on: Post ID to comment on
        reply_to: Comment ID to reply to (used with comment_on)
    """
    api_key = get_api_key()
    
    # IMPORTANT: Must use www.moltbook.com - non-www strips auth headers!
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "OpenClaw/Jarvis"
    }
    
    if comment_on:
        # Creating a comment
        url = f"https://www.moltbook.com/api/v1/posts/{comment_on}/comments"
        payload = {"content": content}
        if reply_to:
            payload["parent_id"] = reply_to
        print(f"💬 Adding comment to post {comment_on}...", file=sys.stderr)
    else:
        # Creating a new post
        url = "https://www.moltbook.com/api/v1/posts"
        payload = {
            "title": title,
            "content": content,
            "submolt": submolt
        }
        print(f"📝 Creating new post in r/{submolt}...", file=sys.stderr)
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if comment_on:
            print(f"✓ Comment created", file=sys.stderr)
        else:
            post_id = result.get('post', {}).get('id', result.get('id', 'unknown'))
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
    
    parser = argparse.ArgumentParser(description='Post to Moltbook v1 API')
    parser.add_argument('--title', '-t', help='Post title (required for new posts)')
    parser.add_argument('--content', '-c', help='Post content/body')
    parser.add_argument('--submolt', '-s', default='general', help='Submolt to post in (default: general)')
    parser.add_argument('--comment-on', help='Post ID to add a comment to')
    parser.add_argument('--reply-to', help='Comment ID to reply to (use with --comment-on)')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    # Also accept positional text for backwards compatibility
    parser.add_argument('text', nargs='?', help='Post text (legacy mode: used as content)')
    
    args = parser.parse_args()
    
    # Handle legacy single-arg mode
    content = args.content or args.text
    title = args.title
    
    # Validate
    if args.comment_on:
        # Comment mode - only need content
        if not content:
            print("⚠️  Content required for comments", file=sys.stderr)
            sys.exit(1)
    else:
        # Post mode - need title
        if not title:
            print("⚠️  Title required for new posts (use --title)", file=sys.stderr)
            sys.exit(1)
    
    if content and len(content) > 10000:
        print("⚠️  Content too long (max 10000 characters)", file=sys.stderr)
        sys.exit(1)
    
    result = post_to_moltbook(
        title=title,
        content=content,
        submolt=args.submolt,
        comment_on=args.comment_on,
        reply_to=args.reply_to
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.comment_on:
            print(f"\n✓ Comment posted!")
        else:
            post_data = result.get('post', result)
            post_id = post_data.get('id', 'unknown')
            print(f"\n✓ Posted successfully!")
            print(f"   ID: {post_id}")
            print(f"   URL: https://www.moltbook.com/r/{args.submolt}/{post_id}")

if __name__ == '__main__':
    main()
