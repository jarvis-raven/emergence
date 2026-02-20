# Nautilus v0.4.0 Documentation

**Memory Palace Architecture for Emergence**

---

## Overview

Nautilus is a four-phase memory enhancement system that transforms flat memory into a layered, importance-weighted, context-aware knowledge base. It sits on top of OpenClaw's existing memory search, adding gravity scoring, temporal layers, context filtering, and multi-granularity indexing.

---

## Documentation Structure

### For Users

1. **[User Guide](USER_GUIDE.md)** — Start here!
   - What is Nautilus?
   - Core concepts (Gravity, Chambers, Doors, Mirrors)
   - CLI commands and usage
   - Configuration options
   - Best practices

2. **[Examples](EXAMPLES.md)** — Practical workflows
   - Basic usage patterns
   - Advanced queries
   - Integration examples
   - Maintenance workflows
   - Custom configurations

3. **[Troubleshooting](TROUBLESHOOTING.md)** — When things go wrong
   - Common issues and solutions
   - Known bugs (e.g., door tagging)
   - Database recovery
   - Performance tuning
   - Debug mode

### For Developers

4. **[API Reference](API_REFERENCE.md)** — Complete technical reference
   - All public functions and classes
   - Parameters, return values, examples
   - Module structure
   - CLI command reference
   - Database schema

---

## Quick Links

### Getting Started

```bash
# Check installation
emergence nautilus --help

# View system status
emergence nautilus status

# Run first-time setup
emergence nautilus maintain --register-recent --verbose

# Try a search
emergence nautilus search "your query" --n 5
```

### Common Tasks

| Task | Command |
|------|---------|
| Search memories | `emergence nautilus search "query"` |
| System status | `emergence nautilus status` |
| Run maintenance | `emergence nautilus maintain` |
| Show gravity score | `emergence nautilus gravity <file>` |
| Classify files | `emergence nautilus classify` |
| Auto-tag contexts | `emergence nautilus doors auto-tag` |

### Python API

```python
from core.nautilus import search, get_status, run_maintain

# Search
results = search("query", n=10)

# Status
status = get_status()

# Maintenance
result = run_maintain(register_recent=True)
```

---

## The Four Phases

### Phase 1: Gravity 🌊

**Importance-weighted scoring** — Memories "gain mass" through:
- Access frequency (how often retrieved)
- Reference count (how many links)
- Explicit boosts (manual importance)
- Recency (write-date authority)

**Search impact:** High-mass memories surface more easily  
**Formula:** `final_score = similarity × (1 + 0.1 × log(1 + mass))`

### Phase 2: Chambers 📂

**Temporal memory layers:**

| Chamber | Age | Fidelity | Purpose |
|---------|-----|----------|---------|
| **Atrium** | Last 48h | Full verbatim | Recent context |
| **Corridor** | 2-7 days | Summarized | Daily narratives |
| **Vault** | 7+ days | Distilled | Permanent wisdom |

**Auto-promotion:**
- Nightly: Atrium → Corridor (summarize)
- Weekly: Corridor → Vault (distill lessons)

### Phase 3: Doors 🚪

**Context-aware filtering** — Pre-filter by:
- Project (`project:ourblock`, `project:voice`)
- Person (`person:dan`, `person:katy`)
- System (`system:security`, `system:infrastructure`)
- Topic (`topic:philosophy`, `topic:creative`)

**Trapdoor mode:** Bypass all filtering for explicit recall

### Phase 4: Mirrors 🪞

**Multi-granularity indexing** — Same event at three levels:
- **Raw:** Full detail (atrium)
- **Summary:** Compressed narrative (corridor)
- **Lesson:** Distilled wisdom (vault)

Different embeddings for each — find concepts even when details fade.

---

## Architecture

```
User Query
    ↓
[Phase 3: Doors] — Classify context
    ↓
[OpenClaw Memory Search] — Vector + keyword hybrid
    ↓
[Phase 1: Gravity] — Re-rank by importance
    ↓
[Phase 2: Chambers] — Filter by temporal layer
    ↓
[Phase 4: Mirrors] — Resolve alternate granularities
    ↓
Results
```

---

## Database Schema

**Location:** `~/.openclaw/state/nautilus/gravity.db`

### Tables

