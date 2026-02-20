# Nautilus API Reference

**Version:** 0.4.0  
**Last Updated:** 2026-02-14

---

## Module Structure

```
core.nautilus/
├── __init__.py          # Main API exports
├── config.py            # Path resolution and configuration
├── search.py            # Full pipeline search
├── gravity.py           # Phase 1: Importance scoring
├── chambers.py          # Phase 2: Temporal layers
├── doors.py             # Phase 3: Context filtering
└── mirrors.py           # Phase 4: Multi-granularity indexing
```

---

## Main API (`core.nautilus`)

### `search(query, n=5, trapdoor=False, verbose=False, chambers_filter=None)`

Run the full Nautilus search pipeline (gravity + context + chambers + mirrors).

**Parameters:**
- `query` (str): Search query string
- `n` (int, default=5): Number of results to return
- `trapdoor` (bool, default=False): Bypass context filtering if True
- `verbose` (bool, default=False): Print pipeline steps to stderr
- `chambers_filter` (str, optional): Comma-separated chambers (e.g., "atrium,corridor")

**Returns:**
```python
{
    "query": str,
    "context": List[str],  # Context tags detected
    "mode": str,  # "trapdoor" | "context-filtered" | "full"
    "results": List[dict],  # Search results with gravity scores
    "mirrors": dict  # Mirror information for top results
}
```

**Example:**
```python
from core.nautilus import search

# Basic search
results = search("project status", n=10)

# Recent memories only
results = search("yesterday's work", chambers_filter="atrium")

# Bypass filtering
results = search("banana jamba", trapdoor=True, verbose=True)
```

**Search Result Format:**
```python
{
    "path": "memory/2026-02-14.md",
    "startLine": 45,
    "endLine": 67,
    "score": 0.847,  # Adjusted by gravity
    "original_score": 0.723,  # Before gravity
    "snippet": "...",
    "chamber": "atrium",
    "context_match": 0.8,
    "gravity": {
        "effective_mass": 5.234,
        "modifier": 1.187,
        "superseded": false
    }
}
```

---

### `get_status()`

Get full Nautilus system status.

**Returns:**
```python
{
    "nautilus": {
        "phase_1_gravity": {
            "total_chunks": int,
            "total_accesses": int,
            "superseded": int,
            "tagged": int,
            "coverage": str  # "tagged/total"
        },
        "phase_2_chambers": {
            "chambers": {
                "atrium": int,
                "corridor": int,
                "vault": int
            },
            "total_tracked": int,
            "summary_files": {
                "corridors": int,
                "vaults": int
            },
            "recent_promotions": List[dict]
        },
        "phase_3_doors": {
            "patterns_defined": int
        },
        "phase_4_mirrors": dict,
        "config": {
            "workspace": str,
            "state_dir": str,
            "gravity_db": str,
            "db_exists": bool
        }
    }
}
```

**Example:**
```python
from core.nautilus import get_status

status = get_status()
total_chunks = status["nautilus"]["phase_1_gravity"]["total_chunks"]
print(f"Tracking {total_chunks} memory chunks")
```

---

### `run_maintain(register_recent=False, verbose=False)`

Run all Nautilus maintenance tasks.

**Parameters:**
- `register_recent` (bool, default=False): Register files modified in last 24h
- `verbose` (bool, default=False): Print progress to stderr

**Returns:**
```python
{
    "chambers": {
        "atrium": int,
        "corridor": int,
        "vault": int
    },
    "tagged": int,  # Files tagged
    "decayed": int,  # Chunks decayed
    "mirrors_linked": int,  # Mirrors auto-linked
    "timestamp": str  # ISO timestamp
}
```

**Example:**
```python
from core.nautilus import run_maintain

# Full maintenance with recent file registration
result = run_maintain(register_recent=True, verbose=True)
print(f"Tagged {result['tagged']} files, decayed {result['decayed']} chunks")
```

---

### `classify_file(filepath)`

Classify a file into a chamber (atrium/corridor/vault) based on age.

**Parameters:**
- `filepath` (str): Path to file (relative to workspace)

