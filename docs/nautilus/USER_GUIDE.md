# Nautilus User Guide

**Version:** 0.4.0  
**Last Updated:** 2026-02-14

---

## What is Nautilus?

Nautilus is a **Memory Palace Architecture** for AI agents — a four-phase system that transforms flat memory into a layered, importance-weighted, context-aware knowledge base. Think of it as an intelligent filing system that knows what matters, when it matters, and how to surface it.

### The Four Phases

| Phase | Name | Purpose |
|-------|------|---------|
| **Phase 1** | **Gravity** | Importance-weighted scoring — frequently accessed memories "gain mass" |
| **Phase 2** | **Chambers** | Temporal layers — recent (atrium), summarized (corridor), distilled (vault) |
| **Phase 3** | **Doors** | Context-aware filtering — pre-filter by project/topic before search |
| **Phase 4** | **Mirrors** | Multi-granularity indexing — same event at raw, summary, and lesson levels |

---

## Getting Started

### Installation

Nautilus is built into Emergence v0.3.0+. If you're using OpenClaw with the Emergence framework, you already have it.

```bash
# Verify installation
emergence nautilus --help
```

### First Run

1. **Check system status:**
   ```bash
   emergence nautilus status
   ```

2. **Run initial maintenance:**
   ```bash
   emergence nautilus maintain --register-recent --verbose
   ```

3. **Try a search:**
   ```bash
   emergence nautilus search "your query" --n 5
   ```

That's it! Nautilus will automatically classify, tag, and score your memories on first run.

---

## Core Concepts

### 🌊 Gravity: Importance Scoring

Every memory chunk has a **mass score** based on:

- **Access count** — how often it's been retrieved
- **Reference count** — how many other memories link to it
- **Explicit importance** — manual boosts you've added
- **Recency** — recently written content gets authority boost

**Formula:**
```
base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
recency_factor = 1 / (1 + days_since_last_write × 0.05)
effective_mass = min(base_mass × recency_factor, 100.0)
```

**Search Impact:**  
High-mass memories surface more easily: `final_score = similarity × (1 + 0.1 × log(1 + mass))`

**Key Features:**
- **Write-date authority** — newer writes outrank old (prevents stale info)
- **Recency decay** — untouched memories fade over time
- **Supersession tagging** — corrected info replaces outdated chunks
- **Mass cap** — prevents runaway accumulation (max 100.0)

### 📂 Chambers: Temporal Memory Layers

Memories are automatically classified into three chambers based on age:

| Chamber | Age | Fidelity | Purpose |
|---------|-----|----------|---------|
| **Atrium** | Last 48 hours | Full verbatim | Recent interactions, fresh context |
| **Corridor** | 2-7 days | Summarized | Compressed daily narratives |
| **Vault** | 7+ days | Distilled | Permanent lessons and patterns |

**Automatic Promotion:**
- **Promoter** (nightly): Atrium → Corridor after 48h (summarize + re-embed)
- **Crystallizer** (weekly): Corridor → Vault after 7d (distill lessons + re-embed)

**Why This Matters:**
- Recent memories stay fresh and detailed
- Old memories compress into wisdom without losing retrievability
- Storage efficiency improves over time

### 🚪 Doors: Context-Aware Filtering

Before searching, Nautilus classifies your query into context tags:

**Context Categories:**
- `project:<name>` — OurBlock, Nautilus, Voice Listener, Smart Home
- `person:<name>` — Dan, Katy, etc.
- `system:<component>` — Security, Infrastructure
- `topic:<theme>` — Philosophy, Creative, AA Recovery

**How It Works:**
1. Query analyzed for keywords and patterns
2. Context tags assigned (e.g., "voice listener debug" → `project:voice`, `system:infrastructure`)
3. Search pre-filtered to relevant memories
4. Results boosted by context match score

**Trapdoor Mode:**  
Bypass all filtering with `--trapdoor` flag for explicit recall.

### 🪞 Mirrors: Multi-Granularity Indexing

The same event indexed at three levels of detail:

