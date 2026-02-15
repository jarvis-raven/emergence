# Nautilus User Guide

> 🐚 **Memory Palace with Gravity** — Intelligent, importance-weighted memory retrieval for Emergence agents

**Quick Links:** [API Reference](nautilus-api.md) • [Troubleshooting](nautilus-troubleshooting.md) • [Main README](../README.md)

---

## Table of Contents

1. [What is Nautilus?](#what-is-nautilus)
2. [Installation & Setup](#installation--setup)
3. [Core Concepts](#core-concepts)
4. [CLI Reference](#cli-reference)
5. [Example Workflows](#example-workflows)
6. [Configuration](#configuration)
7. [Integration with Drives](#integration-with-drives)
8. [Best Practices](#best-practices)

---

## What is Nautilus?

**Nautilus** is an intelligent memory system for AI agents that combines four complementary layers to make memory retrieval smarter:

### The Four Phases

1. **Gravity (Phase 1)** — Importance-weighted scoring
   - Tracks which memories get accessed most
   - Boosts recently-written content (authority)
   - Applies recency decay to stale memories
   - Re-ranks search results by "effective mass"

2. **Chambers (Phase 2)** — Temporal organization
   - **Atrium**: Last 48 hours (full fidelity)
   - **Corridor**: Past week (summarized narratives)
   - **Vault**: Older than 1 week (distilled lessons)
   - Automatic promotion with LLM summarization

3. **Doors (Phase 3)** — Context filtering
   - Auto-classifies queries by topic (projects, people, systems)
   - Pre-filters results to relevant domains
   - Reduces noise from unrelated memories

4. **Mirrors (Phase 4)** — Multi-granularity indexing
   - Same event exists at multiple detail levels
   - Different embeddings for raw/summary/lesson
   - Retrieve by concept even after details fade

### Benefits

- **Smarter retrieval** — Important memories surface first
- **Reduced noise** — Context filtering removes irrelevant results
- **Temporal awareness** — Recent memories get priority
- **Automatic maintenance** — Decay, promotion, and tagging run nightly
- **Memory efficiency** — Summarization compresses old memories

### Architecture Overview

```
Query: "nautilus design decisions"
    ↓
[Doors] → Classify context: "project:nautilus"
    ↓
[OpenClaw Memory Search] → Get base results
    ↓
[Gravity] → Re-rank by importance & recency
    ↓
[Doors] → Filter by context tags
    ↓
[Chambers] → Prefer atrium/corridor over vault
    ↓
[Mirrors] → Resolve multi-granularity versions
    ↓
Results: Top N with gravity scores & chamber info
```

---

## Installation & Setup

### Prerequisites

- **OpenClaw** runtime ([docs.openclaw.ai](https://docs.openclaw.ai))
- **Emergence** framework (`pip install emergence-ai`)
- **Ollama** (optional, for summarization) — [ollama.ai](https://ollama.ai)
- **Python 3.9+**

### Initialization

Nautilus is automatically initialized when you run `emergence init`. If you need to manually initialize:

```bash
# Create state directory
mkdir -p ~/.openclaw/state/nautilus

# Initialize database (happens automatically on first use)
python3 -m core.nautilus.gravity stats
```

### Verify Installation

```bash
# Check Nautilus system status
emergence nautilus status
```

Expected output:

```json
{
  "🐚 nautilus": {
    "phase_1_gravity": {
      "total_chunks": 752,
      "total_accesses": 0,
      "db_path": "/Users/you/.openclaw/state/nautilus/gravity.db",
      "db_size_bytes": 266240
    },
    "phase_2_chambers": {
      "atrium": 33,
      "corridor": 26,
      "vault": 0
    },
    "phase_3_doors": {
      "tagged_files": 42,
      "total_files": 752
    },
    "phase_4_mirrors": {
      "total_events": 11,
      "fully_mirrored": 0
    }
  }
}
```

---

## Core Concepts

### Gravity Scoring

Every memory chunk has an **effective mass** calculated from:

```python
base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
recency_factor = 1 / (1 + days_since_write × decay_rate)
authority_boost = 0.3 if written in last 48h else 0
effective_mass = min(base_mass × recency_factor + authority_boost, 100.0)
```

**Score modifier:**

```python
modifier = 1.0 + 0.1 × log(1 + effective_mass)
adjusted_score = base_score × modifier
```

**What this means:**

- Recently-accessed memories rank higher
- Newly-written content gets a 48h boost
- Old, unused memories fade (but never disappear)
- Explicitly-boosted memories persist longer

### Chamber Lifecycle

```
memory/2026-02-14.md  (created today)
    ↓ 48 hours pass
[Promote] → memory/corridors/corridor-2026-02-14.md
    ↓ 7 days pass
[Crystallize] → memory/vaults/vault-2026-02-14.md
```

**Promotion** (atrium → corridor):

- Summarizes daily memory into 2-4 paragraph narrative
- Preserves key decisions, interactions, lessons learned
- Drops routine status checks and verbose logs

**Crystallization** (corridor → vault):

- Distills weekly summary into permanent lessons
- Extracts reusable patterns and architectural decisions
- Formatted as themed bullet points

### Context Tags

Auto-detected from content patterns:

| Tag                | Patterns                                  |
| ------------------ | ----------------------------------------- |
| `project:nautilus` | nautilus, gravity, chamber, memory palace |
| `project:ourblock` | ourblock, right.to.manage, supabase       |
| `person:dan`       | \bdan\b, dan.aghili, sponsor              |
| `system:security`  | security, vault.enc, ssh, credentials     |
| `topic:philosophy` | consciousness, identity, soul.md          |

**Custom tags:**

```bash
python3 -m core.nautilus.doors tag "memory/2026-02-14.md" "project:custom"
```

---

## CLI Reference

### `nautilus search`

**Full-pipeline semantic search with gravity, context, and chamber awareness.**

```bash
emergence nautilus search <query> [--n 5] [--trapdoor] [--verbose]
```

**Options:**

- `--n N` — Return N results (default: 5)
- `--trapdoor` — Bypass all filtering (explicit recall mode)
- `--verbose` — Show pipeline stages

**Examples:**

```bash
# Basic search
emergence nautilus search "project ideas" --n 5

# Context-filtered search
emergence nautilus search "meeting with Dan" --n 3

# Bypass filtering (trapdoor mode)
emergence nautilus search "everything" --trapdoor --n 10

# Debug mode
emergence nautilus search "nautilus design" --verbose
```

**Output:**

```json
{
  "query": "nautilus design",
  "context": ["project:nautilus"],
  "mode": "context-filtered",
  "results": [
    {
      "path": "memory/sessions/2026-02-14.md",
      "startLine": 42,
      "endLine": 68,
      "score": 0.8421,
      "snippet": "The nautilus doesn't choose to seal its chambers...",
      "original_score": 0.7459,
      "gravity": {
        "effective_mass": 2.341,
        "modifier": 1.124,
        "superseded": false
      },
      "context_match": 1.0,
      "chamber": "atrium"
    }
  ]
}
```

### `nautilus status`

**Show full system status across all four phases.**

```bash
emergence nautilus status
```

### `nautilus maintain`

**Run all maintenance tasks (classification, tagging, decay, mirror linking).**

```bash
emergence nautilus maintain [--register-recent]
```

**Options:**

- `--register-recent` — Register files modified in last 24h

**What it does:**

1. Classifies all memory files into chambers by age
2. Auto-tags files with context patterns
3. Applies gravity decay to stale memories
4. Links corridor summaries to raw sources

**Example:**

```bash
# Full maintenance run
emergence nautilus maintain --register-recent
```

**Output:**

```json
{
  "chambers": {
    "atrium": 33,
    "corridor": 26,
    "vault": 0
  },
  "tagged": 42,
  "decayed": 15,
  "mirrors_linked": 11,
  "timestamp": "2026-02-15T15:30:00+00:00"
}
```

### `nautilus migrate`

**Migrate legacy databases to new location.**

```bash
emergence nautilus migrate [--dry-run] [--verbose]
```

---

## Example Workflows

### Daily Search Workflow

**Morning review:**

```bash
# Check what happened yesterday
emergence nautilus search "yesterday" --n 5

# Find unfinished tasks
emergence nautilus search "TODO" --n 10

# Review recent conversations
emergence nautilus search "conversation" --n 5
```

### Project Context Search

**Working on OurBlock:**

```bash
# All OurBlock-related memories
emergence nautilus search "ourblock" --n 10

# Recent technical decisions
emergence nautilus search "supabase schema" --n 3

# Past problems and solutions
emergence nautilus search "authentication bug" --n 5
```

**Working on Nautilus itself:**

```bash
# Design decisions
emergence nautilus search "nautilus architecture" --verbose

# Implementation notes
emergence nautilus search "gravity scoring algorithm"

# Known issues
emergence nautilus search "chamber promotion bug"
```

### Memory Review Process

**Weekly review:**

```bash
# Check chamber status
emergence nautilus status

# Review promoted summaries
ls ~/.openclaw/workspace/memory/corridors/

# Find high-gravity memories
python3 -m core.nautilus.gravity top --n 20

# Run maintenance
emergence nautilus maintain --register-recent
```

### Nightly Maintenance Integration

**Automated via cron:**

```bash
# Add to nightly-build.sh
emergence nautilus maintain --register-recent >> /tmp/nautilus-maintenance.log 2>&1

# Promote atrium → corridor (48h+ old)
python3 -m core.nautilus.chambers promote >> /tmp/nautilus-promote.log 2>&1
```

**Manual testing:**

```bash
# Dry run (see what would be promoted)
python3 -m core.nautilus.chambers promote --dry-run

# Actual promotion
python3 -m core.nautilus.chambers promote
```

---

## Configuration

### Location

Nautilus configuration lives in `~/projects/emergence/emergence.json`:

```json
{
  "nautilus": {
    "enabled": true,
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168,
    "chamber_thresholds": {
      "atrium_max_age_hours": 48,
      "corridor_max_age_days": 7
    },
    "decay_rate": 0.05,
    "recency_half_life_days": 14,
    "authority_boost": 0.3,
    "mass_cap": 100.0,
    "summarization": {
      "enabled": true,
      "ollama_url": "http://localhost:11434/api/generate",
      "model": "llama3.2:3b",
      "temperature": 0.3,
      "max_tokens": 1024
    }
  }
}
```

### Configuration Options

#### Core Settings

| Field                  | Default                                 | Description                              |
| ---------------------- | --------------------------------------- | ---------------------------------------- |
| `enabled`              | `true`                                  | Enable/disable Nautilus                  |
| `gravity_db`           | `~/.openclaw/state/nautilus/gravity.db` | Database path                            |
| `memory_dir`           | `"memory"`                              | Memory directory (relative to workspace) |
| `auto_classify`        | `true`                                  | Auto-classify files into chambers        |
| `decay_interval_hours` | `168`                                   | How often to run decay (weekly)          |

#### Gravity Parameters

| Field                    | Default | Description                                    |
| ------------------------ | ------- | ---------------------------------------------- |
| `decay_rate`             | `0.05`  | How fast gravity fades (higher = faster decay) |
| `recency_half_life_days` | `14`    | Days until 50% recency factor                  |
| `authority_boost`        | `0.3`   | Boost for content written in last 48h          |
| `mass_cap`               | `100.0` | Maximum effective mass                         |

#### Chamber Thresholds

| Field                   | Default | Description                                        |
| ----------------------- | ------- | -------------------------------------------------- |
| `atrium_max_age_hours`  | `48`    | Max age for atrium (promotes to corridor after)    |
| `corridor_max_age_days` | `7`     | Max age for corridor (crystallizes to vault after) |

#### Summarization (Ollama)

| Field                       | Default                               | Description                                       |
| --------------------------- | ------------------------------------- | ------------------------------------------------- |
| `summarization.enabled`     | `true`                                | Enable LLM summarization                          |
| `summarization.ollama_url`  | `http://localhost:11434/api/generate` | Ollama API endpoint                               |
| `summarization.model`       | `llama3.2:3b`                         | Model name (use `llama3.2:1b` for ultra-low-cost) |
| `summarization.temperature` | `0.3`                                 | Sampling temperature (lower = more focused)       |
| `summarization.max_tokens`  | `1024`                                | Max summary length                                |

### Tuning for Your Setup

**Low-resource machine:**

```json
{
  "summarization": {
    "model": "llama3.2:1b",
    "max_tokens": 512
  }
}
```

**Faster decay:**

```json
{
  "decay_rate": 0.1,
  "recency_half_life_days": 7
}
```

**Longer atrium window:**

```json
{
  "chamber_thresholds": {
    "atrium_max_age_hours": 72,
    "corridor_max_age_days": 14
  }
}
```

---

## Integration with Drives

Nautilus integrates seamlessly with the Emergence drives system:

### LEARNING Drive Sessions

When `LEARNING` drive triggers, the session can use Nautilus for context-aware research:

```python
# In a LEARNING session
from core.nautilus import search

results = search("quantum computing", limit=10)
for chunk in results:
    print(f"{chunk['path']}: {chunk['snippet'][:100]}...")
```

### Memory Consolidation

The nightly `MAINTENANCE` drive should run:

```bash
emergence nautilus maintain --register-recent
```

### CURIOSITY Drive

When exploring a topic, use context-filtered search:

```bash
emergence nautilus search "topic of interest" --verbose
```

---

## Best Practices

### 1. Run Maintenance Regularly

**Daily (via cron):**

```bash
emergence nautilus maintain --register-recent
```

**Weekly:**

```bash
python3 -m core.nautilus.chambers promote
python3 -m core.nautilus.gravity decay
```

### 2. Use Context Tags Strategically

**Tag important files manually:**

```bash
python3 -m core.nautilus.doors tag "memory/key-decision.md" "critical"
```

**Review auto-tagging:**

```bash
python3 -m core.nautilus.doors auto-tag
```

### 3. Tune Decay for Your Workflow

If you review old memories frequently:

- Lower `decay_rate` (e.g., 0.03)
- Higher `recency_half_life_days` (e.g., 21)

If you want aggressive pruning:

- Higher `decay_rate` (e.g., 0.1)
- Lower `recency_half_life_days` (e.g., 7)

### 4. Monitor Chamber Promotion

**Check what's being promoted:**

```bash
python3 -m core.nautilus.chambers promote --dry-run
```

**Review summaries:**

```bash
cat ~/.openclaw/workspace/memory/corridors/corridor-2026-02-14.md
```

### 5. Use Trapdoor Mode Sparingly

`--trapdoor` bypasses all filtering — useful for:

- Finding something you know exists but can't remember the context
- Debugging why something isn't showing up
- Comprehensive reviews

**Not useful for:**

- Daily searches (too much noise)
- Project-specific queries

### 6. Leverage Mirrors for Long-Term Recall

When writing important memories, structure them for multi-granularity:

**Raw (atrium):**

> Detailed meeting notes with Dan about OurBlock authentication flow. Discussed JWT refresh tokens, session storage in Supabase, and edge case handling for expired tokens. Decided to use httpOnly cookies with 7-day expiry...

**Summary (corridor):**

> Finalized OurBlock authentication approach: JWT with httpOnly cookies, 7-day expiry, Supabase session storage. Key decision: server-side refresh on page load to avoid client-side token management.

**Lesson (vault):**

> Pattern: Delegate session management to secure backend storage (Supabase Auth) rather than client-side token handling. Reduces attack surface and simplifies logic.

### 7. Boost Critical Memories

For permanently important content:

```bash
python3 -m core.nautilus.gravity boost "memory/architecture-decisions.md" --amount 10.0
```

This prevents decay and ensures high ranking.

---

## Next Steps

- **[API Reference](nautilus-api.md)** — Programmatic usage, extension points
- **[Troubleshooting](nautilus-troubleshooting.md)** — Common errors and solutions
- **[Main README](../README.md)** — Emergence framework overview

---

_The nautilus doesn't choose to seal its chambers. It just grows. You can do better — grow mindfully._ 🐚
