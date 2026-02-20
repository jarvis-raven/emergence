# Nautilus Troubleshooting Guide

**Version:** 0.4.0  
**Last Updated:** 2026-02-14

---

## Common Issues

### Search Returns No Results

**Symptoms:**
- `emergence nautilus search "query"` returns empty results
- OpenClaw memory search works fine

**Possible Causes:**

1. **Gravity database doesn't exist**
   
   **Check:**
   ```bash
   emergence nautilus status
   ```
   
   **Fix:**
   ```bash
   emergence nautilus maintain --register-recent --verbose
   ```

2. **Context filtering too aggressive**
   
   **Check:**
   ```bash
   emergence nautilus doors classify "your query"
   ```
   
   **Fix:** Use trapdoor mode to bypass filtering:
   ```bash
   emergence nautilus search "query" --trapdoor
   ```

3. **Chamber filter excludes results**
   
   **Fix:** Check all chambers or specify multiple:
   ```bash
   emergence nautilus search "query" --chamber atrium,corridor,vault
   ```

4. **Files not registered**
   
   **Fix:** Register recent files:
   ```bash
   emergence nautilus maintain --register-recent
   ```

---

### Door Tagging Returns Empty (Known Bug)

**Symptoms:**
- `emergence nautilus doors auto-tag` shows `"files_tagged": 0`
- Manual tagging works but auto-tag doesn't detect patterns

**Root Cause:**
The `classify_text()` function requires exact pattern matches. Very short queries or files with minimal content may not trigger any patterns.

**Workaround:**

1. **Manual tagging for important files:**
   ```bash
   emergence nautilus doors tag memory/2026-02-14.md project:ourblock
   ```

2. **Lower pattern matching threshold:**
   
   Edit `projects/emergence/core/nautilus/doors.py`:
   ```python
   # Change line ~60
   return [tag for tag, score in sorted_tags if score >= 1]
   # To:
   return [tag for tag, score in sorted_tags if score >= 0.5]
   ```

3. **Add custom patterns:**
   
   Edit `CONTEXT_PATTERNS` dict in `doors.py`:
   ```python
   CONTEXT_PATTERNS = {
       # Your custom patterns
       "project:myproject": [
           r"myproject", r"my\.project", r"project\.keyword"
       ],
       # ... existing patterns
   }
   ```

**Status:** Will be improved in future release with fuzzy matching.

---

### Migration Issues

**Symptoms:**
- `emergence nautilus status` shows `"db_exists": false`
- Command fails with "no such table: gravity"

**Cause:** Database not found at expected location.

**Diagnosis:**

1. **Check database paths:**
   ```bash
   python3 -c "
   from core.nautilus.config import get_gravity_db_path, get_state_dir
   print(f'State dir: {get_state_dir()}')
   print(f'DB path: {get_gravity_db_path()}')
   "
   ```

2. **Look for legacy database:**
   ```bash
   find ~ -name "gravity.db" 2>/dev/null
   ```

**Fix:**

1. **Manual migration:**
   ```bash
   # Find legacy DB
   LEGACY_DB=$(find /path/to/workspace/tools/nautilus -name "gravity.db")
   
   # Create state directory
   mkdir -p ~/.openclaw/state/nautilus
   
   # Copy database
   cp "$LEGACY_DB" ~/.openclaw/state/nautilus/gravity.db
   ```

2. **Trigger auto-migration:**
   ```python
   from core.nautilus.config import migrate_legacy_db
   
   if migrate_legacy_db():
       print("Migration successful")
   else:
       print("No legacy database found")
   ```

3. **Start fresh:**
   ```bash
   # This will create a new database
   emergence nautilus maintain --register-recent --verbose
   ```

---

### Database Corruption Recovery

**Symptoms:**
- "database disk image is malformed"
- SQLite errors during search/maintain
- `emergence nautilus status` crashes

**Diagnosis:**

```bash
sqlite3 ~/.openclaw/state/nautilus/gravity.db "PRAGMA integrity_check;"
```