| Granularity | Example |
|-------------|---------|
| **Raw** | "Dan and I debugged the pf firewall. Cast devices needed inbound on ports 8768-8799..." |
| **Summary** | "Fixed voice casting — pf firewall was blocking Cast device inbound connections" |
| **Lesson** | "Security hardening can break functionality. Cast devices need bidirectional network access." |

Each level has different embeddings — you can find the lesson by concept even when details fade.

---

## CLI Commands

### Search

**Full pipeline search** (gravity + context + chambers):

```bash
emergence nautilus search "query text" [options]
```

**Options:**
- `--n N` — Number of results (default: 5)
- `--trapdoor` — Bypass context filtering
- `--verbose` — Show pipeline steps
- `--chamber CHAMBERS` — Filter to specific chambers (atrium,corridor,vault)

**Examples:**
```bash
# Basic search
emergence nautilus search "project status"

# More results with verbose output
emergence nautilus search "security review" --n 10 --verbose

# Search only recent memories
emergence nautilus search "yesterday's conversation" --chamber atrium

# Explicit recall (no filtering)
emergence nautilus search "banana jamba" --trapdoor
```

### Status

**Show system status:**

```bash
emergence nautilus status
```

**Output includes:**
- Gravity stats (total chunks, accesses, tagged coverage)
- Chamber distribution (atrium/corridor/vault counts)
- Doors patterns (context categories defined)
- Mirrors coverage (multi-granularity linking)
- Config paths and database status

### Maintain

**Run all maintenance tasks:**

```bash
emergence nautilus maintain [options]
```

**Options:**
- `--register-recent` — Register files modified in last 24h
- `--verbose` — Show detailed progress

**Tasks performed:**
1. Register recently modified files (if `--register-recent`)
2. Classify files into chambers (by age)
3. Auto-tag with context categories
4. Run gravity decay (reduce importance of stale memories)
5. Auto-link mirrors (corridor summaries ↔ raw sources)

**Example:**
```bash
emergence nautilus maintain --register-recent --verbose
```

**Recommended Schedule:**  
Run nightly via cron at 3:00 AM.

### Classify

**Classify files into chambers:**

```bash
emergence nautilus classify [file]
```

**Examples:**
```bash
# Classify all memory files
emergence nautilus classify

# Classify specific file
emergence nautilus classify memory/2026-02-14.md
```

### Gravity

**Show gravity score for a file:**

```bash
emergence nautilus gravity <file> [options]
```

**Options:**
- `--lines START:END` — Show score for specific line range

**Examples:**
```bash
emergence nautilus gravity memory/2026-02-14.md
emergence nautilus gravity memory/2026-02-14.md --lines 1:50
```

**Output:**
```json
{
  "path": "memory/2026-02-14.md",
  "lines": "0:0",
  "access_count": 12,
  "reference_count": 3,
  "explicit_importance": 2.0,
  "days_since_write": 0.5,
  "days_since_access": 0.1,
  "effective_mass": 5.234,
  "modifier": 1.187,
  "superseded_by": null,
  "exists": true
}
```

### Chambers Subcommands

**Show chamber distribution:**
```bash
emergence nautilus chambers status
```

**Promote atrium → corridor:**
```bash
emergence nautilus chambers promote [--dry-run]
```

**Crystallize corridor → vault:**
```bash
emergence nautilus chambers crystallize [--dry-run]
```

### Doors Subcommands

**Classify query context:**
```bash
emergence nautilus doors classify "query text"
```

**Auto-tag all memory files:**
```bash
emergence nautilus doors auto-tag
```

**Manually tag a file:**
```bash
emergence nautilus doors tag <file> <tag>
```

**Example:**
```bash
emergence nautilus doors tag memory/2026-02-14.md project:ourblock
```

### Mirrors Subcommands

**Show mirror statistics:**
```bash
emergence nautilus mirrors stats
```

**Find all granularity levels for a path:**
```bash
emergence nautilus mirrors resolve <path>
```

**Auto-link corridor summaries:**
```bash
emergence nautilus mirrors auto-link
```

---

## Understanding the Room Dashboard

When you run `emergence room`, Nautilus metrics appear in the dashboard:

### Gravity Section
```
Phase 1: Gravity
  Total Chunks: 1,861
  Total Accesses: 342
  Superseded: 12
  Tagged: 426/1,861 (23%)
  Effective Mass Range: 0.0 - 87.3
```

