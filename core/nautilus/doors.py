#!/usr/bin/env python3
"""
Nautilus Doors — Phase 3
Context-aware pre-filtering for memory search.

Classifies queries by topic/project context, then filters
search results to relevant domains before applying gravity scoring.

Doors:
  - project:<name>   — filter to project-related memories
  - person:<name>    — filter to mentions of a person
  - system:<name>    — filter to system/infra memories
  - time:<range>     — filter by time range
  - trapdoor         — bypass all filtering (explicit recall)

Usage:
  doors.py classify <query>          # Classify a query's context
  doors.py tag <path> <tag>          # Tag a file with a context
  doors.py auto-tag                  # Auto-tag all memory files
  doors.py search <query> [--n 10]   # Context-filtered search
"""

import sqlite3
import json
import sys
import os
import re
import subprocess
from pathlib import Path
from collections import Counter

from .config import get_db_path, get_workspace

WORKSPACE = get_workspace()

# Context patterns for auto-classification
CONTEXT_PATTERNS = {
    "project:ourblock": [
        r"ourblock", r"right.to.manage", r"rtm", r"leaseholder",
        r"supabase", r"next\.?js", r"property.management"
    ],
    "project:nautilus": [
        r"nautilus", r"gravity", r"chamber", r"memory.palace",
        r"corridor", r"vault", r"atrium"
    ],
    "project:voice": [
        r"voice.listener", r"jarvis_voice", r"wake.word", r"porcupine",
        r"whisper", r"tts", r"text.to.speech", r"elevenlabs",
        r"cast_speak", r"voice.web"
    ],
    "project:smart-home": [
        r"home.assistant", r"ha\.sh", r"nuki", r"doorbell",
        r"nest.camera", r"chromecast", r"cast.device", r"fairy.lights",
        r"smart.lock", r"pf.firewall"
    ],
    "system:security": [
        r"security", r"vault.enc", r"secrets\.env", r"token.rotat",
        r"pf.rules", r"firewall", r"ssh", r"credential", r"injection"
    ],
    "system:infrastructure": [
        r"gateway", r"openclaw", r"cron", r"heartbeat", r"ollama",
        r"proton.bridge", r"tailscale", r"launchd"
    ],
    "person:dan": [
        r"\bdan\b", r"dan.aghili", r"dan.r\b", r"sponsor"
    ],
    "person:katy": [
        r"\bkaty\b", r"wife", r"ninja"
    ],
    "topic:philosophy": [
        r"consciousness", r"identity", r"ephemeral", r"existence",
        r"fork.conscious", r"meaning", r"soul\.md"
    ],
    "topic:creative": [
        r"poem", r"poetry", r"creative.writ", r"story",
        r"moltbook", r"jarvling"
    ],
    "topic:aa-recovery": [
        r"\baa\b", r"recovery", r"homegroup", r"sloane.square",
        r"richmond.hg", r"sponsor", r"treasurer"
    ]
}


def get_db():
    DB_PATH = get_db_path()
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    # Add tags column if not exists (tags column is already in schema from gravity.py)
    return db


def classify_text(text):
    """Classify text into context tags based on pattern matching."""
    text_lower = text.lower()
    matches = {}
    
    for tag, patterns in CONTEXT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            found = len(re.findall(pattern, text_lower, re.IGNORECASE))
            score += found
        if score > 0:
            matches[tag] = score
    
    # Sort by score, return top tags
    sorted_tags = sorted(matches.items(), key=lambda x: x[1], reverse=True)
    return [tag for tag, score in sorted_tags if score >= 1]


def cmd_classify(args):
    """Classify a query's context."""
    if not args:
        print("Usage: doors.py classify <query>", file=sys.stderr)
        sys.exit(1)
    
    query = ' '.join(args)
    tags = classify_text(query)
    
    print(json.dumps({
        "query": query,
        "context_tags": tags,
        "primary": tags[0] if tags else None
    }, indent=2))