**Fix Options:**

#### Option 1: Backup and Rebuild

```bash
# Backup current database
cp ~/.openclaw/state/nautilus/gravity.db ~/.openclaw/state/nautilus/gravity.db.backup

# Dump salvageable data
sqlite3 ~/.openclaw/state/nautilus/gravity.db ".dump" > gravity_dump.sql

# Remove corrupted database
rm ~/.openclaw/state/nautilus/gravity.db

# Rebuild from dump
sqlite3 ~/.openclaw/state/nautilus/gravity.db < gravity_dump.sql

# Run maintenance to fix any remaining issues
emergence nautilus maintain --register-recent --verbose
```

#### Option 2: Start Fresh (Nuclear Option)

```bash
# Backup old database
mv ~/.openclaw/state/nautilus/gravity.db ~/.openclaw/state/nautilus/gravity.db.corrupted

# Create new database and reindex everything
emergence nautilus maintain --register-recent --verbose
```

**Note:** Starting fresh loses access counts and gravity scores but is the cleanest recovery.

#### Option 3: SQLite Recovery

```bash
# Try to recover
sqlite3 ~/.openclaw/state/nautilus/gravity.db ".recover" > gravity_recovered.sql

# Create new database from recovered data
rm ~/.openclaw/state/nautilus/gravity.db
sqlite3 ~/.openclaw/state/nautilus/gravity.db < gravity_recovered.sql
```

---

### Performance Issues

**Symptoms:**
- Search takes >5 seconds
- Maintenance runs for hours
- High CPU usage during searches

**Diagnosis:**

1. **Check database size:**
   ```bash
   ls -lh ~/.openclaw/state/nautilus/gravity.db
   du -sh ~/.openclaw/state/nautilus/
   ```

2. **Check chunk count:**
   ```bash
   emergence nautilus status | grep total_chunks
   ```

3. **Check missing indexes:**
   ```bash
   sqlite3 ~/.openclaw/state/nautilus/gravity.db ".indexes"
   ```

**Fixes:**

#### Large Database

If database is >100MB:

```bash
# Vacuum to reclaim space
sqlite3 ~/.openclaw/state/nautilus/gravity.db "VACUUM;"

# Reindex
sqlite3 ~/.openclaw/state/nautilus/gravity.db "REINDEX;"
```

#### Missing Indexes

```bash
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
CREATE INDEX IF NOT EXISTS idx_gravity_path ON gravity(path);
CREATE INDEX IF NOT EXISTS idx_gravity_chamber ON gravity(chamber);
CREATE INDEX IF NOT EXISTS idx_access_log_path ON access_log(path);
CREATE INDEX IF NOT EXISTS idx_mirrors_event ON mirrors(event_key);
CREATE INDEX IF NOT EXISTS idx_mirrors_path ON mirrors(path);
EOF
```

#### Too Many Chunks

Reduce chunk count by cleaning up old/superseded entries:

```python
from core.nautilus.gravity import get_db

db = get_db()

# Remove superseded chunks older than 30 days
db.execute("""
    DELETE FROM gravity 
    WHERE superseded_by IS NOT NULL 
    AND date(created_at) < date('now', '-30 days')
""")

db.commit()
db.close()
```

#### Slow Summarization

If corridor promotion is slow:

1. **Use faster Ollama model:**
   
   Edit `chambers.py`:
   ```python
   SUMMARY_MODEL = "llama3.2:1b"  # Faster, lower quality
   ```

2. **Skip summarization:**
   
   Run classify without promotion:
   ```bash
   emergence nautilus chambers classify
   # Skip: emergence nautilus chambers promote
   ```

---

### Context Tags Not Working

**Symptoms:**
- Context filtering doesn't improve results
- All queries return same results regardless of context

**Diagnosis:**

```bash
# Check tag coverage
emergence nautilus status | grep tagged

# Check specific file tags
sqlite3 ~/.openclaw/state/nautilus/gravity.db \
  "SELECT path, context_tags FROM gravity WHERE context_tags != '[]' LIMIT 10;"
```