**Returns:**
- `str`: Chamber name ("atrium" | "corridor" | "vault")

**Example:**
```python
from core.nautilus import classify_file

chamber = classify_file("memory/2026-02-14.md")
print(f"File belongs in: {chamber}")
```

---

### `get_gravity_score(filepath, line_start=0, line_end=0)`

Get the gravity score for a specific file or chunk.

**Parameters:**
- `filepath` (str): Path to file
- `line_start` (int, default=0): Start line (0 for whole file)
- `line_end` (int, default=0): End line (0 for whole file)

**Returns:**
```python
{
    "path": str,
    "lines": str,  # "start:end"
    "access_count": int,
    "reference_count": int,
    "explicit_importance": float,
    "days_since_write": float,
    "days_since_access": float,
    "effective_mass": float,
    "modifier": float,
    "superseded_by": str | null,
    "exists": bool
}
```

**Example:**
```python
from core.nautilus import get_gravity_score

score = get_gravity_score("memory/2026-02-14.md")
print(f"Effective mass: {score['effective_mass']}")
print(f"Score modifier: {score['modifier']}x")
```

---

### `nautilus_info()`

Get metadata about the Nautilus system.

**Returns:**
```python
{
    "name": "Nautilus Memory Palace",
    "version": str,
    "phases": [
        {
            "id": int,
            "name": str,
            "description": str
        },
        ...
    ],
    "workspace": str,
    "state_dir": str,
    "gravity_db": str
}
```

**Example:**
```python
from core.nautilus import nautilus_info

info = nautilus_info()
print(f"Nautilus v{info['version']}")
print(f"Database: {info['gravity_db']}")
```

---

## Configuration API (`core.nautilus.config`)

### `get_workspace()`

Get the workspace directory path.

**Returns:** `pathlib.Path`

**Resolution order:**
1. `OPENCLAW_WORKSPACE` environment variable
2. Config file `workspace` key
3. Inferred from package location
4. Current working directory

**Example:**
```python
from core.nautilus.config import get_workspace

workspace = get_workspace()
print(f"Workspace: {workspace}")
```

---

### `get_state_dir()`

Get the state directory for Nautilus data.

**Returns:** `pathlib.Path`

**Default:** `~/.openclaw/state/nautilus/`

**Example:**
```python
from core.nautilus.config import get_state_dir

state_dir = get_state_dir()
print(f"State directory: {state_dir}")
```

---

### `get_gravity_db_path()`

Get the path to the gravity database file.

**Returns:** `pathlib.Path`

**Default:** `<state_dir>/gravity.db`

---

### `get_memory_dir()`

Get the memory directory path.

**Returns:** `pathlib.Path`

**Default:** `<workspace>/memory/`

---

### `get_corridors_dir()`

Get the corridors directory (summarized memories).

**Returns:** `pathlib.Path`

**Default:** `<memory_dir>/corridors/`

---

### `get_vaults_dir()`

Get the vaults directory (distilled lessons).

**Returns:** `pathlib.Path`

**Default:** `<memory_dir>/vaults/`

---

### `get_nautilus_config()`

Get the nautilus-specific configuration section.

**Returns:** `dict`

**Example:**
```python
from core.nautilus.config import get_nautilus_config

config = get_nautilus_config()
print(f"Auto-classify enabled: {config.get('auto_classify', True)}")
```

---

### `is_auto_classify_enabled()`

Check if auto-classify is enabled in config.

**Returns:** `bool` (default: `True`)

---

### `get_decay_interval_hours()`

Get the decay interval in hours.

**Returns:** `int` (default: `168` = 7 days)

---

### `migrate_legacy_db()`

Migrate gravity.db from legacy location to new state directory.

**Returns:** `bool` (True if migration was performed)

**Example:**
```python
from core.nautilus.config import migrate_legacy_db

if migrate_legacy_db():
    print("Legacy database migrated successfully")
```

---

## Gravity API (`core.nautilus.gravity`)

### Configuration Constants