**What to look for:**
- **Tagged coverage** should increase over time as auto-tag runs
- **Superseded** count shows how many outdated chunks have been replaced
- **Total accesses** grows with search usage

### Chambers Section
```
Phase 2: Chambers
  Atrium: 2 files (last 48h)
  Corridor: 7 files (summaries)
  Vault: 3 files (distilled)
  Recent Promotions: 5
```

**What to look for:**
- **Atrium** should contain ~2-3 recent daily logs
- **Corridor** grows as daily logs age out (summaries created)
- **Vault** contains distilled wisdom from old corridors

### Doors Section
```
Phase 3: Doors
  Patterns Defined: 11
  Top Tags: project:ourblock (43), project:voice (28), system:security (19)
```

**What to look for:**
- **Tag distribution** shows which topics dominate your memory

### Mirrors Section
```
Phase 4: Mirrors
  Total Events: 7
  Fully Mirrored: 7 (raw + summary + lesson)
  Partially Mirrored: 0
```

**What to look for:**
- **Fully mirrored** events have all three granularity levels indexed

---

## Session Hooks

Nautilus integrates with your agent session lifecycle:

### On Session Start
```python
# In your agent initialization
from core.nautilus import get_status

status = get_status()
# Use status to understand current memory state
```

### On Memory Access
```python
# When retrieving memories
from core.nautilus import search

results = search("your query", n=10)
# Automatically updates access counts and gravity scores
```

### Nightly Maintenance

**Recommended cron job** (runs at 3:00 AM):

```bash
0 3 * * * cd /path/to/workspace && python3 -m core.cli nautilus maintain --register-recent --verbose >> logs/nautilus-maintain.log 2>&1
```

**What it does:**
1. Registers files modified in last 24h
2. Promotes 48h+ memories to corridor (summarized)
3. Crystallizes 7d+ corridors to vault (distilled)
4. Applies gravity decay to stale memories
5. Auto-links new corridor summaries to raw sources

---

## Configuration

### Config File

Create `~/.openclaw/config/emergence.json`:

```json
{
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus",
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable Nautilus system |
| `state_dir` | string | `~/.openclaw/state/nautilus` | Database storage directory |
| `gravity_db` | string | `<state_dir>/gravity.db` | Gravity database path |
| `memory_dir` | string | `memory` | Memory files directory (relative to workspace) |
| `auto_classify` | boolean | `true` | Auto-classify files into chambers |
| `decay_interval_hours` | integer | `168` (7 days) | How often to run gravity decay |

### Path Resolution

Paths are resolved in this order:

1. **Environment variables**: `OPENCLAW_WORKSPACE`, `OPENCLAW_STATE_DIR`
2. **Config file**: Paths in `emergence.json`
3. **Inference**: From package location or current working directory

**Override paths via environment:**
```bash
export OPENCLAW_WORKSPACE="/path/to/workspace"
export OPENCLAW_STATE_DIR="/custom/state/dir"
```

### Database Location

By default, gravity database lives at:
```
~/.openclaw/state/nautilus/gravity.db
```

**Migration:** On first run, Nautilus auto-migrates legacy databases from `tools/nautilus/gravity.db`.

---

## Best Practices

### 1. Run Nightly Maintenance

Set up a cron job to maintain your memory palace automatically:
```bash
0 3 * * * cd /path/to/workspace && emergence nautilus maintain --register-recent --verbose
```

### 2. Use Context Tags

Manually tag important memories with context:
```bash
emergence nautilus doors tag memory/important-meeting.md project:ourblock
```

### 3. Boost Critical Memories

Use gravity boost for memories you want to surface more:
```bash
# Boost importance by 5.0
python3 -m core.nautilus.gravity boost memory/critical-decision.md --amount 5.0
```

### 4. Review Chamber Distribution

Check periodically to ensure healthy distribution:
```bash
emergence nautilus chambers status
```

Healthy state:
- Atrium: 2-3 recent files
- Corridor: Growing collection of summaries
- Vault: Accumulating distilled wisdom

### 5. Use Trapdoor for Exact Recall

When you need to find something specific (like a unique phrase), bypass filtering:
```bash
emergence nautilus search "banana jamba" --trapdoor
```

### 6. Monitor Gravity Coverage

Aim for >50% tagged coverage over time:
```bash
emergence nautilus status | grep coverage
```

If coverage is low, run:
```bash
emergence nautilus doors auto-tag
```

---

## Advanced Features

### Custom Summarization

The corridor/vault builders use Ollama for summarization. You can customize the model:

Edit `projects/emergence/core/nautilus/chambers.py`:
```python
SUMMARY_MODEL = "llama3.2:3b"  # Change to your preferred model
```

### Manual Promotion

Force promote a specific file:
```bash
# Promote to corridor
python3 -m core.nautilus.chambers promote memory/2026-02-10.md

