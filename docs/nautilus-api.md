# Nautilus API Reference

> 🐚 **Developer guide for extending and integrating Nautilus**

**Quick Links:** [User Guide](nautilus-user-guide.md) • [Troubleshooting](nautilus-troubleshooting.md) • [Main README](../README.md)

---

## Table of Contents

1. [Python API Overview](#python-api-overview)
2. [Core Functions](#core-functions)
3. [Extension Points](#extension-points)
4. [Database Schema](#database-schema)
5. [Examples](#examples)

---

## Python API Overview

Nautilus provides a Python API for programmatic access to all four phases. Import from `core.nautilus`:

```python
from core.nautilus import gravity, chambers, doors, mirrors
from core.nautilus.config import get_workspace, get_config, get_db_path
```

### Quick Start

```python
# Search with full pipeline
from core.nautilus.nautilus_cli import cmd_search
cmd_search(["quantum computing", "--n", "5"])

# Or use individual modules
from core.nautilus import gravity

# Record an access
gravity.cmd_record_access(["memory/2026-02-14.md", "--query", "test"])

# Get gravity score
gravity.cmd_score(["memory/2026-02-14.md"])
```

---

## Core Functions

### Gravity Module (`core.nautilus.gravity`)

#### `get_db() → sqlite3.Connection`

Get or create the gravity database with WAL mode enabled.

**Returns:** SQLite connection with `row_factory = sqlite3.Row`

**Example:**

```python
from core.nautilus.gravity import get_db

db = get_db()
rows = db.execute("SELECT * FROM gravity LIMIT 10").fetchall()
for row in rows:
    print(f"{row['path']}: {row['access_count']} accesses")
db.close()
```

#### `compute_effective_mass(row: sqlite3.Row) → float`

Calculate effective mass from gravity record.

**Parameters:**

- `row` — Database row with fields: `access_count`, `reference_count`, `explicit_importance`, `last_written_at`, `last_accessed_at`

**Returns:** Effective mass (float, 0.0 to `mass_cap`)

**Formula:**

```python
base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
recency_factor = 1.0 / (1.0 + days_since_write × decay_rate)
authority_boost = 0.3 if days_since_write < 2.0 else 0.0
effective_mass = min(base_mass × recency_factor + authority_boost, mass_cap)
```

**Example:**

```python
from core.nautilus.gravity import get_db, compute_effective_mass

db = get_db()
row = db.execute("SELECT * FROM gravity WHERE path = ?",
                 ("memory/2026-02-14.md",)).fetchone()
if row:
    mass = compute_effective_mass(row)
    print(f"Effective mass: {mass:.3f}")
db.close()
```

#### `gravity_score_modifier(effective_mass: float) → float`

Convert effective mass to a score multiplier.

**Parameters:**

- `effective_mass` — Effective mass value

**Returns:** Multiplier >= 1.0

**Formula:**

```python
modifier = 1.0 + 0.1 × log(1.0 + effective_mass)
```

**Scaling:**

- mass = 0 → modifier = 1.0 (no change)
- mass = 5 → modifier ≈ 1.18
- mass = 20 → modifier ≈ 1.30
- mass = 100 → modifier ≈ 1.46

**Example:**

```python
from core.nautilus.gravity import gravity_score_modifier

base_score = 0.75
mass = 10.0
modifier = gravity_score_modifier(mass)
adjusted_score = base_score * modifier
print(f"Base: {base_score}, Adjusted: {adjusted_score:.3f}")
# Output: Base: 0.75, Adjusted: 0.897
```

#### `cmd_record_access(args: list[str])`

Record that a memory chunk was accessed.

**Arguments:**

- `args[0]` — File path (relative to workspace)
- `--lines START:END` — Line range (optional)
- `--query Q` — Search query (optional)
- `--score S` — Similarity score (optional)

**Side effects:**

- Increments `access_count` in gravity table
- Updates `last_accessed_at` timestamp
- Inserts record in `access_log` table

**Example:**

```python
from core.nautilus.gravity import cmd_record_access

cmd_record_access([
    "memory/2026-02-14.md",
    "--lines", "42:68",
    "--query", "nautilus design",
    "--score", "0.8421"
])
```

#### `cmd_record_write(args: list[str])`

Record that a memory file was written/updated.

**Arguments:**

- `args[0]` — File path (relative to workspace)

**Side effects:**

- Updates `last_written_at` for all chunks in file
- Creates new record if file not tracked

**Example:**

```python
from core.nautilus.gravity import cmd_record_write

cmd_record_write(["memory/2026-02-15.md"])
```

#### `cmd_boost(args: list[str])`

Explicitly boost a memory's importance.

**Arguments:**

- `args[0]` — File path
- `--amount N` — Boost amount (default: 2.0)
- `--lines START:END` — Line range (optional)

**Example:**

```python
from core.nautilus.gravity import cmd_boost

cmd_boost([
    "memory/architecture-decisions.md",
    "--amount", "10.0"
])
```

#### `cmd_decay(args: list[str])`

Apply nightly decay to stale memories.

**Logic:**

- If not accessed in 30+ days AND not written in 14+ days
- Reduce `explicit_importance` by 10%

**Example:**

```python
from core.nautilus.gravity import cmd_decay

cmd_decay([])  # No arguments needed
```

#### `cmd_rerank(args: list[str])`

Re-rank memory search results using gravity scores.

**Arguments:**

- `--json <results>` — JSON array of search results

**Expected input format:**

```json
[
  {
    "path": "memory/2026-02-14.md",
    "startLine": 42,
    "endLine": 68,
    "score": 0.75,
    "snippet": "..."
  }
]
```

**Output format:**

```json
[
  {
    "path": "memory/2026-02-14.md",
    "startLine": 42,
    "endLine": 68,
    "score": 0.8964,
    "original_score": 0.75,
    "snippet": "...",
    "gravity": {
      "effective_mass": 12.341,
      "modifier": 1.195,
      "superseded": false
    }
  }
]
```

**Example:**

```python
from core.nautilus.gravity import cmd_rerank
import json

results = [
    {"path": "memory/test.md", "score": 0.75, "snippet": "..."}
]
cmd_rerank(["--json", json.dumps(results)])
```

---

### Chambers Module (`core.nautilus.chambers`)

#### `classify_chamber(filepath: str) → str`

Determine which chamber a file belongs to based on age.

**Parameters:**

- `filepath` — File path (relative to workspace)

**Returns:** `"atrium"`, `"corridor"`, or `"vault"`

**Logic:**

```python
age_days = file_age_days(filepath)
if age_days <= atrium_max_age_hours / 24:
    return "atrium"
elif age_days <= corridor_max_age_days:
    return "corridor"
else:
    return "vault"
```

**Example:**

```python
from core.nautilus.chambers import classify_chamber

chamber = classify_chamber("memory/2026-02-14.md")
print(f"Chamber: {chamber}")  # Output: Chamber: atrium
```

#### `llm_summarize(text: str, mode: str = "corridor") → str | None`

Summarize text using local Ollama with graceful fallback.

**Parameters:**

- `text` — Text to summarize (max 8000 chars for corridor, 6000 for vault)
- `mode` — `"corridor"` (narrative summary) or `"vault"` (distilled lessons)

**Returns:** Summary string, or `None` if Ollama unavailable

**Prompts:**

**Corridor mode:**

> Create a readable narrative (2-4 paragraphs) that preserves key decisions, interactions, problems solved, lessons learned, and searchable terms. Drop routine logs and verbose debugging.

**Vault mode:**

> Extract only long-term lessons: reusable patterns, architectural decisions, relationship insights, system knowledge. Format as themed bullet points.

**Example:**

```python
from core.nautilus.chambers import llm_summarize

text = open("memory/2026-02-14.md").read()
summary = llm_summarize(text, mode="corridor")

if summary:
    print(f"Summary ({len(summary)} chars):\n{summary}")
else:
    print("Summarization unavailable")
```

#### `cmd_classify(args: list[str])`

Auto-classify all memory files into chambers.

**Example:**

```python
from core.nautilus.chambers import cmd_classify

cmd_classify([])  # Classifies all files in memory/
```

#### `cmd_promote(args: list[str])`

Promote atrium files (>48h) to corridor with summarization.

**Arguments:**

- `--dry-run` — Show candidates without promoting

**Example:**

```python
from core.nautilus.chambers import cmd_promote

# Dry run
cmd_promote(["--dry-run"])

# Actual promotion
cmd_promote([])
```

#### `cmd_crystallize(args: list[str])`

Crystallize corridor summaries (>7d) into vault lessons.

**Arguments:**

- `--dry-run` — Show candidates without crystallizing

**Example:**

```python
from core.nautilus.chambers import cmd_crystallize

cmd_crystallize([])
```

---

### Doors Module (`core.nautilus.doors`)

#### `classify_text(text: str) → list[str]`

Classify text into context tags based on pattern matching.

**Parameters:**

- `text` — Text to classify (lowercased internally)

**Returns:** List of tags, sorted by match score

**Patterns:**

```python
CONTEXT_PATTERNS = {
    "project:nautilus": [r"nautilus", r"gravity", r"chamber", ...],
    "project:ourblock": [r"ourblock", r"supabase", ...],
    "person:dan": [r"\bdan\b", r"dan.aghili", ...],
    "system:security": [r"security", r"vault.enc", ...],
    # ... 15+ patterns total
}
```

**Example:**

```python
from core.nautilus.doors import classify_text

text = "Discussed nautilus gravity scoring with Dan"
tags = classify_text(text)
print(tags)  # Output: ['project:nautilus', 'person:dan']
```

#### `cmd_auto_tag(args: list[str])`

Auto-tag all memory files with context patterns.

**Logic:**

- Reads first 5KB of each file in `memory/`
- Classifies content
- Merges new tags with existing tags
- Updates `gravity` table

**Example:**

```python
from core.nautilus.doors import cmd_auto_tag

cmd_auto_tag([])
```

---

### Mirrors Module (`core.nautilus.mirrors`)

#### `cmd_link(args: list[str])`

Link three granularity levels for the same event.

**Arguments:**

- `args[0]` — Event key (unique identifier)
- `args[1]` — Raw path (atrium)
- `args[2]` — Summary path (corridor)
- `args[3]` — Vault path (optional)

**Example:**

```python
from core.nautilus.mirrors import cmd_link

cmd_link([
    "daily-2026-02-14",
    "memory/2026-02-14.md",
    "memory/corridors/corridor-2026-02-14.md",
    "memory/vaults/vault-2026-02-14.md"
])
```

#### `cmd_resolve(args: list[str])`

Find all granularity levels for a path or event key.

**Arguments:**

- `args[0]` — File path or event key

**Returns:** JSON with all mirrors for the event

**Example:**

```python
from core.nautilus.mirrors import cmd_resolve

cmd_resolve(["memory/2026-02-14.md"])
```

**Output:**

```json
{
  "event_key": "daily-2026-02-14",
  "mirrors": [
    {
      "granularity": "raw",
      "path": "memory/2026-02-14.md"
    },
    {
      "granularity": "summary",
      "path": "memory/corridors/corridor-2026-02-14.md"
    }
  ]
}
```

#### `cmd_auto_link(args: list[str])`

Auto-detect and link corridor summaries to raw sources.

**Logic:**

- Scans `memory/corridors/corridor-*.md`
- Extracts date from filename
- Links to `memory/YYYY-MM-DD.md` if exists

**Example:**

```python
from core.nautilus.mirrors import cmd_auto_link

cmd_auto_link([])
```

---

### Config Module (`core.nautilus.config`)

#### `get_workspace() → Path`

Get workspace directory with fallback chain.

**Fallback order:**

1. `OPENCLAW_WORKSPACE` environment variable
2. `emergence.json` config file
3. `~/.openclaw/workspace` (default)

**Example:**

```python
from core.nautilus.config import get_workspace

workspace = get_workspace()
print(f"Workspace: {workspace}")
```

#### `get_state_dir() → Path`

Get state directory with fallback chain.

**Fallback order:**

1. `EMERGENCE_STATE` environment variable
2. `emergence.json` config file
3. `~/.openclaw/state` (default)

**Example:**

```python
from core.nautilus.config import get_state_dir

state_dir = get_state_dir()
print(f"State: {state_dir}")
```

#### `get_config() → dict`

Load full Nautilus configuration from `emergence.json`.

**Returns:** Dictionary with all config options (see [User Guide](nautilus-user-guide.md#configuration))

**Example:**

```python
from core.nautilus.config import get_config

config = get_config()
print(f"Decay rate: {config['decay_rate']}")
print(f"Summarization model: {config['summarization']['model']}")
```

#### `get_db_path() → Path`

Get gravity database path with automatic migration detection.

**Returns:** Path to `gravity.db`

**Side effects:** Creates parent directories if needed

**Example:**

```python
from core.nautilus.config import get_db_path

db_path = get_db_path()
print(f"Database: {db_path}")
# Output: Database: /Users/you/.openclaw/state/nautilus/gravity.db
```

---

## Extension Points

### Custom Door Patterns

Add your own context detection patterns:

```python
from core.nautilus.doors import CONTEXT_PATTERNS, classify_text

# Add custom pattern
CONTEXT_PATTERNS["project:myproject"] = [
    r"myproject", r"custom.keyword", r"special.pattern"
]

# Use it
tags = classify_text("Discussion about myproject architecture")
print(tags)  # Output: ['project:myproject']
```

### Gravity Hooks

Extend gravity scoring with custom factors:

```python
from core.nautilus.gravity import compute_effective_mass, get_db

def compute_custom_mass(row):
    """Add custom factors to effective mass calculation."""
    base_mass = compute_effective_mass(row)

    # Custom factor: boost if path contains "critical"
    if "critical" in row['path']:
        base_mass *= 1.5

    # Custom factor: penalize if path contains "draft"
    if "draft" in row['path']:
        base_mass *= 0.5

    return base_mass

# Use it
db = get_db()
rows = db.execute("SELECT * FROM gravity").fetchall()
for row in rows:
    mass = compute_custom_mass(row)
    print(f"{row['path']}: {mass:.3f}")
db.close()
```

### Custom Context Classifiers

Implement ML-based context detection:

```python
from core.nautilus.doors import cmd_auto_tag
import sqlite3
from pathlib import Path

def ml_classify_context(text: str) -> list[str]:
    """
    Custom ML-based context classifier.
    Replace with your own model (e.g., sentence transformers).
    """
    # Placeholder: Use a simple keyword approach
    # In production, use embeddings + cosine similarity
    keywords = {
        "technical": ["bug", "error", "fix", "implementation"],
        "planning": ["roadmap", "milestone", "sprint", "goal"],
        "meeting": ["discussed", "meeting", "call", "sync"]
    }

    tags = []
    text_lower = text.lower()
    for tag, words in keywords.items():
        if any(word in text_lower for word in words):
            tags.append(f"topic:{tag}")

    return tags

def tag_all_with_ml():
    """Auto-tag all files using ML classifier."""
    from core.nautilus.config import get_workspace, get_db_path

    workspace = get_workspace()
    db = sqlite3.connect(str(get_db_path()))
    db.row_factory = sqlite3.Row

    memory_dir = workspace / "memory"
    for md_file in memory_dir.glob("*.md"):
        content = md_file.read_text()[:5000]
        tags = ml_classify_context(content)

        if tags:
            rel_path = str(md_file.relative_to(workspace))
            existing_tags = db.execute(
                "SELECT tags FROM gravity WHERE path = ?",
                (rel_path,)
            ).fetchone()

            if existing_tags:
                merged = list(set(existing_tags['tags'] + tags))
            else:
                merged = tags

            db.execute(
                "UPDATE gravity SET tags = ? WHERE path = ?",
                (json.dumps(merged), rel_path)
            )

    db.commit()
    db.close()

# Use it
tag_all_with_ml()
```

### Custom Summarization Prompts

Override default prompts for chamber promotion:

```python
from core.nautilus.chambers import llm_summarize
import subprocess
import json

def custom_summarize(text: str, mode: str = "corridor") -> str | None:
    """Custom summarization with different prompts."""

    if mode == "corridor":
        prompt = f"""You are creating a technical log summary. Focus on:
- Code changes and commits
- Technical decisions with rationale
- Bugs fixed and their root causes
- Performance metrics and benchmarks

Text:
{text[:8000]}

Summary:"""
    else:  # vault
        prompt = f"""Extract technical patterns:
- Architectural principles discovered
- Reusable code patterns
- Performance optimization techniques
- Debugging strategies that worked

Text:
{text[:6000]}

Patterns:"""

    # Call Ollama with custom prompt
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate", "-d",
             json.dumps({
                 "model": "llama3.2:3b",
                 "prompt": prompt,
                 "stream": False
             })],
            capture_output=True,
            text=True,
            timeout=120
        )
        response = json.loads(result.stdout)
        return response.get("response", "").strip()
    except:
        return None

# Use it in promotion
from core.nautilus.chambers import cmd_promote

# Monkey-patch the summarizer (not recommended for production)
import core.nautilus.chambers as chambers_mod
chambers_mod.llm_summarize = custom_summarize

cmd_promote([])
```

---

## Database Schema

### `gravity` table

**Primary table for importance tracking.**

| Column                | Type    | Description                                    |
| --------------------- | ------- | ---------------------------------------------- |
| `path`                | TEXT    | File path (relative to workspace)              |
| `line_start`          | INTEGER | Start line (0 = whole file)                    |
| `line_end`            | INTEGER | End line (0 = whole file)                      |
| `access_count`        | INTEGER | Number of times accessed                       |
| `reference_count`     | INTEGER | Number of cross-references (future)            |
| `explicit_importance` | REAL    | Manual importance boost                        |
| `last_accessed_at`    | TEXT    | ISO timestamp of last access                   |
| `last_written_at`     | TEXT    | ISO timestamp of last write                    |
| `created_at`          | TEXT    | ISO timestamp of record creation               |
| `superseded_by`       | TEXT    | Path to newer version (if superseded)          |
| `tags`                | TEXT    | JSON array of context tags                     |
| `chamber`             | TEXT    | Chamber classification (atrium/corridor/vault) |

**Primary key:** `(path, line_start, line_end)`

**Indexes:**

- `idx_gravity_path` on `path`
- `idx_gravity_chamber` on `chamber`

### `access_log` table

**Audit log of all memory accesses.**

| Column        | Type    | Description                      |
| ------------- | ------- | -------------------------------- |
| `id`          | INTEGER | Auto-increment primary key       |
| `path`        | TEXT    | File path                        |
| `line_start`  | INTEGER | Start line                       |
| `line_end`    | INTEGER | End line                         |
| `accessed_at` | TEXT    | ISO timestamp                    |
| `query`       | TEXT    | Search query that retrieved this |
| `score`       | REAL    | Similarity score from search     |
| `context`     | TEXT    | JSON context metadata            |

### `mirrors` table

**Multi-granularity event linking.**

| Column        | Type    | Description                   |
| ------------- | ------- | ----------------------------- |
| `id`          | INTEGER | Auto-increment primary key    |
| `event_key`   | TEXT    | Unique event identifier       |
| `granularity` | TEXT    | `raw`, `summary`, or `lesson` |
| `path`        | TEXT    | File path                     |
| `line_start`  | INTEGER | Start line (future use)       |
| `line_end`    | INTEGER | End line (future use)         |
| `created_at`  | TEXT    | ISO timestamp                 |

**Unique constraint:** `(event_key, granularity)`

**Indexes:**

- `idx_mirrors_event` on `event_key`
- `idx_mirrors_path` on `path`

---

## Examples

### Complete Search Implementation

```python
import json
import subprocess
from core.nautilus import gravity, doors
from core.nautilus.config import get_db_path

def semantic_search(query: str, n: int = 5, use_context: bool = True) -> list:
    """
    Full Nautilus search pipeline.

    Args:
        query: Search query
        n: Number of results
        use_context: Enable context filtering

    Returns:
        List of ranked results with gravity metadata
    """
    # Step 1: Classify context
    context_tags = []
    if use_context:
        context_tags = doors.classify_text(query)
        print(f"🚪 Context: {context_tags}")

    # Step 2: Run base memory search
    result = subprocess.run(
        ["openclaw", "memory", "search", query, "--max-results", str(n * 3), "--json"],
        capture_output=True,
        text=True,
        timeout=30
    )
    raw_results = json.loads(result.stdout)

    if not isinstance(raw_results, list):
        raw_results = raw_results.get('results', [])

    print(f"🔍 Base search: {len(raw_results)} results")

    # Step 3: Apply gravity re-ranking
    rerank_result = subprocess.run(
        ["python3", "-m", "core.nautilus.gravity", "rerank", "--json", json.dumps(raw_results)],
        capture_output=True,
        text=True,
        timeout=30
    )
    reranked = json.loads(rerank_result.stdout)

    print(f"⚖️ Gravity applied: {len(reranked)} results")

    # Step 4: Context filtering
    if use_context and context_tags:
        import sqlite3
        db = sqlite3.connect(str(get_db_path()))
        db.row_factory = sqlite3.Row

        filtered = []
        for r in reranked:
            path = r.get('path', '')
            row = db.execute(
                "SELECT tags FROM gravity WHERE path = ? LIMIT 1",
                (path,)
            ).fetchone()

            if row and row['tags']:
                file_tags = json.loads(row['tags'])
                overlap = len(set(context_tags) & set(file_tags))
                if overlap > 0:
                    r['context_match'] = overlap / len(context_tags)
                    filtered.append(r)
            else:
                # Untagged files pass through with neutral score
                r['context_match'] = 0.5
                filtered.append(r)

        db.close()
        results = sorted(filtered, key=lambda x: x['score'], reverse=True)
        print(f"🚪 Context filtered: {len(results)} results")
    else:
        results = reranked

    # Truncate to n
    return results[:n]

# Usage
results = semantic_search("nautilus architecture", n=5)
for r in results:
    print(f"\n{r['path']} (score: {r['score']:.3f})")
    print(f"  Gravity: {r['gravity']['effective_mass']:.2f} mass, "
          f"{r['gravity']['modifier']:.3f}x modifier")
    print(f"  Context: {r.get('context_match', 0):.2f}")
    print(f"  {r['snippet'][:100]}...")
```

### Custom Maintenance Script

```python
from core.nautilus import gravity, chambers, doors, mirrors
from pathlib import Path
from datetime import datetime
import json

def comprehensive_maintenance():
    """Run all Nautilus maintenance tasks."""

    print(f"🐚 Nautilus Maintenance - {datetime.now().isoformat()}\n")

    # 1. Register recent writes
    print("📝 Registering recent writes...")
    from core.nautilus.config import get_workspace
    import time

    workspace = get_workspace()
    memory_dir = workspace / "memory"
    now = time.time()
    day_ago = now - 86400

    registered = 0
    for md_file in memory_dir.glob("*.md"):
        if md_file.stat().st_mtime >= day_ago:
            rel_path = str(md_file.relative_to(workspace))
            gravity.cmd_record_write([rel_path])
            registered += 1

    print(f"   ✅ {registered} recent files registered\n")

    # 2. Classify chambers
    print("📂 Classifying chambers...")
    chambers.cmd_classify([])
    print()

    # 3. Auto-tag contexts
    print("🏷️  Auto-tagging...")
    doors.cmd_auto_tag([])
    print()

    # 4. Apply gravity decay
    print("⚖️  Applying gravity decay...")
    gravity.cmd_decay([])
    print()

    # 5. Link mirrors
    print("🔗 Auto-linking mirrors...")
    mirrors.cmd_auto_link([])
    print()

    # 6. Promote to corridor (dry run first)
    print("📊 Checking promotion candidates...")
    chambers.cmd_promote(["--dry-run"])
    print()

    response = input("Proceed with promotion? [y/N]: ")
    if response.lower() == 'y':
        print("\n🎯 Promoting to corridor...")
        chambers.cmd_promote([])
    else:
        print("   ⏭️  Skipped promotion")

    print("\n✅ Maintenance complete!")

# Run it
comprehensive_maintenance()
```

### Importance Analysis

```python
from core.nautilus.gravity import get_db, compute_effective_mass, days_since
import json

def analyze_importance_distribution():
    """Analyze gravity distribution across memory."""

    db = get_db()
    rows = db.execute("SELECT * FROM gravity").fetchall()

    # Compute mass for all chunks
    masses = []
    for row in rows:
        mass = compute_effective_mass(row)
        masses.append({
            "path": row['path'],
            "mass": mass,
            "access_count": row['access_count'],
            "days_since_write": days_since(row['last_written_at']),
            "days_since_access": days_since(row['last_accessed_at']),
            "chamber": row['chamber']
        })

    # Sort by mass
    masses.sort(key=lambda x: x['mass'], reverse=True)

    # Statistics
    total = len(masses)
    high_mass = [m for m in masses if m['mass'] > 10.0]
    medium_mass = [m for m in masses if 1.0 < m['mass'] <= 10.0]
    low_mass = [m for m in masses if m['mass'] <= 1.0]

    print(f"📊 Importance Distribution\n")
    print(f"Total chunks: {total}")
    print(f"High mass (>10): {len(high_mass)} ({len(high_mass)/total*100:.1f}%)")
    print(f"Medium mass (1-10): {len(medium_mass)} ({len(medium_mass)/total*100:.1f}%)")
    print(f"Low mass (<1): {len(low_mass)} ({len(low_mass)/total*100:.1f}%)")

    print(f"\n🏆 Top 10 by importance:\n")
    for i, m in enumerate(masses[:10], 1):
        print(f"{i}. {m['path']}")
        print(f"   Mass: {m['mass']:.2f} | Accesses: {m['access_count']} | "
              f"Written: {m['days_since_write']:.0f}d ago | "
              f"Chamber: {m['chamber']}")

    # Chamber breakdown
    chambers = {}
    for m in masses:
        ch = m['chamber']
        if ch not in chambers:
            chambers[ch] = []
        chambers[ch].append(m['mass'])

    print(f"\n📂 Chamber breakdown:\n")
    for ch, vals in chambers.items():
        avg = sum(vals) / len(vals) if vals else 0
        print(f"{ch}: {len(vals)} chunks, avg mass {avg:.2f}")

    db.close()

# Run it
analyze_importance_distribution()
```

---

## Next Steps

- **[User Guide](nautilus-user-guide.md)** — CLI usage, workflows, configuration
- **[Troubleshooting](nautilus-troubleshooting.md)** — Common errors and solutions
- **[Main README](../README.md)** — Emergence framework overview

---

_Extend mindfully. The API is your nautilus shell — add chambers as you grow._ 🐚