```python
DECAY_RATE = 0.05  # Mass lost per day since last write
RECENCY_HALF_LIFE = 14  # Days for recency factor to halve
AUTHORITY_BOOST = 0.3  # Bonus multiplier for recently-written chunks
MASS_CAP = 100.0  # Prevent runaway accumulation
```

---

### `get_db()`

Get or create the gravity database connection.

**Returns:** `sqlite3.Connection`

**Schema:**
```sql
CREATE TABLE gravity (
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    access_count INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0,
    explicit_importance REAL DEFAULT 0.0,
    last_accessed_at TEXT,
    last_written_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    superseded_by TEXT DEFAULT NULL,
    tags TEXT DEFAULT '[]',
    context_tags TEXT DEFAULT '[]',
    chamber TEXT DEFAULT 'atrium',
    promoted_at TEXT,
    source_chunk TEXT,
    PRIMARY KEY (path, line_start, line_end)
);

CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    accessed_at TEXT DEFAULT (datetime('now')),
    query TEXT DEFAULT NULL,
    score REAL DEFAULT NULL
);

CREATE TABLE mirrors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL,
    granularity TEXT NOT NULL CHECK(granularity IN ('raw', 'summary', 'lesson')),
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(event_key, granularity)
);
```

---

### `compute_effective_mass(row)`

Compute effective mass for a gravity row.

**Parameters:**
- `row` (sqlite3.Row): Database row from gravity table

**Returns:** `float` (effective mass score)

**Formula:**
```python
base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
recency_factor = 1.0 / (1.0 + days_since_write × DECAY_RATE)
authority_boost = AUTHORITY_BOOST if days_since_write < 2.0 else 0.0
effective_mass = min(base_mass × recency_factor + authority_boost, MASS_CAP)
```

**Example:**
```python
from core.nautilus.gravity import get_db, compute_effective_mass

db = get_db()
row = db.execute("SELECT * FROM gravity WHERE path = ?", ("memory/2026-02-14.md",)).fetchone()
mass = compute_effective_mass(row)
print(f"Effective mass: {mass:.3f}")
```

---

### `gravity_score_modifier(effective_mass)`

Convert effective mass to a search score multiplier.

**Parameters:**
- `effective_mass` (float): Effective mass from `compute_effective_mass()`

**Returns:** `float` (multiplier >= 1.0)

**Formula:**
```python
modifier = 1.0 + 0.1 × log(1.0 + effective_mass)
```

**Mass → Modifier Examples:**
- Mass 0: 1.00x (no change)
- Mass 5: 1.18x
- Mass 20: 1.30x
- Mass 100: 1.46x

---

### CLI Commands

#### `cmd_record_access(args)`

Record that a memory chunk was accessed.

**Args format:** `["<path>", "--lines", "START:END", "--query", "Q", "--score", "S"]`

**Example:**
```python
from core.nautilus.gravity import cmd_record_access

cmd_record_access(["memory/2026-02-14.md", "--lines", "1:50", "--query", "project status"])
```

---

#### `cmd_record_write(args)`

Record that a memory file was written/updated.

**Args format:** `["<path>"]`

**Example:**
```python
from core.nautilus.gravity import cmd_record_write

cmd_record_write(["memory/2026-02-14.md"])
```

---

#### `cmd_boost(args)`

Explicitly boost a memory's importance.

**Args format:** `["<path>", "--amount", "N", "--lines", "START:END"]`

**Example:**
```python
from core.nautilus.gravity import cmd_boost

# Boost by 5.0
cmd_boost(["memory/critical-decision.md", "--amount", "5.0"])
```

---

#### `cmd_decay(args)`

Apply gravity decay to stale memories.

**Args format:** `[]`

**Returns:** `dict`

**Example:**
```python
from core.nautilus.gravity import cmd_decay

result = cmd_decay([])
print(f"Decayed {result['decayed']} chunks")
```

---

#### `cmd_score(args)`

Get the gravity score for a specific path.

**Args format:** `["<path>", "--lines", "START:END"]`

---

#### `cmd_top(args)`

Show highest-gravity memories.

**Args format:** `["--n", "10"]`