# Crystallize to vault
python3 -m core.nautilus.chambers crystallize corridors/corridor-2026-02-03.md
```

### Supersession

Mark outdated info as superseded:
```bash
python3 -m core.nautilus.gravity supersede \
  memory/old-info.md \
  memory/corrected-info.md
```

### Multi-Granularity Linking

Create explicit mirror links:
```bash
python3 -m core.nautilus.mirrors link \
  "event-key" \
  "memory/2026-02-14.md" \
  "corridors/corridor-2026-02-14.md" \
  "vaults/vault-2026-02-14.md"
```

---

## Integration with Other Tools

### With OpenClaw Memory Search

Nautilus enhances OpenClaw's built-in memory search:

```bash
# Standard OpenClaw search (vector + keyword)
openclaw memory search "query"

# Nautilus search (+ gravity + context + chambers)
emergence nautilus search "query"
```

Both work together — use OpenClaw for quick searches, Nautilus for important recalls.

### With Emergence Drives

Nautilus integrates with the Emergence drives system:

```python
# In your agent code
from core.nautilus import search
from core.drives import fire_drive

# When LEARNING drive fires
if drive == "LEARNING":
    results = search("recent lessons", chamber="vault")
    # Process distilled wisdom
```

### With Agent Memory

Use Nautilus in agent sessions:

```python
from core.nautilus import search, get_status, run_maintain

# Session start
status = get_status()
print(f"Memory palace has {status['nautilus']['phase_1_gravity']['total_chunks']} chunks")

# During conversation
results = search(user_query, n=5)

# Session end
run_maintain(register_recent=True)
```

---

## FAQ

### Q: How much storage does Nautilus use?

**A:** Minimal. The gravity database is typically <10MB even with thousands of chunks. Multi-granularity indexing (mirrors) adds 2-3x embedding volume but still under 50MB total.

### Q: Does it slow down searches?

**A:** Slightly. Adds ~50-100ms for gravity scoring + context filtering. Still fast enough for interactive use.

### Q: Can I disable auto-promotion?

**A:** Yes. Skip the `maintain` cron job. Files stay in atrium until manually promoted.

### Q: What if summarization fails?

**A:** Promotion continues with `[Summarization failed: <error>]` marker. You can manually fix later.

### Q: Can I use a different LLM for summaries?

**A:** Yes. Edit `SUMMARY_MODEL` in `chambers.py`. Any Ollama model works.

### Q: How do I reset gravity scores?

**A:** Delete the gravity database and run maintain:
```bash
rm ~/.openclaw/state/nautilus/gravity.db
emergence nautilus maintain --register-recent
```

### Q: Does it work with non-markdown files?

**A:** Currently optimized for `.md` files in the `memory/` directory. Extension to other formats is planned.

---

## Next Steps

1. **Run your first search:** `emergence nautilus search "your query"`
2. **Set up nightly maintenance:** Add cron job
3. **Review the dashboard:** `emergence room` (if using Emergence framework)
4. **Explore the API:** See [API_REFERENCE.md](API_REFERENCE.md)
5. **Check troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
6. **Try examples:** See [EXAMPLES.md](EXAMPLES.md)

---

**Related Documentation:**
- [API Reference](API_REFERENCE.md) — Python API and function reference
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues and solutions
- [Examples](EXAMPLES.md) — Workflow examples and recipes