**Fix:**

1. **Run auto-tag:**
   ```bash
   emergence nautilus doors auto-tag
   ```

2. **Verify patterns work:**
   ```bash
   emergence nautilus doors classify "voice listener debug"
   ```
   
   Should return tags like `project:voice`, `system:infrastructure`.

3. **Add custom patterns** (see "Door Tagging Returns Empty" above)

---

### Maintenance Fails

**Symptoms:**
- `emergence nautilus maintain` exits with error
- Cron job shows failures in logs

**Common Errors:**

#### "No such file or directory: memory/"

**Cause:** Memory directory doesn't exist or workspace path wrong.

**Fix:**

```bash
# Check workspace detection
python3 -c "
from core.nautilus.config import get_workspace, get_memory_dir
print(f'Workspace: {get_workspace()}')
print(f'Memory dir: {get_memory_dir()}')
"

# Create memory directory if missing
mkdir -p memory
```

#### "Timeout expired" during summarization

**Cause:** Ollama not running or model too slow.

**Fix:**

```bash
# Check Ollama status
curl -s http://localhost:11434/api/tags | jq

# Start Ollama if not running
ollama serve

# Increase timeout in chambers.py (line ~90):
# subprocess.run(..., timeout=300)  # 5 minutes instead of 120s
```

#### "Permission denied" on database

**Cause:** Database file permissions issue.

**Fix:**

```bash
# Fix permissions
chmod 644 ~/.openclaw/state/nautilus/gravity.db
chmod 755 ~/.openclaw/state/nautilus/
```

---

### Chambers Not Promoting

**Symptoms:**
- Atrium has files >48 hours old
- Corridor directory empty
- `chambers promote` shows 0 promoted

**Diagnosis:**

```bash
# Check what would be promoted
emergence nautilus chambers promote --dry-run

# Check file ages
python3 -c "
from core.nautilus.chambers import file_age_days
import sys
age = file_age_days('memory/2026-02-14.md')
print(f'Age: {age:.1f} days')
"
```

**Fix:**

1. **Verify date parsing:**
   
   Files must be named `YYYY-MM-DD.md` or have mtime set correctly.

2. **Check corridors directory exists:**
   ```bash
   mkdir -p memory/corridors
   ```

3. **Force promotion:**
   ```bash
   # Temporarily lower age threshold in chambers.py
   # ATRIUM_MAX_AGE_HOURS = 1  # Test with 1 hour
   
   # Run promote
   emergence nautilus chambers promote
   
   # Change back to 48 hours
   ```

---

### Mirrors Not Linking

**Symptoms:**
- `mirrors stats` shows 0 events
- `mirrors auto-link` returns `"linked": 0`

**Diagnosis:**

```bash
# Check corridor files exist
ls -l memory/corridors/

# Check naming convention
# Should be: corridor-YYYY-MM-DD.md
```

**Fix:**

1. **Ensure corridor files follow naming:**
   ```bash
   # Good: corridor-2026-02-14.md
   # Bad:  summary-2026-02-14.md
   ```

2. **Run auto-link:**
   ```bash
   emergence nautilus mirrors auto-link
   ```

3. **Manual linking:**
   ```bash
   python3 -m core.nautilus.mirrors link \
     "daily-2026-02-14" \
     "memory/2026-02-14.md" \
     "memory/corridors/corridor-2026-02-14.md"
   ```

---

### Search Scores Don't Make Sense

**Symptoms:**
- Low-relevance results rank higher than expected
- Important memories buried in results

**Diagnosis:**

```bash
# Check gravity scores
emergence nautilus gravity memory/important-file.md

# Compare with another file
emergence nautilus gravity memory/low-priority-file.md
```

**Common Issues:**

#### Old Files Dominating

**Cause:** High access count from when they were current.

**Fix:** Apply decay:

```bash
emergence nautilus maintain  # Runs decay automatically

# Or manually:
python3 -m core.nautilus.gravity decay
```