**Example:**
```python
from core.nautilus.gravity import cmd_top

cmd_top(["--n", "10"])  # Prints JSON to stdout
```

---

#### `cmd_rerank(args)`

Re-rank memory_search results using gravity scores.

**Args format:** `["--json", "<results_json>"]` or via stdin

**Example:**
```python
import json
from core.nautilus.gravity import cmd_rerank

results = [
    {"path": "memory/2026-02-14.md", "score": 0.7, "snippet": "..."}
]
cmd_rerank(["--json", json.dumps(results)])
```

---

#### `cmd_stats(args)`

Show database statistics.

**Args format:** `[]`

---

#### `cmd_supersede(args)`

Mark a chunk as superseded by a newer one.

**Args format:** `["<old_path>", "<new_path>"]`

---

## Chambers API (`core.nautilus.chambers`)

### Configuration Constants

```python
ATRIUM_MAX_AGE_HOURS = 48  # Atrium holds last 48 hours
CORRIDOR_MAX_AGE_DAYS = 7  # Corridor holds 2-7 days
SUMMARY_MODEL = "llama3.2:3b"  # Ollama model for summarization
```

---

### `classify_chamber(filepath)`

Determine which chamber a file belongs to based on age.

**Parameters:**
- `filepath` (str): Path to file

**Returns:** `str` ("atrium" | "corridor" | "vault")

**Example:**
```python
from core.nautilus.chambers import classify_chamber

chamber = classify_chamber("memory/2026-02-14.md")
print(f"Chamber: {chamber}")
```

---

### `file_age_days(filepath)`

Get the age of a file in days.

**Parameters:**
- `filepath` (str): Path to file

**Returns:** `float` (age in days)

**Algorithm:**
1. Try to parse YYYY-MM-DD from filename
2. Fall back to file mtime
3. Return 999 if file doesn't exist

---

### `llm_summarize(text, mode="corridor")`

Use local Ollama to summarize text.

**Parameters:**
- `text` (str): Text to summarize
- `mode` (str): "corridor" (2-4 paragraphs) or "vault" (bullet points)

**Returns:** `str` (summary text or error message)

**Example:**
```python
from core.nautilus.chambers import llm_summarize

summary = llm_summarize(content, mode="corridor")
```

---

### CLI Commands

#### `cmd_classify(args)`

Auto-classify all memory files into chambers.

**Args format:** `[<path1>, <path2>, ...]` or `[]` for all files

**Returns:** `dict`

---

#### `cmd_promote(args)`

Promote atrium memories (>48h) to corridor (summarized).

**Args format:** `["--dry-run"]` (optional)

**Returns:**
```python
{
    "promoted": int,
    "details": [
        {
            "source": str,
            "summary": str,
            "original_size": int,
            "summary_size": int
        },
        ...
    ],
    "timestamp": str
}
```

---

#### `cmd_crystallize(args)`

Crystallize corridor summaries (>7d) into vault lessons.

**Args format:** `["--dry-run"]` (optional)

**Returns:**
```python
{
    "crystallized": int,
    "details": [
        {
            "source": str,
            "vault": str,
            "lessons_size": int
        },
        ...
    ],
    "timestamp": str
}
```

---

#### `cmd_status(args)`

Show chamber distribution and recent promotions.

**Args format:** `[]`

---

## Doors API (`core.nautilus.doors`)

### Context Patterns

```python
CONTEXT_PATTERNS = {
    "project:ourblock": [...],
    "project:nautilus": [...],
    "project:voice": [...],
    "project:smart-home": [...],
    "system:security": [...],
    "system:infrastructure": [...],
    "person:dan": [...],
    "person:katy": [...],
    "topic:philosophy": [...],
    "topic:creative": [...],
    "topic:aa-recovery": [...]
}
```

---

### `classify_text(text)`

Classify text into context tags based on pattern matching.

**Parameters:**
- `text` (str): Text to classify

**Returns:** `List[str]` (context tags, sorted by match score)

**Example:**
```python
from core.nautilus.doors import classify_text

tags = classify_text("Working on voice listener terminal bug")
print(tags)  # ["project:voice", "system:infrastructure"]
```

