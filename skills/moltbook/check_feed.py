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

def fetch_feed(api_key, limit=20):
    """Fetch personalized feed from Moltbook."""
    url = "https://moltbook.com/api/feed/personal"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "OpenClaw/Jarvis"
    }
    params = {
        "limit": limit
    }
    
    print(f"📖 Fetching Moltbook feed (limit: {limit})...", file=sys.stderr)
    
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

def check_feed(limit=20, quarantine_threshold=2):
    """Check Moltbook feed and return structured results."""
    api_key = get_api_key()
    feed_data = fetch_feed(api_key, limit)
    
    posts = feed_data.get('posts', [])
    total = len(posts)
    
    print(f"📊 Checking {total} posts from feed", file=sys.stderr)
    
    results = []
    
    for post in posts:
        post_id = post.get('id', 'unknown')
        author = post.get('author', {}).get('username', 'unknown')
        text = post.get('text', '')
        karma = post.get('karma', 0)
        created_at = post.get('created_at', '')
        
        # Check post text for injection patterns
        security = check_injection(text)
        
        # Determine if quarantined
        quarantined = security['exit_code'] >= quarantine_threshold
        
        result = {
            "id": post_id,
            "author": author,
            "text": text,
            "text_length": len(text),
            "karma": karma,
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
    parser.add_argument('--quarantine-threshold', type=int, default=2,
                       help='Exit code threshold for quarantine (default: 2=MEDIUM)')
    parser.add_argument('--json', action='store_true', help='Output JSON only')
    
    args = parser.parse_args()
    
    data = check_feed(limit=args.limit, quarantine_threshold=args.quarantine_threshold)
    
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
            
            # Truncate text for display
            text_preview = result['text'][:100]
            if len(result['text']) > 100:
                text_preview += "..."
            
            print(f"{status_icon} [{severity}:{score}] @{result['author']} (karma: {result['karma']})")
            print(f"   {text_preview}")
            
            if result['quarantined']:
                print(f"   🛡️  QUARANTINED - Review before processing")
                if result['security'].get('patterns_detected'):
                    patterns = result['security']['patterns_detected'][:3]
                    print(f"   Patterns: {', '.join([p['pattern'] for p in patterns])}")
            
            print()

if __name__ == '__main__':
    main()