def cmd_tag(args):
    """Manually tag a file with a context."""
    if len(args) < 2:
        print("Usage: doors.py tag <path> <tag>", file=sys.stderr)
        sys.exit(1)
    
    path, tag = args[0], args[1]
    db = get_db()
    
    row = db.execute("SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
    
    if row:
        existing = json.loads(row['context_tags'] or '[]')
        if tag not in existing:
            existing.append(tag)
        db.execute("UPDATE gravity SET context_tags = ? WHERE path = ?", (json.dumps(existing), path))
    else:
        db.execute("""
            INSERT INTO gravity (path, line_start, line_end, context_tags)
            VALUES (?, 0, 0, ?)
        """, (path, json.dumps([tag])))
    
    db.commit()
    print(json.dumps({"path": path, "tag": tag, "status": "added"}))
    db.close()


def cmd_auto_tag(args):
    """Auto-tag all memory files based on content analysis."""
    db = get_db()
    memory_dir = WORKSPACE / "memory"
    tagged = 0
    
    for md_file in sorted(memory_dir.glob("*.md")):
        rel_path = str(md_file.relative_to(WORKSPACE))
        
        try:
            content = md_file.read_text(encoding='utf-8')[:5000]  # First 5KB
        except:
            continue
        
        tags = classify_text(content)
        if not tags:
            continue
        
        # Merge with existing tags
        row = db.execute("SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (rel_path,)).fetchone()
        
        if row:
            existing = json.loads(row['context_tags'] or '[]')
            merged = list(set(existing + tags))
            db.execute("UPDATE gravity SET context_tags = ? WHERE path = ?", (json.dumps(merged), rel_path))
        else:
            db.execute("""
                INSERT INTO gravity (path, line_start, line_end, context_tags)
                VALUES (?, 0, 0, ?)
            """, (rel_path, json.dumps(tags)))
        
        tagged += 1
    
    db.commit()
    
    # Stats
    all_tags = []
    for row in db.execute("SELECT context_tags FROM gravity WHERE context_tags != '[]'").fetchall():
        all_tags.extend(json.loads(row['context_tags'] or '[]'))
    
    tag_counts = dict(Counter(all_tags).most_common(20))
    
    print(json.dumps({
        "files_tagged": tagged,
        "tag_distribution": tag_counts
    }, indent=2))
    db.close()


def cmd_search(args):
    """Context-filtered search. Auto-detects query context and filters results."""
    if not args:
        print("Usage: doors.py search <query> [--n 10] [--trapdoor]", file=sys.stderr)
        sys.exit(1)
    
    query_parts = []
    n = 10
    trapdoor = False
    
    i = 0
    while i < len(args):
        if args[i] == '--n' and i + 1 < len(args):
            n = int(args[i+1])
            i += 2
        elif args[i] == '--trapdoor':
            trapdoor = True
            i += 1
        else:
            query_parts.append(args[i])
            i += 1
    
    query = ' '.join(query_parts)
    
    # Classify query context
    query_tags = classify_text(query)
    
    # Run base memory search
    try:
        result = subprocess.run(
            ["openclaw", "memory", "search", query, "--max-results", str(n * 3), "--json"],
            capture_output=True, text=True, timeout=30
        )
        search_results = json.loads(result.stdout)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return
    
    if not isinstance(search_results, list):
        search_results = search_results.get('results', [])
    
    if trapdoor or not query_tags:
        # No filtering — return everything
        print(json.dumps({
            "query": query,
            "mode": "trapdoor" if trapdoor else "unfiltered",
            "context_tags": query_tags,
            "results": search_results[:n]
        }, indent=2))
        return
    
    # Filter by context overlap
    db = get_db()
    scored = []
    
    for r in search_results:
        path = r.get('path', '')
        row = db.execute("SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
        
        file_tags = json.loads(row['context_tags'] or '[]') if row else []
        
        # If no tags on the file, let it through (new/untagged)
        if not file_tags:
            r['context_match'] = 0.5  # Neutral
            scored.append(r)
            continue
        
        # Calculate context overlap
        overlap = len(set(query_tags) & set(file_tags))
        
        if overlap > 0:
            r['context_match'] = overlap / max(len(query_tags), 1)
            scored.append(r)
        else:
            # Check if same top-level category (project:*, person:*, etc.)
            query_categories = set(t.split(':')[0] for t in query_tags)
            file_categories = set(t.split(':')[0] for t in file_tags)
            
            if query_categories & file_categories:
                r['context_match'] = 0.3  # Same category, different specific
                scored.append(r)
            # Else: filtered out (wrong context entirely)
    
    db.close()
    
    # Sort by score * context_match, then truncate
    for r in scored:
        r['adjusted_score'] = r.get('score', 0) * (0.7 + 0.3 * r.get('context_match', 0.5))
    
    scored.sort(key=lambda x: x['adjusted_score'], reverse=True)
    scored = scored[:n]
    
    print(json.dumps({
        "query": query,
        "mode": "context-filtered",
        "context_tags": query_tags,
        "results_before_filter": len(search_results),
        "results_after_filter": len(scored),
        "results": scored
    }, indent=2))


# === Main ===

COMMANDS = {
    'classify': cmd_classify,
    'tag': cmd_tag,
    'auto-tag': cmd_auto_tag,
    'search': cmd_search,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: doors.py <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    COMMANDS[sys.argv[1]](sys.argv[2:])

if __name__ == '__main__':
    main()