---

### CLI Commands

#### `cmd_classify(args)`

Classify a query's context.

**Args format:** `["query", "text", "..."]`

**Returns:**
```python
{
    "query": str,
    "context_tags": List[str],
    "primary": str | null
}
```

---

#### `cmd_tag(args)`

Manually tag a file with a context.

**Args format:** `["<path>", "<tag>"]`

**Returns:**
```python
{
    "path": str,
    "tag": str,
    "status": "added"
}
```

---

#### `cmd_auto_tag(args)`

Auto-tag all memory files based on content analysis.

**Args format:** `[]`

**Returns:**
```python
{
    "files_tagged": int,
    "tag_distribution": {
        "tag1": count1,
        "tag2": count2,
        ...
    }
}
```

---

## Mirrors API (`core.nautilus.mirrors`)

### CLI Commands

#### `cmd_create(args)`

Create a mirror set for an event.

**Args format:** `["<event_key>", "--raw", "<path>", "--summary", "<path>", "--lesson", "<path>"]`

**Example:**
```python
from core.nautilus.mirrors import cmd_create

cmd_create([
    "daily-2026-02-14",
    "--raw", "memory/2026-02-14.md",
    "--summary", "corridors/corridor-2026-02-14.md"
])
```

---

#### `cmd_link(args)`

Link three granularity levels for the same event.

**Args format:** `["<event_key>", "<raw_path>", "<summary_path>", "<vault_path>"]`

---

#### `cmd_resolve(args)`

Find all granularity levels for a path or event key.

**Args format:** `["<path_or_event_key>"]`

**Returns:**
```python
{
    "event_key": str,
    "mirrors": [
        {
            "id": int,
            "event_key": str,
            "granularity": "raw" | "summary" | "lesson",
            "path": str,
            "created_at": str
        },
        ...
    ],
    "found": bool
}
```

---

#### `cmd_stats(args)`

Show mirror coverage statistics.

**Args format:** `[]`

**Returns:**
```python
{
    "total_events": int,
    "coverage": {
        "raw": int,
        "summary": int,
        "lesson": int
    },
    "fully_mirrored": int,
    "partially_mirrored": int,
    "partial_details": [
        {
            "event": str,
            "has": str  # "raw,summary"
        },
        ...
    ]
}
```

---

#### `cmd_auto_link(args)`

Auto-detect and link corridor summaries to their raw sources.

**Args format:** `[]`

**Returns:**
```python
{
    "linked": int
}
```

---

## Search Pipeline (`core.nautilus.search`)

### `run_full_search(query, n=5, trapdoor=False, verbose=False, chambers_filter=None)`

Run the full Nautilus search pipeline.

**Pipeline Steps:**
1. Classify context (Doors) — detect project/topic tags
2. Search with chamber awareness (Chambers) — run base memory search
3. Apply gravity re-ranking (Gravity) — adjust scores by importance
4. Filter by chambers (if specified) — atrium/corridor/vault
5. Apply context filter (unless trapdoor) — boost matching tags
6. Resolve mirrors (Mirrors) — find alternate granularities for top results

**Returns:** Same as main API `search()` function

---

### Internal Functions

#### `_apply_gravity(results, verbose=False)`

Apply gravity re-ranking to search results.

**Parameters:**
- `results` (List[dict]): Raw search results
- `verbose` (bool): Print progress

**Returns:** `List[dict]` (reranked results)

---

#### `_filter_by_chambers(results, allowed_chambers)`

Filter results by chamber.

**Parameters:**
- `results` (List[dict]): Search results
- `allowed_chambers` (set): Set of chamber names

**Returns:** `List[dict]` (filtered results)

---

#### `_apply_context_filter(results, context_tags, verbose=False)`

Apply context filtering to results.

**Parameters:**
- `results` (List[dict]): Search results
- `context_tags` (List[str]): Detected context tags
- `verbose` (bool): Print progress

**Returns:** `List[dict]` (filtered + boosted results)

---