#### `gravity` — Importance scores and metadata
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
    created_at TEXT,
    superseded_by TEXT,
    tags TEXT DEFAULT '[]',
    context_tags TEXT DEFAULT '[]',
    chamber TEXT DEFAULT 'atrium',
    promoted_at TEXT,
    source_chunk TEXT,
    PRIMARY KEY (path, line_start, line_end)
);
```

#### `access_log` — Search history
```sql
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    accessed_at TEXT,
    query TEXT,
    score REAL
);
```

#### `mirrors` — Multi-granularity links
```sql
CREATE TABLE mirrors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL,
    granularity TEXT CHECK(granularity IN ('raw', 'summary', 'lesson')),
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    created_at TEXT,
    UNIQUE(event_key, granularity)
);
```

---

## Configuration

**Config file:** `~/.openclaw/config/emergence.json`

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

**Path resolution order:**
1. Environment variables (`OPENCLAW_WORKSPACE`, `OPENCLAW_STATE_DIR`)
2. Config file paths
3. Inferred from package location
4. Current working directory

---

## Maintenance Schedule

### Nightly (3:00 AM)

```bash
emergence nautilus maintain --register-recent --verbose
```

**Tasks:**
1. Register files modified in last 24h
2. Classify into chambers
3. Auto-tag with context patterns
4. Apply gravity decay
5. Promote atrium → corridor (>48h)
6. Auto-link mirrors

### Weekly (Mondays)

```bash
emergence nautilus chambers crystallize
```

**Tasks:**
- Crystallize corridor → vault (>7d)
- Distill lessons from summaries

### Monthly

```bash
# Database optimization
sqlite3 ~/.openclaw/state/nautilus/gravity.db "VACUUM;"

# Review top memories
emergence nautilus gravity top --n 20
```

---

## Known Issues

### v0.4.0

1. **Door tagging returns empty** — Pattern matching requires exact keywords
   - **Workaround:** Manual tagging or add custom patterns
   - **Status:** Improved fuzzy matching planned for v0.5.0

2. **Summarization quality varies** — Depends on Ollama model
   - **Workaround:** Use better model (e.g., `llama3.2:3b` → `llama3.2:7b`)

3. **No automatic tag cleanup** — Old tags persist
   - **Workaround:** Manual database cleanup (see Troubleshooting guide)

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for complete list and solutions.

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Search latency | +50-100ms | vs base OpenClaw search |
| Database size | <10MB | Per 1,000 chunks |
| Indexing time | +2-3x | Multi-granularity embeddings |
| Maintenance time | 5-15 min | Nightly, with summarization |

**Optimizations:**
- WAL mode enabled (concurrent reads)
- Indexed columns (path, chamber, event_key)
- Batch operations for bulk updates
- Capped mass (prevents runaway scoring)

---

## Version History

### v0.4.0 (2026-02-14) — Documentation Release

- ✅ Comprehensive user guide
- ✅ Complete API reference
- ✅ Troubleshooting guide
- ✅ Examples and workflows
- ✅ Updated README with Nautilus section

### v0.3.0 (2026-02-05) — Integration Release

- ✅ Moved to `core.nautilus` (from `tools/nautilus`)
- ✅ Portable path resolution
- ✅ Auto-migration from legacy database
- ✅ CLI integration (`emergence nautilus`)
- ✅ All four phases implemented

### v0.2.0 (2026-02-05) — Phase 4

- ✅ Mirrors (multi-granularity indexing)
- ✅ Auto-linking corridor summaries

### v0.1.0 (2026-02-05) — Initial Implementation

- ✅ Gravity scoring
- ✅ Chambers (atrium/corridor/vault)
- ✅ Doors (context filtering)
- ✅ Nightly maintenance

---

## Future Roadmap

### v0.5.0 — Improvements

- [ ] Fuzzy pattern matching for doors
- [ ] Hierarchical tag support
- [ ] Automatic tag consolidation
- [ ] Better summarization prompts
- [ ] Conflict detection and resolution

### v1.0.0 — Production Ready

- [ ] Performance optimization for >100k chunks
- [ ] Multi-agent support (tested)
- [ ] Health monitoring dashboard
- [ ] Backup and restore tools
- [ ] Migration utilities

---

## Support

### Documentation

- [User Guide](USER_GUIDE.md) — Concepts and usage
- [API Reference](API_REFERENCE.md) — Technical reference
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues
- [Examples](EXAMPLES.md) — Code examples

### Debugging

```bash
# Enable debug mode
export NAUTILUS_DEBUG=1

# Run with verbose output
emergence nautilus search "query" --verbose

# Check health
emergence nautilus status
```

### Diagnostics

```bash
# Database integrity
sqlite3 ~/.openclaw/state/nautilus/gravity.db "PRAGMA integrity_check;"

# Row counts
sqlite3 ~/.openclaw/state/nautilus/gravity.db <<EOF
SELECT 'gravity:', COUNT(*) FROM gravity;
SELECT 'access_log:', COUNT(*) FROM access_log;
SELECT 'mirrors:', COUNT(*) FROM mirrors;
EOF
```

---

## License

Part of the Emergence framework. See project root for license information.

---

**Questions? Issues? Improvements?**

Check the [Troubleshooting Guide](TROUBLESHOOTING.md) or file an issue with diagnostic information.