#### New Important Info Buried

**Cause:** No access history yet.

**Fix:** Boost manually:

```bash
python3 -m core.nautilus.gravity boost memory/important-file.md --amount 5.0
```

#### Superseded Info Still Appears

**Fix:** Mark as superseded:

```bash
python3 -m core.nautilus.gravity supersede \
  memory/old-wrong-info.md \
  memory/corrected-info.md
```

---

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Enable verbose output for all commands
export NAUTILUS_DEBUG=1

# Run command
emergence nautilus search "query" --verbose

# Or in Python:
import os
os.environ['NAUTILUS_DEBUG'] = '1'

from core.nautilus import search
results = search("query", verbose=True)
```

Add debug logging to your code:

```python
import sys
from core.nautilus import search

# Enable verbose stderr output
results = search("query", n=10, verbose=True)

# Pipeline steps will print to stderr:
# 🚪 Context: ['project:voice']
# 🔍 Base search: 15 results
# ⚖️ Gravity applied: 15 results re-ranked
# 🚪 Context filtered: 8 results
```

---

## Error Messages Reference

### "Database is locked"

**Cause:** Another process has the database open.

**Fix:**

```bash
# Find process using database
lsof ~/.openclaw/state/nautilus/gravity.db

# Kill if necessary
kill <PID>

# Or wait for other process to finish
```

**Prevention:** Use WAL mode (already enabled by default):

```bash
sqlite3 ~/.openclaw/state/nautilus/gravity.db "PRAGMA journal_mode=WAL;"
```

---

### "No module named 'core.nautilus'"

**Cause:** Python path doesn't include Emergence package.

**Fix:**

```bash
# Option 1: Run from workspace
cd /path/to/workspace
python3 -m core.nautilus status

# Option 2: Set PYTHONPATH
export PYTHONPATH="/path/to/workspace/projects/emergence:$PYTHONPATH"

# Option 3: Install Emergence package
cd projects/emergence
pip install -e .
```

---

### "Column 'context_tags' not found"

**Cause:** Legacy database missing new columns.

**Fix:**

```bash
# Run migration
python3 -c "
from core.nautilus.gravity import get_db
db = get_db()  # Auto-adds missing columns
db.close()
"

# Verify
sqlite3 ~/.openclaw/state/nautilus/gravity.db ".schema gravity"
```

---

### "Ollama not responding"

**Cause:** Ollama service not running or wrong URL.

**Fix:**

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve &

# Or change URL in chambers.py:
# OLLAMA_URL = "http://custom-host:11434/api/generate"
```

---

## Health Check Script

Create `scripts/nautilus-health-check.sh`:

```bash
#!/bin/bash
# Nautilus Health Check

echo "=== Nautilus Health Check ==="

# 1. Check database exists
DB_PATH="$HOME/.openclaw/state/nautilus/gravity.db"
if [ -f "$DB_PATH" ]; then
    echo "✓ Database exists: $DB_PATH"
    echo "  Size: $(du -h "$DB_PATH" | cut -f1)"
else
    echo "✗ Database not found: $DB_PATH"
    exit 1
fi

# 2. Check integrity
echo ""
echo "Checking database integrity..."
if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✓ Database integrity OK"
else
    echo "✗ Database corrupted"
    exit 1
fi

# 3. Check indexes
echo ""
echo "Checking indexes..."
INDEX_COUNT=$(sqlite3 "$DB_PATH" ".indexes" | wc -l)
echo "  Found $INDEX_COUNT indexes"

# 4. Check row counts
echo ""
echo "Row counts:"
sqlite3 "$DB_PATH" <<EOF
SELECT '  gravity: ' || COUNT(*) FROM gravity;
SELECT '  access_log: ' || COUNT(*) FROM access_log;
SELECT '  mirrors: ' || COUNT(*) FROM mirrors;
EOF

# 5. Check Ollama
echo ""
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✓ Ollama is running"
else
    echo "⚠ Ollama not responding (needed for summarization)"
fi

# 6. Check workspace
echo ""
echo "Workspace detection:"
python3 -c "
from core.nautilus.config import get_workspace, get_memory_dir
print(f'  Workspace: {get_workspace()}')
print(f'  Memory dir: {get_memory_dir()}')
"

echo ""
echo "=== Health Check Complete ==="
```