#### `_resolve_mirrors(results)`

Resolve mirrors for top results.

**Parameters:**
- `results` (List[dict]): Search results

**Returns:** `dict` (mirror information keyed by path)

---

## CLI Command Reference

All CLI commands are accessible via:

```bash
python -m core.nautilus <command> [args]
# or
emergence nautilus <command> [args]
```

### Command List

| Command | Module | Description |
|---------|--------|-------------|
| `search` | cli | Full pipeline search |
| `status` | cli | System status |
| `maintain` | cli | Run maintenance |
| `classify` | cli | Classify files |
| `gravity` | cli | Show gravity score |
| `chambers` | cli | Chambers subcommands |
| `doors` | cli | Doors subcommands |
| `mirrors` | cli | Mirrors subcommands |

### Gravity Subcommands

```bash
python -m core.nautilus.gravity <command>
```

- `record-access <path> [--lines START:END] [--query Q] [--score S]`
- `record-write <path>`
- `boost <path> [--amount N] [--lines START:END]`
- `decay`
- `score <path> [--lines START:END]`
- `top [--n N]`
- `rerank --json <results>` or via stdin
- `stats`
- `supersede <old_path> <new_path>`

### Chambers Subcommands

```bash
python -m core.nautilus.chambers <command>
```

- `classify [path...]`
- `promote [--dry-run]`
- `crystallize [--dry-run]`
- `status`

### Doors Subcommands

```bash
python -m core.nautilus.doors <command>
```

- `classify <query>`
- `tag <path> <tag>`
- `auto-tag`

### Mirrors Subcommands

```bash
python -m core.nautilus.mirrors <command>
```

- `create <event_key> --raw <path> [--summary <path>] [--lesson <path>]`
- `link <event_key> <raw_path> <summary_path> [vault_path]`
- `resolve <path_or_event_key>`
- `stats`
- `auto-link`

---

## Error Handling

All API functions may raise:

- `sqlite3.Error` — Database errors
- `FileNotFoundError` — Missing files or directories
- `json.JSONDecodeError` — Invalid JSON in database fields
- `subprocess.TimeoutExpired` — Ollama timeout during summarization
- `ValueError` — Invalid parameters

**Best Practice:**

```python
try:
    results = search("query", n=10)
except Exception as e:
    print(f"Search failed: {e}")
    # Fall back to basic memory search
```

---

## Type Annotations

For type-safe usage, add type hints:

```python
from typing import Dict, List, Optional, Any
from pathlib import Path

def my_search(query: str, n: int = 5) -> Dict[str, Any]:
    from core.nautilus import search
    return search(query, n=n)
```

---

## Performance Considerations

### Database Connections

Always close database connections when done:

```python
from core.nautilus.gravity import get_db

db = get_db()
try:
    # Use database
    results = db.execute("SELECT * FROM gravity").fetchall()
finally:
    db.close()
```

### Batch Operations

For bulk updates, use transactions:

```python
db = get_db()
try:
    for filepath in files:
        db.execute("UPDATE gravity SET chamber = ? WHERE path = ?", (chamber, filepath))
    db.commit()
finally:
    db.close()
```

### Search Optimization

For best performance:

1. Use chamber filters when possible
2. Enable trapdoor for exact phrase recall (bypasses context filtering)
3. Keep `n` parameter reasonable (<20)
4. Run maintenance during off-hours (nightly cron)

---

## Version Compatibility

**Current Version:** 0.4.0

**Breaking Changes from 0.3.0:**
- None (fully backward compatible)

**New in 0.4.0:**
- Enhanced documentation
- Improved error messages
- Additional type safety

**Migration from tools/nautilus:**

The old `tools/nautilus/` implementation is deprecated. Use `core.nautilus` instead:

```python
# Old (deprecated)
from tools.nautilus import nautilus
nautilus.search("query")

# New (v0.3.0+)
from core.nautilus import search
search("query")
```

---

## Related Documentation

- [User Guide](USER_GUIDE.md) — Getting started and concepts
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues
- [Examples](EXAMPLES.md) — Code examples and workflows
