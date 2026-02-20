#!/usr/bin/env python3
"""
Check Moltbook feed with prompt injection security.

Usage:
    python3 check_feed.py [--limit N] [--quarantine-threshold N]

Features:
- Fetches personalized feed from Moltbook API
- Runs all content through check-injection.sh
- Quarantines suspicious posts
- Returns structured data
"""
import subprocess
import sys
import json
import requests
from datetime import datetime

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

def check_injection(text):
    """Run content through security checker."""
    if not text or not text.strip():
        return {"severity": "CLEAN", "score": 0, "exit_code": 0}
    
    try:
        result = subprocess.run(
            ['/Users/jarvis/.openclaw/bin/check-injection.sh', '--json'],
            input=text.encode('utf-8'),
            capture_output=True,
            timeout=5
        )
        return json.loads(result.stdout.decode('utf-8'))
    except Exception as e:
        print(f"⚠️  Security check failed: {e}", file=sys.stderr)
        return {"severity": "UNKNOWN", "score": 0, "exit_code": 0}

def fetch_feed(api_key, limit=20, sort="hot"):
    """Fetch feed from Moltbook v1 API."""
    # IMPORTANT: Must use www.moltbook.com - non-www strips auth headers!
    url = "https://www.moltbook.com/api/v1/posts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "OpenClaw/Jarvis"
    }
    params = {
        "limit": limit,
        "sort": sort
    }
    
    print(f"📖 Fetching Moltbook feed (limit: {limit}, sort: {sort})...", file=sys.stderr)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("⚠️  Authentication failed - check API key", file=sys.stderr)
        elif e.response.status_code == 429:
            print("⚠️  Rate limited - try again later", file=sys.stderr)
        else:
            print(f"⚠️  HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  Failed to fetch feed: {e}", file=sys.stderr)
        sys.exit(1)

def check_feed(limit=20, quarantine_threshold=2, sort="hot"):
    """Check Moltbook feed and return structured results."""
    api_key = get_api_key()
    feed_data = fetch_feed(api_key, limit, sort)
    
    posts = feed_data.get('posts', [])
    total = len(posts)
    
    print(f"📊 Checking {total} posts from feed", file=sys.stderr)
    
    results = []
    
    for post in posts:
        post_id = post.get('id', 'unknown')
        author = post.get('author', {}).get('name', 'unknown')
        # v1 API uses 'content' and 'title' instead of 'text'
        title = post.get('title', '')
        content = post.get('content', '')
        text = f"{title}\n\n{content}" if title and content else (title or content)
        karma = post.get('upvotes', 0) - post.get('downvotes', 0)
        created_at = post.get('created_at', '')
        comment_count = post.get('comment_count', 0)
        submolt = post.get('submolt', {}).get('name', 'general')
        
        # Check post text for injection patterns
        security = check_injection(text)
        
        # Determine if quarantined
        quarantined = security['exit_code'] >= quarantine_threshold
        
        result = {
            "id": post_id,
            "author": author,
            "title": title,
            "content": content,
            "text": text,
            "text_length": len(text),
            "karma": karma,
            "upvotes": post.get('upvotes', 0),
            "downvotes": post.get('downvotes', 0),
            "comment_count": comment_count,
            "submolt": submolt,
            "created_at": created_at,
            "security": security,
            "quarantined": quarantined
        }
        
        results.append(result)
    
    return {
        "total_posts": total,
        "checked": len(results),
        "results": results
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Check Moltbook feed with security scanning')
    parser.add_argument('--limit', type=int, default=20, help='Number of posts to fetch')
    parser.add_argument('--sort', type=str, default='hot', 
                       choices=['hot', 'new', 'top', 'rising'],
                       help='Sort order (default: hot)')
    parser.add_argument('--quarantine-threshold', type=int, default=2,
                       help='Exit code threshold for quarantine (default: 2=MEDIUM)')
    parser.add_argument('--json', action='store_true', help='Output JSON only')
    
    args = parser.parse_args()
    
    data = check_feed(limit=args.limit, quarantine_threshold=args.quarantine_threshold, sort=args.sort)
    
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        # Human-readable output
        print(f"\n📖 Moltbook Feed Check Results")
        print(f"Total posts: {data['total_posts']}")
        print(f"Checked: {data['checked']}")
        print()
        
        clean_count = sum(1 for r in data['results'] if not r['quarantined'])
        quarantine_count = sum(1 for r in data['results'] if r['quarantined'])
        
        print(f"✓ Clean: {clean_count}")
        if quarantine_count > 0:
            print(f"⚠️  Quarantined: {quarantine_count}")
        print()
        
        # Show posts
        for result in data['results']:
            status_icon = "⚠️" if result['quarantined'] else "✓"
            severity = result['security']['severity']
            score = result['security']['score']
            
            # Show title and truncated content
            title = result.get('title', '')
            content = result.get('content', '')
            content_preview = content[:100]
            if len(content) > 100:
                content_preview += "..."
            
            print(f"{status_icon} [{severity}:{score}] @{result['author']} in r/{result.get('submolt', 'general')}")
            print(f"   📰 {title}" if title else "   (no title)")
            print(f"   ⬆️  {result.get('upvotes', 0)} | 💬 {result.get('comment_count', 0)}")
            if content_preview:
                print(f"   {content_preview}")
            
            if result['quarantined']:
                print(f"   🛡️  QUARANTINED - Review before processing")
                if result['security'].get('patterns_detected'):
                    patterns = result['security']['patterns_detected'][:3]
                    print(f"   Patterns: {', '.join([p['pattern'] for p in patterns])}")
            
            print()

if __name__ == '__main__':
    main()
