# Nautilus Troubleshooting Guide

> 🐚 **Common errors, solutions, and debugging strategies**

**Quick Links:** [User Guide](nautilus-user-guide.md) • [API Reference](nautilus-api.md) • [Main README](../README.md)

---

## Table of Contents

1. [Common Errors & Solutions](#common-errors--solutions)
2. [Performance Issues](#performance-issues)
3. [Database Problems](#database-problems)
4. [Summarization Failures](#summarization-failures)
5. [Search Quality Issues](#search-quality-issues)
6. [Migration Problems](#migration-problems)
7. [OS-Specific Issues](#os-specific-issues)
8. [Debugging Modes](#debugging-modes)

---

## Common Errors & Solutions

### 1. "Database is locked" Error

**Symptom:**

```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes trying to write to `gravity.db` simultaneously.

**Solutions:**

**A. Find and stop competing processes:**

```bash
# Check for processes using the database
lsof | grep gravity.db

# Or on Linux
fuser ~/.openclaw/state/nautilus/gravity.db

# Kill the process (if safe)
kill -9 <PID>
```

**B. Enable WAL mode** (should be default, but verify):

```python
import sqlite3
from core.nautilus.config import get_db_path

db = sqlite3.connect(str(get_db_path()))
db.execute("PRAGMA journal_mode=WAL")
db.commit()
db.close()
```

**C. Increase timeout in code:**

```python
db = sqlite3.connect(str(get_db_path()), timeout=30.0)
```

**Prevention:**

- Don't run multiple maintenance tasks simultaneously
- Use the unified `emergence nautilus maintain` command
- Check daemon logs for conflicts

---

### 2. "No results found" Debugging

**Symptom:**

```json
{
  "query": "test query",
  "results": []
}
```

**Causes & Solutions:**

**A. Database not initialized:**

```bash
# Check database exists
ls -lh ~/.openclaw/state/nautilus/gravity.db

# Initialize if missing
python3 -m core.nautilus.gravity stats
```

**B. No memory files indexed:**

```bash
# Check total chunks
emergence nautilus status

# If zero, run classification
emergence nautilus maintain --register-recent
```

**C. Context filtering too aggressive:**

```bash
# Try trapdoor mode to bypass filtering
emergence nautilus search "test query" --trapdoor --n 10
```

**D. OpenClaw memory search failing:**

```bash
# Test base search directly
openclaw memory search "test query" --max-results 10 --json

# If this fails, the issue is upstream (not Nautilus)
```

**Debug mode:**

```bash
# Enable verbose output
emergence nautilus search "test query" --verbose

# Check each pipeline stage:
# 1. 🚪 Context classification
# 2. 🔍 Base search results count
# 3. ⚖️ Gravity re-ranking
# 4. 🚪 Context filtering
```

---

### 3. Ollama Connection Failures

**Symptom:**

```
⚠️  Ollama not available (HTTP 000), skipping summarization...
```

**Causes & Solutions:**

**A. Ollama not running:**

```bash
# Check if Ollama is running
curl -s http://localhost:11434 | jq

# Start Ollama
ollama serve &
```

**B. Wrong port/URL:**

```json
// Check emergence.json
{
  "nautilus": {
    "summarization": {
      "ollama_url": "http://localhost:11434/api/generate"
    }
  }
}
```

**C. Model not installed:**

```bash
# Check available models
ollama list

# Install the configured model
ollama pull llama3.2:3b
```

**D. Firewall blocking:**

```bash
# Test connectivity
curl -v http://localhost:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"test","stream":false}'

# If timeout, check firewall rules
```

**E. Disable summarization** (if Ollama not needed):

```json
{
  "nautilus": {
    "summarization": {
      "enabled": false
    }
  }
}
```

---

### 4. Chamber Promotion Finding 0 Candidates

**Symptom:**

```json
{
  "mode": "dry-run",
  "candidates": 0,
  "files": []
}
```

**Causes & Solutions:**

**A. No files old enough:**

```bash
# Check file ages
ls -lt ~/.openclaw/workspace/memory/*.md | head -10

# Default threshold is 48 hours
# If all files are newer, this is expected
```

**B. Already promoted:**

```bash
# Check for existing summaries
ls ~/.openclaw/workspace/memory/corridors/

# If summaries exist, files won't re-promote
```

**C. Wrong memory directory:**

```bash
# Verify memory directory setting
python3 -c "from core.nautilus.config import get_workspace; print(get_workspace() / 'memory')"

# Check if files exist there
ls -la <output_from_above>
```

**D. Files in wrong location:**

```bash
# Promotion looks for files matching pattern 2*.md in memory/
# Verify naming: 2026-02-14.md (correct) vs notes.md (ignored)

# Rename if needed
mv memory/notes.md memory/2026-02-15-notes.md
```

**E. Adjust threshold** (if you want more aggressive promotion):

```json
{
  "nautilus": {
    "chamber_thresholds": {
      "atrium_max_age_hours": 24 // Promote after 24h instead of 48h
    }
  }
}
```

---

### 5. High Memory Usage

**Symptom:**
System sluggish during summarization or search.

**Causes & Solutions:**

**A. Large Ollama model:**

```bash
# Check current model size
ollama list

# Use smaller model
ollama pull llama3.2:1b  # 1.3GB vs 2.0GB for 3b

# Update config
{
  "summarization": {
    "model": "llama3.2:1b"
  }
}
```

**B. Too many results in pipeline:**

```bash
# Search currently fetches n × 3 base results
# Reduce if needed (edit nautilus_cli.py):

# Change this line in cmd_search():
["openclaw", "memory", "search", query, "--max-results", str(n * 3), ...]
# to:
["openclaw", "memory", "search", query, "--max-results", str(n * 2), ...]
```

**C. Database size bloat:**

```bash
# Check database size
ls -lh ~/.openclaw/state/nautilus/gravity.db

# If >100MB, vacuum
python3 -c "
import sqlite3
from core.nautilus.config import get_db_path
db = sqlite3.connect(str(get_db_path()))
db.execute('VACUUM')
db.commit()
db.close()
print('Vacuumed!')
"
```

**D. Limit summarization concurrency:**

Currently, promotion runs sequentially. If you've modified code for parallel promotion, add rate limiting:

```python
import time

for c in candidates:
    summary = llm_summarize(content)
    time.sleep(2)  # 2 second delay between summaries
```

---

### 6. Gravity Scores Not Updating

**Symptom:**
Old files still ranking high despite not being accessed.

**Causes & Solutions:**

**A. Decay not running:**

```bash
# Check last decay timestamp
python3 -m core.nautilus.gravity stats | jq '.recent_accesses[-1].accessed_at'

# Run manual decay
python3 -m core.nautilus.gravity decay
```

**B. Explicit importance too high:**

```bash
# Check top chunks
python3 -m core.nautilus.gravity top --n 10 | jq '.[] | {path, explicit_importance}'

# If explicit_importance > 50, it dominates recency
# Reduce manually:
python3 -c "
import sqlite3
from core.nautilus.config import get_db_path
db = sqlite3.connect(str(get_db_path()))
db.execute('UPDATE gravity SET explicit_importance = explicit_importance * 0.5 WHERE explicit_importance > 50')
db.commit()
db.close()
"
```

**C. Decay rate too low:**

```json
{
  "nautilus": {
    "decay_rate": 0.1 // Increase from default 0.05
  }
}
```

**D. Authority boost masking decay:**

Files written in last 48h get +0.3 boost. If you write frequently to the same files, they'll stay high.

**Solution:** Adjust authority window:

```python
# Edit gravity.py, line ~100:
authority = AUTHORITY_BOOST if days_written < 1.0 else 0.0  # 24h instead of 48h
```

---

### 7. Context Tags Not Applied

**Symptom:**

```json
{
  "tagged_files": 0,
  "total_files": 150
}
```

**Causes & Solutions:**

**A. Auto-tag not run:**

```bash
# Run auto-tagging
python3 -m core.nautilus.doors auto-tag
```

**B. No pattern matches:**

```bash
# Check file content for known patterns
grep -i "nautilus\|ourblock\|dan" memory/*.md | head -5

# If no matches, content doesn't match defined patterns
```

**C. Database field doesn't exist:**

```bash
# Verify schema includes tags column
python3 -c "
import sqlite3
from core.nautilus.config import get_db_path
db = sqlite3.connect(str(get_db_path()))
cursor = db.execute('PRAGMA table_info(gravity)')
cols = [row[1] for row in cursor.fetchall()]
print('tags' in cols)
db.close()
"
# Should print: True
```

**D. Add custom patterns:**

```python
# Edit doors.py to add your patterns
CONTEXT_PATTERNS["project:myproject"] = [
    r"myproject", r"custom.keyword"
]

# Then re-run auto-tag
```

---

### 8. Summarization Produces Low-Quality Output

**Symptom:**
Corridor summaries are too short, miss key details, or hallucinate.

**Solutions:**

**A. Wrong model for task:**

```bash
# 1b model may be too small for good summarization
# Upgrade to 3b:
ollama pull llama3.2:3b

# Update config
{
  "summarization": {
    "model": "llama3.2:3b"
  }
}
```

**B. Temperature too high:**

```json
{
  "summarization": {
    "temperature": 0.2 // Lower = more focused (default: 0.3)
  }
}
```

**C. Max tokens too low:**

```json
{
  "summarization": {
    "max_tokens": 2048 // Increase from default 1024
  }
}
```

**D. Prompt needs tuning:**

Edit `chambers.py`, function `llm_summarize()`, and adjust prompts:

```python
# More specific instructions
prompt = f"""Summarize this daily memory log. Include:
1. Key decisions made (with reasoning)
2. Problems solved (with solutions)
3. Important interactions (names and outcomes)
4. Technical details (versions, configs, bugs)
5. Action items and follow-ups

Keep it 3-5 paragraphs. Be specific, not generic.

{text[:8000]}

Summary:"""
```

**E. Skip summarization for specific files:**

```python
# In cmd_promote(), add filter:
if "draft" in c['path'] or "scratch" in c['path']:
    skipped.append({"path": c['path'], "reason": "draft file"})
    continue
```

---

### 9. Migration Fails from Legacy Location

**Symptom:**

```
Migration failed: [Errno 2] No such file or directory
```

**Cause:** Old database not found in expected location.

**Solutions:**

**A. Find legacy database:**

```bash
# Common locations
find ~/.openclaw/workspace -name "gravity.db" 2>/dev/null
find ~/projects/emergence -name "gravity.db" 2>/dev/null

# If found, note the path
```

**B. Manual migration:**

```bash
# Copy to new location
cp /path/to/old/gravity.db ~/.openclaw/state/nautilus/gravity.db

# Verify
ls -lh ~/.openclaw/state/nautilus/gravity.db
```

**C. Check config override:**

```json
// If you've customized the path:
{
  "nautilus": {
    "gravity_db": "/custom/path/gravity.db"
  }
}

// Make sure the directory exists
```

---

### 10. Search Returns Wrong Context

**Symptom:**
Query for "Dan" returns results tagged `project:nautilus` instead of `person:dan`.

**Causes & Solutions:**

**A. Context classification weak:**

```bash
# Test classification
python3 -m core.nautilus.doors classify "conversation with Dan about nautilus"

# Expected: ['project:nautilus', 'person:dan']
# If missing person:dan, pattern doesn't match
```

**B. Add more specific patterns:**

```python
# Edit doors.py
CONTEXT_PATTERNS["person:dan"] = [
    r"\bdan\b",           # Existing
    r"dan.aghili",        # Existing
    r"discussed.*dan",    # NEW: "discussed with Dan"
    r"dan.*said",         # NEW: "Dan said..."
    r"meeting.*dan"       # NEW: "meeting with Dan"
]
```

**C. Manual tagging:**

```bash
# For specific important files
python3 -m core.nautilus.doors tag "memory/2026-02-14.md" "person:dan"
```

**D. Use trapdoor for ambiguous queries:**

```bash
# When context is mixed or unclear
emergence nautilus search "Dan nautilus" --trapdoor --n 10
```

---

### 11. Chambers Classify Everything as "unknown"

**Symptom:**

```json
{
  "chambers": {
    "unknown": 752,
    "atrium": 0,
    "corridor": 0
  }
}
```

**Causes & Solutions:**

**A. Files don't match date pattern:**

```bash
# Classifier looks for YYYY-MM-DD in filename
# Check naming:
ls memory/*.md | head -5

# Correct: memory/2026-02-14.md
# Wrong: memory/notes.md
```

**B. Files lack mtime metadata:**

```bash
# Fallback uses file modification time
# Check if stat works:
stat memory/2026-02-14.md

# If mtime is far future or 1970, filesystem issue
```

**C. Run explicit classification:**

```bash
python3 -m core.nautilus.chambers classify
```

**D. Verify workspace path:**

```python
from core.nautilus.config import get_workspace
print(get_workspace())

# Should point to your actual workspace
# If wrong, set OPENCLAW_WORKSPACE env var
```

---

### 12. Promotion Creates Empty Summaries

**Symptom:**
Corridor files exist but contain no content or just headers.

**Causes & Solutions:**

**A. Ollama timeout:**

```bash
# Check logs during promotion
python3 -m core.nautilus.chambers promote 2>&1 | tee promotion.log

# Look for "timed out" messages
```

**B. Increase timeout:**

```python
# Edit chambers.py, llm_summarize() function:
result = subprocess.run(..., timeout=180)  # 3 minutes instead of 120 seconds
```

**C. Source file too small:**

```python
# Promotion skips files <100 chars
# Check source size:
wc -c memory/2026-02-14.md

# If smaller, this is expected behavior
```

**D. Model returned empty response:**

```bash
# Test model manually
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Summarize this: Test content",
  "stream": false
}' | jq '.response'

# If empty, model issue — try different model
```

---

## Performance Issues

### Slow Search Queries

**Symptoms:**

- Search takes >10 seconds
- High CPU usage during search

**Solutions:**

**A. Reduce pipeline complexity:**

```bash
# Skip context filtering for speed
emergence nautilus search "query" --trapdoor
```

**B. Limit base results:**

```python
# Edit nautilus_cli.py, cmd_search():
# Change n × 3 to n × 2 or even n × 1.5
```

**C. Index optimization:**

```sql
-- Add custom indexes if needed
CREATE INDEX IF NOT EXISTS idx_gravity_last_accessed
  ON gravity(last_accessed_at);

CREATE INDEX IF NOT EXISTS idx_gravity_last_written
  ON gravity(last_written_at);
```

**D. Pre-compute gravity scores:**

```python
# Add computed column
ALTER TABLE gravity ADD COLUMN effective_mass_cached REAL;

# Update nightly
UPDATE gravity SET effective_mass_cached = <formula>;
```

---

### Slow Promotion

**Symptoms:**

- Promotion takes >5 minutes per file
- Ollama uses 100% CPU

**Solutions:**

**A. Use faster model:**

```json
{
  "summarization": {
    "model": "llama3.2:1b" // 2-3x faster than 3b
  }
}
```

**B. Reduce max_tokens:**

```json
{
  "summarization": {
    "max_tokens": 512 // Faster generation
  }
}
```

**C. Batch promotion:**

```bash
# Don't promote all at once
# Do 5-10 files per run
python3 -c "
from core.nautilus.chambers import cmd_promote
import sys

# Promote max 10 files
# (Would need to modify cmd_promote to accept --limit flag)
"
```

---

## Database Problems

### Database Corruption

**Symptoms:**

```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions:**

**A. Try recovery:**

```bash
cd ~/.openclaw/state/nautilus

# Backup first
cp gravity.db gravity.db.backup

# Attempt repair
sqlite3 gravity.db "PRAGMA integrity_check;"

# If errors, dump and restore
sqlite3 gravity.db .dump > dump.sql
mv gravity.db gravity.db.corrupt
sqlite3 gravity.db < dump.sql
```

**B. Restore from backup:**

```bash
# If you have Time Machine or backups
cp /path/to/backup/gravity.db ~/.openclaw/state/nautilus/

# Verify
sqlite3 gravity.db "SELECT COUNT(*) FROM gravity;"
```

**C. Nuclear option (rebuild):**

```bash
# Delete database
rm ~/.openclaw/state/nautilus/gravity.db

# Rebuild from scratch
emergence nautilus maintain --register-recent
```

---

### WAL File Growing Large

**Symptoms:**
`gravity.db-wal` is hundreds of MB.

**Solutions:**

```bash
# Checkpoint WAL
python3 -c "
import sqlite3
from core.nautilus.config import get_db_path
db = sqlite3.connect(str(get_db_path()))
db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
db.commit()
db.close()
"

# Verify
ls -lh ~/.openclaw/state/nautilus/gravity.db*
```

---

## Search Quality Issues

### Results Don't Match Intent

**Problem:** Searching for "project ideas" returns meeting notes.

**Solutions:**

**A. Use more specific queries:**

```bash
# Instead of:
emergence nautilus search "ideas"

# Try:
emergence nautilus search "project ideas creative concepts"
```

**B. Boost specific memories:**

```bash
python3 -m core.nautilus.gravity boost "memory/project-ideas.md" --amount 5.0
```

**C. Manual tagging:**

```bash
python3 -m core.nautilus.doors tag "memory/project-ideas.md" "topic:planning"
```

---

### Old Memories Dominating

**Problem:** Recent content buried by old high-access content.

**Solutions:**

**A. Increase authority boost:**

```json
{
  "nautilus": {
    "authority_boost": 0.5 // Default: 0.3
  }
}
```

**B. More aggressive decay:**

```json
{
  "nautilus": {
    "decay_rate": 0.1,
    "recency_half_life_days": 7
  }
}
```

**C. Reset access counts:**

```sql
-- Nuclear option: reset all access counts
UPDATE gravity SET access_count = 0;
```

---

## Migration Problems

### Paths Don't Match After Migration

**Problem:** Old paths reference wrong workspace.

**Solutions:**

```python
# Run path rewriter
from core.nautilus.config import get_db_path
import sqlite3

old_prefix = "/old/workspace/path"
new_prefix = "/new/workspace/path"

db = sqlite3.connect(str(get_db_path()))
cursor = db.execute("SELECT DISTINCT path FROM gravity WHERE path LIKE ?",
                    (f"{old_prefix}%",))
paths = [row[0] for row in cursor.fetchall()]

for old_path in paths:
    new_path = old_path.replace(old_prefix, new_prefix)
    db.execute("UPDATE gravity SET path = ? WHERE path = ?", (new_path, old_path))

db.commit()
db.close()
```

---

## OS-Specific Issues

### macOS: Permission Denied on Database

**Solution:**

```bash
# Check permissions
ls -l ~/.openclaw/state/nautilus/gravity.db

# Fix ownership
chown $(whoami) ~/.openclaw/state/nautilus/gravity.db

# Fix permissions
chmod 644 ~/.openclaw/state/nautilus/gravity.db
```

---

### Ubuntu: curl Not Found

**Solution:**

```bash
sudo apt update
sudo apt install curl
```

---

### Ubuntu: Python Module Import Errors

**Solution:**

```bash
# Make sure you're in the right directory
cd ~/projects/emergence

# Verify PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH

# Or use python -m syntax
python3 -m core.nautilus.gravity stats
```

---

### Windows: Path Separators

**Solution:**

Use `pathlib.Path` instead of string concatenation:

```python
from pathlib import Path
from core.nautilus.config import get_workspace

workspace = get_workspace()
memory_dir = workspace / "memory"  # Works on all OSes
```

---

## Debugging Modes

### Enable Verbose Logging

```bash
# CLI verbose mode
emergence nautilus search "query" --verbose

# Python verbose mode
import logging
logging.basicConfig(level=logging.DEBUG)

from core.nautilus.gravity import cmd_search
cmd_search(["test"])
```

---

### Inspect Database Directly

```bash
# Open database
sqlite3 ~/.openclaw/state/nautilus/gravity.db

# Useful queries:
.schema                                    # Show schema
SELECT COUNT(*) FROM gravity;              # Total chunks
SELECT * FROM gravity LIMIT 5;             # Sample records
SELECT path, access_count FROM gravity ORDER BY access_count DESC LIMIT 10;  # Top accessed
SELECT * FROM access_log ORDER BY id DESC LIMIT 10;  # Recent accesses
```

---

### Capture Pipeline Output

```bash
# Save full pipeline output
emergence nautilus search "test" --verbose 2>&1 | tee debug.log

# Analyze stages
grep "🚪\|🔍\|⚖️" debug.log
```

---

### Test Individual Modules

```bash
# Test gravity
python3 -m core.nautilus.gravity stats
python3 -m core.nautilus.gravity top --n 10

# Test chambers
python3 -m core.nautilus.chambers status
python3 -m core.nautilus.chambers promote --dry-run

# Test doors
python3 -m core.nautilus.doors classify "test query"
python3 -m core.nautilus.doors auto-tag

# Test mirrors
python3 -m core.nautilus.mirrors stats
```

---

## Still Stuck?

### Collect Diagnostic Info

```bash
# System info
uname -a
python3 --version
sqlite3 --version

# Nautilus status
emergence nautilus status > nautilus-status.json

# Database info
ls -lh ~/.openclaw/state/nautilus/
sqlite3 ~/.openclaw/state/nautilus/gravity.db "SELECT COUNT(*) FROM gravity;"

# Config
cat ~/projects/emergence/emergence.json | jq '.nautilus'

# Recent logs
tail -100 /tmp/nautilus-*.log
```

### Report an Issue

Include:

1. Diagnostic info from above
2. Full error message with stack trace
3. Steps to reproduce
4. What you expected vs what happened

**GitHub:** [github.com/jarvis-raven/emergence/issues](https://github.com/jarvis-raven/emergence/issues)

---

_When debugging, remember: The nautilus grew its shell one chamber at a time. You can rebuild yours, too._ 🐚