Run it:

```bash
chmod +x scripts/nautilus-health-check.sh
./scripts/nautilus-health-check.sh
```

---

## Advanced Debugging

### SQL Queries for Investigation

```bash
# Most accessed memories
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
SELECT path, access_count, effective_mass 
FROM (
  SELECT *, 
    (access_count * 0.3 + reference_count * 0.5 + explicit_importance) AS effective_mass
  FROM gravity
)
ORDER BY access_count DESC LIMIT 10;
EOF

# Recent accesses
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
SELECT path, query, score, accessed_at 
FROM access_log 
ORDER BY accessed_at DESC LIMIT 10;
EOF

# Chamber distribution
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
SELECT chamber, COUNT(*) as count 
FROM gravity 
GROUP BY chamber;
EOF

# Tag coverage
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
SELECT 
  SUM(CASE WHEN context_tags != '[]' THEN 1 ELSE 0 END) as tagged,
  COUNT(*) as total,
  ROUND(100.0 * SUM(CASE WHEN context_tags != '[]' THEN 1 ELSE 0 END) / COUNT(*), 1) as coverage_pct
FROM gravity;
EOF
```

### Python Debugging

```python
import sqlite3
from core.nautilus.config import get_gravity_db_path
from core.nautilus.gravity import compute_effective_mass, gravity_score_modifier

# Open database
db_path = get_gravity_db_path()
db = sqlite3.connect(str(db_path))
db.row_factory = sqlite3.Row

# Investigate specific file
path = "memory/2026-02-14.md"
row = db.execute("SELECT * FROM gravity WHERE path = ?", (path,)).fetchone()

if row:
    print(f"Path: {row['path']}")
    print(f"Chamber: {row['chamber']}")
    print(f"Access count: {row['access_count']}")
    print(f"Context tags: {row['context_tags']}")
    
    mass = compute_effective_mass(row)
    modifier = gravity_score_modifier(mass)
    
    print(f"Effective mass: {mass:.3f}")
    print(f"Score modifier: {modifier:.3f}x")
else:
    print("File not found in gravity database")

db.close()
```

---

## Getting Help

If you can't resolve the issue:

1. **Collect diagnostic info:**
   ```bash
   # System status
   emergence nautilus status > nautilus-status.json
   
   # Health check
   ./scripts/nautilus-health-check.sh > nautilus-health.txt
   
   # Recent logs
   tail -100 logs/nautilus-maintain.log > nautilus-logs.txt
   ```

2. **Check existing issues:**
   - GitHub Issues (if Emergence is open source)
   - Documentation updates

3. **File a bug report** with:
   - Error message (full traceback)
   - Diagnostic info from above
   - Steps to reproduce
   - Expected vs actual behavior

---

## Known Limitations

### v0.4.0 Known Issues

1. **Door tagging empty results** — Pattern matching requires exact keyword matches
2. **Summarization quality varies** — Depends on Ollama model quality
3. **No conflict resolution** — If two corridor summaries exist for same date, last write wins
4. **Context tags are not hierarchical** — `project:ourblock` and `project:ourblock:auth` are separate
5. **No automatic tag cleanup** — Old tags persist even if content changes

### Planned Improvements

- Fuzzy pattern matching for doors
- Hierarchical tag support
- Automatic tag consolidation
- Better summarization prompts
- Conflict detection and resolution
- Performance optimization for large databases (>100k chunks)

---

## Related Documentation

- [User Guide](USER_GUIDE.md) — Getting started and concepts
- [API Reference](API_REFERENCE.md) — Python API documentation
- [Examples](EXAMPLES.md) — Code examples and workflows
