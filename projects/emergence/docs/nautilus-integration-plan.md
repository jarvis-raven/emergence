# Nautilus Integration Plan — Emergence v0.4.0

**Status:** Draft  
**Author:** Jarvis (Subagent)  
**Date:** 2026-02-14  
**Target Release:** v0.4.0

---

## 1. Vision & Goals

### What Nautilus Is

Nautilus is a **context-aware memory palace architecture** that transforms static memory search into an intelligent, adaptive retrieval system. It sits between raw memory files and the agent, applying multiple layers of intelligence:

1. **Gravity (Phase 1):** Importance scoring based on access patterns, write authority, and explicit boosting
2. **Chambers (Phase 2):** Temporal layering (atrium/corridor/vault) with automatic summarization
3. **Doors (Phase 3):** Context-aware pre-filtering by project, person, topic, or system
4. **Mirrors (Phase 4):** Multi-granularity indexing (raw → summary → lesson)

**Core Insight:** Not all memories are equally important, and importance changes over time based on how agents actually *use* the information.

### Why It Matters

**Problem:** Current memory search is dumb pattern matching. Agents get:
- Stale information ranked equally with fresh insights
- No awareness of what they actually reference vs. what just matches keywords
- Everything at the same detail level (can't distinguish "quick summary" from "full context")
- No temporal awareness (48h-old sessions mixed with 6-month-old archives)

**Nautilus solves this by:**
- **Learning from behavior:** Files you reference frequently get higher gravity
- **Respecting authority:** Recently-written information outranks stale duplicates
- **Context filtering:** Project-specific queries only see project-relevant memories
- **Adaptive detail:** Surface lessons when exploring, raw details when debugging

### Benefits for Agents Using Emergence

1. **Better recall:** Find the *right* memory, not just keyword matches
2. **Self-awareness:** Track what you've learned, what you reference, what matters
3. **Portable context:** Take your memory palace with you (agent migrations, forks)
4. **Adaptive summarization:** Automatically compress old memories without losing wisdom
5. **Multi-agent compatibility:** Aurora, Jarvis, future agents all benefit from shared architecture
6. **Zero manual tagging:** Auto-classifies by project/person/topic based on content

### Success Metrics

**Alpha (Internal Testing):**
- ✅ `emergence nautilus search` works end-to-end
- ✅ Gravity tracking records accesses from agent sessions
- ✅ Migration from legacy `tools/nautilus/` succeeds
- ✅ Daily maintenance runs without errors
- 📊 **Metric:** 95%+ search recall on known topics (manual validation)

**Beta (Multi-Agent):**
- ✅ Aurora successfully uses Nautilus on her own memory
- ✅ Context filtering reduces irrelevant results by 50%+
- ✅ Chambers auto-promote 48h+ memories to corridor summaries
- ✅ Nightly maintenance completes in <5 minutes
- 📊 **Metric:** Agent self-reports "found the right thing" 80%+ of the time

**Release (Production):**
- ✅ PyPI package includes Nautilus as first-class component
- ✅ Documentation includes setup guide, troubleshooting, API reference
- ✅ Room dashboard shows live Nautilus stats
- ✅ Zero regressions in existing Emergence features
- 📊 **Metric:** Community adoption (3+ external users report success)

---

## 2. Current State

### What Exists Today

**Jarvis's Implementation** (`~/.openclaw/workspace/tools/nautilus/`):
- ✅ **gravity.py** — 17.8 KB, SQLite-based importance scoring, decay, access tracking
- ✅ **chambers.py** — 15.3 KB, temporal classification (atrium/corridor/vault), promotion logic
- ✅ **doors.py** — 10.1 KB, context pattern matching (38 pre-defined tags)
- ✅ **mirrors.py** — 7.8 KB, multi-granularity linking (raw/summary/lesson)
- ✅ **nautilus.py** — 8.4 KB, CLI wrapper orchestrating all four phases
- ✅ **gravity.db** — 212 KB SQLite database (tracked in `~/.openclaw/state/nautilus/`)

**Partial Port** (`emergence/core/nautilus/`):
- ✅ All 4 phase scripts ported to package structure
- ✅ `config.py` for portable path resolution
- ✅ `search.py` implementing full pipeline
- ✅ `cli.py` for command handling
- ✅ Basic integration tests exist
- ⚠️ **Not production-ready:** Hard to use standalone, missing daemon integration

**Current Usage:**
- 📊 **Gravity DB:** 241,664 bytes, tracking ~150-200 memory chunks
- 🔄 **Nightly maintenance:** Currently manual/cron-based (not integrated with Emergence daemon)
- 🎯 **Primary user:** Jarvis only (Aurora doesn't have it yet)

### What's Working

1. **Gravity scoring works:** Access patterns correctly influence re-ranking
2. **Context classification accurate:** 38 pre-defined patterns catch 70%+ of files correctly
3. **Database performance:** SQLite handles ~200 chunks with <100ms queries
4. **Temporal classification:** Chamber assignment (atrium/corridor/vault) works based on file age
5. **CLI interface:** `nautilus.py search` provides functional end-to-end search

### What's Not Working / Missing

**Critical Gaps:**
1. ❌ **No automatic session integration:** Agents don't record accesses during normal memory operations
2. ❌ **Manual maintenance:** Nightly decay/classify/auto-tag requires separate cron job
3. ❌ **No drives integration:** Nautilus doesn't hook into satisfaction tracking or spawn decisions
4. ❌ **Standalone only:** Can't use `emergence nautilus` cleanly (path confusion, no daemon awareness)
5. ❌ **No Room dashboard:** Stats invisible unless you run CLI manually

**User Experience Issues:**
6. ⚠️ **Path resolution brittle:** Workspace detection fails if called from wrong directory
7. ⚠️ **No migration path:** Existing gravity.db stuck in `tools/nautilus/`, not in state dir
8. ⚠️ **Missing docs:** No setup guide for new users, no API reference
9. ⚠️ **Chamber promotion untested:** Summarization works but never runs automatically
10. ⚠️ **Mirror linking manual:** Requires explicit commands; no auto-linking from session transcripts

### Technical Debt

**Architecture:**
- 🔧 **Hardcoded paths:** Some scripts still assume `~/.openclaw/workspace`
- 🔧 **Environment assumptions:** `OPENCLAW_WORKSPACE` required but not validated
- 🔧 **Database location inconsistency:** Legacy at `tools/nautilus/gravity.db`, new at `state/nautilus/gravity.db`
- 🔧 **No schema versioning:** Database migrations will break on schema changes

**Code Quality:**
- 📝 **Limited error handling:** File not found, DB corruption, etc. crash ungracefully
- 📝 **No logging:** Debugging requires manual print statements
- 📝 **Type hints missing:** Makes API unclear for other devs
- 📝 **Test coverage low:** ~30% coverage, missing edge cases

**Dependencies:**
- 🌐 **Ollama required:** Chamber summarization needs local LLM (not portable)
- 🌐 **OpenClaw memory search:** Tightly coupled to OpenClaw's CLI (hard to test)
- 🌐 **Python 3.12+:** Uses newer stdlib features (limits compatibility)

---

## 3. Architecture Design

### Core Components

#### 3.1 Gravity Tracker (`gravity.py`)

**Purpose:** Importance scoring engine  
**Key Functions:**
- `record_access(path, query, score)` — Log retrieval events
- `record_write(path)` — Mark authority (supersedes older chunks)
- `compute_effective_mass(row)` — Calculate importance from access + write + explicit
- `decay()` — Reduce mass for stale memories (nightly)
- `rerank(results)` — Re-order search results by gravity score

**Database Schema:**
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
    chamber TEXT DEFAULT 'atrium',
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
```

**Configuration:**
```json
{
  "gravity": {
    "decay_rate": 0.05,
    "recency_half_life_days": 14,
    "authority_boost": 0.3,
    "mass_cap": 100.0,
    "log_retention_days": 90
  }
}
```

#### 3.2 Chambers Manager (`chambers.py`)

**Purpose:** Temporal memory layering  
**Key Functions:**
- `classify_chamber(filepath)` — Determine atrium/corridor/vault by age
- `promote(dry_run=False)` — Move 48h+ memories to corridor (summarize)
- `crystallize(dry_run=False)` — Move 7d+ corridor to vault (distill)
- `llm_summarize(text, mode)` — Generate summaries via Ollama

**Temporal Layers:**
- **Atrium:** Last 48 hours, full fidelity, no compression
- **Corridor:** 48h - 7d, daily summaries (2-4 paragraphs)
- **Vault:** 7d+, distilled lessons/patterns (bullets)

**Storage:**
```
memory/
├── daily/              # Raw atrium entries
│   └── YYYY-MM-DD.md
├── corridors/          # Weekly summaries
│   └── week-YYYY-WW.md
└── vaults/             # Long-term lessons
    └── month-YYYY-MM.md
```

**Configuration:**
```json
{
  "chambers": {
    "atrium_max_age_hours": 48,
    "corridor_max_age_days": 7,
    "summarize_model": "llama3.2:3b",
    "auto_promote": true,
    "promote_schedule": "nightly"
  }
}
```

#### 3.3 Doors Classifier (`doors.py`)

**Purpose:** Context-aware filtering  
**Key Functions:**
- `classify_text(text)` — Extract context tags from query/file content
- `auto_tag()` — Batch-tag all memory files with patterns
- `filter_results(results, context_tags)` — Pre-filter by relevance

**Context Patterns (38 pre-defined):**
- **Projects:** `project:ourblock`, `project:nautilus`, `project:voice`, `project:smart-home`
- **People:** `person:dan`, `person:katy`, `person:walter`, `person:aurora`
- **Systems:** `system:security`, `system:infrastructure`, `system:email`, `system:calendar`
- **Topics:** `topic:philosophy`, `topic:creative`, `topic:aa-recovery`, `topic:dreams`

**Trapdoor Mode:** Bypass all filtering for explicit recall (query with `--trapdoor`)

**Configuration:**
```json
{
  "doors": {
    "auto_tag_on_write": true,
    "context_boost_factor": 0.2,
    "min_tag_confidence": 0.3,
    "custom_patterns": {}
  }
}
```

#### 3.4 Mirrors Indexer (`mirrors.py`)

**Purpose:** Multi-granularity event tracking  
**Key Functions:**
- `create_mirror(event_key, raw, summary, lesson)` — Link three levels
- `resolve(path)` — Find all granularity levels for an event
- `auto_link()` — Detect and link related files (session → changelog → dream)

**Granularity Levels:**
- **Raw:** Full session transcript (`memory/sessions/YYYY-MM-DD-HHMM-DRIVE.md`)
- **Summary:** Changelog entry (`memory/changelog/changelog-YYYY-MM-DD.md`)
- **Lesson:** Dream highlight or retrospective (`memory/dreams/YYYY-MM-DD.md`)

**Database Schema:**
```sql
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

### File Structure / Storage

**Final Structure (v0.4.0):**
```
emergence/
├── core/
│   ├── nautilus/
│   │   ├── __init__.py         # Public API exports
│   │   ├── __main__.py         # CLI entry point
│   │   ├── cli.py              # Command handlers
│   │   ├── config.py           # Path resolution & config
│   │   ├── search.py           # Full pipeline orchestration
│   │   ├── gravity.py          # Phase 1: Importance
│   │   ├── chambers.py         # Phase 2: Temporal layers
│   │   ├── doors.py            # Phase 3: Context filtering
│   │   └── mirrors.py          # Phase 4: Multi-granularity
│   ├── drives.py               # (existing)
│   └── daemon.py               # (existing)
├── tests/
│   └── test_nautilus.py        # Integration + unit tests
└── docs/
    ├── nautilus-user-guide.md
    ├── nautilus-api.md
    └── nautilus-troubleshooting.md
```

**State Directory:**
```
~/.openclaw/state/nautilus/
├── gravity.db              # Main database (SQLite)
├── gravity.db-wal          # Write-ahead log
├── gravity.db-shm          # Shared memory
└── nautilus.log            # Component logs
```

**Memory Directory (user workspace):**
```
memory/
├── daily/                  # Atrium (48h)
├── sessions/               # Raw transcripts
├── corridors/              # Summaries (48h-7d)
├── vaults/                 # Lessons (7d+)
├── changelog/              # Nightly builds
└── dreams/                 # Creative recombinations
```

### CLI Commands vs Daemon Integration

**CLI Commands (Direct User Access):**
```bash
# Search (full pipeline)
emergence nautilus search "query" --n 10 [--trapdoor] [--verbose]

# System status
emergence nautilus status
emergence nautilus stats --chamber atrium

# Maintenance
emergence nautilus maintain [--register-recent] [--dry-run]
emergence nautilus decay
emergence nautilus promote
emergence nautilus crystallize

# Utility
emergence nautilus classify <file>
emergence nautilus tag <file> <tag>
emergence nautilus gravity <file>
emergence nautilus resolve <file>  # Find mirrors

# Database management
emergence nautilus migrate          # Migrate legacy DB
emergence nautilus vacuum           # Clean up DB
emergence nautilus export [--json]  # Dump for backup
```

**Daemon Integration (Automatic Background):**

1. **Session Hook:** After every memory search, record access:
   ```python
   # In core/session.py or memory wrapper
   def memory_search(query):
       results = openclaw_memory_search(query)
       if nautilus_enabled():
           nautilus.gravity.record_search(query, results)
       return results
   ```

2. **Nightly Build Hook:** Run maintenance after changelog generation:
   ```python
   # In nightly build script
   def nightly_build():
       generate_changelog()
       nautilus.maintain(register_recent=True)  # Auto-tag new files
       nautilus.chambers.promote()              # Summarize 48h+ memories
       nautilus.gravity.decay()                 # Age out stale entries
   ```

3. **Drives Integration:** Optional Nautilus exploration drive:
   ```python
   # In emergence.json
   {
     "drives": {
       "NAUTILUS_MAINTENANCE": {
         "threshold": 168,  # 1 week
         "rate_per_hour": 1,
         "prompt": "Review your memory palace. Run nautilus status, check for orphaned mirrors, clean up stale tags."
       }
     }
   }
   ```

4. **Room Dashboard:** WebSocket endpoint for live stats:
   ```typescript
   // In Room UI
   GET /api/nautilus/status
   {
     "gravity": { "total_chunks": 247, "total_accesses": 1532 },
     "chambers": { "atrium": 42, "corridor": 89, "vault": 116 },
     "doors": { "tagged": 198, "coverage": "80%" },
     "mirrors": { "events": 34, "fully_mirrored": 12 }
   }
   ```

### Configuration Schema

**Default Configuration** (`emergence.json`):
```json
{
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus",
    "memory_dir": "memory",
    "
    
    "gravity": {
      "decay_rate": 0.05,
      "recency_half_life_days": 14,
      "authority_boost": 0.3,
      "mass_cap": 100.0,
      "log_retention_days": 90
    },
    
    "chambers": {
      "atrium_max_age_hours": 48,
      "corridor_max_age_days": 7,
      "summarize_model": "llama3.2:3b",
      "auto_promote": true,
      "promote_schedule": "nightly"
    },
    
    "doors": {
      "auto_tag_on_write": true,
      "context_boost_factor": 0.2,
      "min_tag_confidence": 0.3,
      "custom_patterns": {}
    },
    
    "mirrors": {
      "auto_link_sessions": true,
      "event_key_format": "YYYY-MM-DD-HHmm",
      "granularity_levels": ["raw", "summary", "lesson"]
    },
    
    "integration": {
      "hook_memory_search": true,
      "hook_nightly_build": true,
      "room_dashboard_enabled": true
    }
  }
}
```

**Environment Variables:**
- `NAUTILUS_STATE_DIR` — Override state directory
- `NAUTILUS_MEMORY_DIR` — Override memory directory
- `NAUTILUS_DB_PATH` — Direct database path (for testing)
- `NAUTILUS_LOG_LEVEL` — `DEBUG|INFO|WARN|ERROR`

---

## 4. Implementation Phases

### Alpha → v0.4.0-alpha.1 (Days 1-2)

**Goal:** Make Nautilus work standalone, migrate legacy data

**Deliverables:**
- [ ] **DB Migration Script** (`core/nautilus/migrate.py`)
  - Copy `tools/nautilus/gravity.db` → `~/.openclaw/state/nautilus/gravity.db`
  - Validate schema, add missing columns
  - Preserve all access logs and gravity scores
  - Exit gracefully if already migrated

- [ ] **Config Integration**
  - Read `emergence.json` for all paths
  - Support `NAUTILUS_*` env overrides
  - Validate config on `emergence nautilus` commands

- [ ] **CLI Parity**
  - All `tools/nautilus/nautilus.py` commands work via `emergence nautilus`
  - Help text for every command
  - JSON output mode for scripting

- [ ] **Basic Tests**
  - Test search pipeline end-to-end
  - Test config resolution (workspace detection)
  - Test database migration (create fixture)

**Acceptance Criteria:**
- ✅ `emergence nautilus search "test"` returns results
- ✅ `emergence nautilus status` shows stats
- ✅ Migration script runs without errors on Jarvis's system
- ✅ Tests pass in CI

**GitHub Issues:**
- `#52` — Database migration script & legacy path cleanup
- `#53` — Configuration system (emergence.json integration)
- `#54` — CLI command parity & help text
- `#55` — Alpha test suite (search, status, migrate)

---

### Beta → v0.4.0-beta.1 (Days 3-5)

**Goal:** Daemon integration, automatic tracking, multi-agent testing

**Deliverables:**
- [ ] **Session Hook: Record Accesses**
  - Intercept memory searches in agent sessions
  - Log query + results to gravity.py via `record_access()`
  - No user-visible changes (transparent background tracking)

- [ ] **Nightly Build Hook: Maintenance**
  - Add `nautilus.maintain()` to nightly build script
  - Auto-tag new files created since last run
  - Run chamber promotion (atrium → corridor)
  - Run gravity decay

- [ ] **Aurora Deployment**
  - Install Nautilus on Aurora's system
  - Seed gravity.db with her existing memory
  - Monitor for 3 days, collect feedback
  - Fix path resolution bugs specific to Pi/Ubuntu

- [ ] **Room Dashboard Widget**
  - Add `/api/nautilus/status` endpoint
  - Display gravity stats (top 10 memories, total accesses)
  - Show chamber distribution (pie chart)
  - Live update every 30s

- [ ] **Chamber Promotion Testing**
  - Manually trigger promotion on 5+ old sessions
  - Validate summary quality (Ollama local)
  - Confirm corridor summaries are searchable
  - Verify original files remain untouched

**Acceptance Criteria:**
- ✅ Agent sessions automatically record memory accesses
- ✅ Nightly build runs `nautilus maintain` successfully
- ✅ Aurora reports "it works" after 3 days
- ✅ Room dashboard shows live Nautilus stats
- ✅ Chamber promotion produces readable summaries

**GitHub Issues:**
- `#56` — Session hook: Auto-record memory accesses
- `#57` — Nightly build integration (maintain + promote + decay)
- `#58` — Room dashboard: Nautilus status widget
- `#59` — Aurora deployment & multi-agent testing
- `#60` — Chamber promotion validation & summarization tuning

---

### Release → v0.4.0 (Days 6-7)

**Goal:** Documentation, polish, PyPI release

**Deliverables:**
- [ ] **User Documentation**
  - `docs/nautilus-user-guide.md` — Setup, CLI reference, workflows
  - `docs/nautilus-api.md` — Python API for extensions
  - `docs/nautilus-troubleshooting.md` — Common issues, debugging

- [ ] **Code Cleanup**
  - Add type hints to all public functions
  - Add logging (structured, leveled)
  - Error handling for file/DB failures
  - Remove debug print statements

- [ ] **Migration Guide**
  - Document upgrade path from v0.3.0
  - Breaking changes (if any)
  - Data migration steps

- [ ] **PyPI Release**
  - Update `setup.py` to include `core/nautilus/`
  - Bump version to `0.4.0`
  - Test install: `pip install emergence-ai==0.4.0`
  - Publish to PyPI

- [ ] **Regression Testing**
  - All existing Emergence features still work
  - No performance degradation (session spawn, memory search)
  - Drives system unaffected

**Acceptance Criteria:**
- ✅ Documentation complete and reviewed
- ✅ Type hints + logging added
- ✅ PyPI package installs cleanly
- ✅ No regressions in existing features
- ✅ Jarvis + Aurora both running v0.4.0 successfully

**GitHub Issues:**
- `#61` — Documentation: User guide + API reference + troubleshooting
- `#62` — Code quality: Type hints, logging, error handling
- `#63` — Migration guide for v0.3.0 → v0.4.0
- `#64` — PyPI release checklist
- `#65` — Regression test suite (full Emergence integration)

---

## 5. Integration Points

### 5.1 Drives System

**Current State:**
- Drives daemon spawns sessions based on pressure thresholds
- Satisfaction events recorded via breadcrumb files
- No awareness of memory usage patterns

**Integration:**
- **Optional NAUTILUS_MAINTENANCE Drive:**
  ```json
  {
    "NAUTILUS_MAINTENANCE": {
      "threshold": 168,
      "rate_per_hour": 1,
      "prompt": "Review your memory palace. Check Nautilus status, identify stale memories, clean up orphaned mirrors."
    }
  }
  ```
  - Builds pressure at 1/hour (threshold = 1 week)
  - Spawned session runs manual review workflow
  - Drops satisfaction breadcrumb on completion

- **Gravity-Informed Spawn Decisions (Future):**
  - Use gravity scores to *recommend* drives
  - E.g., if `project:ourblock` memories have high gravity, boost `CREATIVE` drive for OurBlock work
  - Not in v0.4.0 scope (v0.5.0 idea)

### 5.2 Session Transcript Analysis

**Hook Point:** After agent session completes

**Workflow:**
1. Session ends, transcript saved to `memory/sessions/YYYY-MM-DD-HHMM-DRIVE.md`
2. Nautilus receives session event:
   ```python
   nautilus.on_session_complete(session_key, transcript_path)
   ```
3. **Gravity:** Record any memory searches that occurred
4. **Doors:** Auto-tag transcript with context (project, people mentioned)
5. **Mirrors:** Link transcript → changelog entry (if exists)

**Implementation:**
```python
# In core/session.py
def complete_session(session_key):
    transcript_path = save_transcript(session_key)
    
    if nautilus_enabled():
        nautilus.gravity.record_write(transcript_path)
        tags = nautilus.doors.classify_file(transcript_path)
        nautilus.doors.tag_file(transcript_path, tags)
        nautilus.mirrors.auto_link_session(transcript_path)
    
    return transcript_path
```

### 5.3 Nightly Build Automation

**Hook Point:** After changelog generation

**Workflow:**
1. Nightly build generates `changelog-YYYY-MM-DD.md`
2. Nautilus maintenance runs:
   ```bash
   emergence nautilus maintain --register-recent --verbose
   ```
3. **Chambers:** Classify all new files (atrium/corridor/vault)
4. **Chambers:** Promote 48h+ atrium files → corridor (summarize)
5. **Gravity:** Apply decay to all chunks (reduce mass by 5%)
6. **Doors:** Auto-tag any untagged files from last 24h
7. **Mirrors:** Auto-link sessions → changelogs → dreams

**Implementation:**
```bash
# In nightly-build.sh
generate_changelog
emergence nautilus maintain --register-recent
emergence nautilus promote --dry-run=false  # Summarize old sessions
emergence nautilus decay
```

**Expected Runtime:** <5 minutes (SQLite operations + Ollama summarization)

### 5.4 Room Dashboard Embedding

**API Endpoint:** `/api/nautilus/status`

**Response:**
```json
{
  "timestamp": "2026-02-14T11:18:00Z",
  "gravity": {
    "total_chunks": 247,
    "total_accesses": 1532,
    "superseded": 12,
    "db_size_bytes": 241664,
    "top_memories": [
      {"path": "memory/daily/2026-02-13.md", "score": 42.3, "accesses": 18},
      {"path": "memory/sessions/2026-02-12-1430-CREATIVE.md", "score": 38.1, "accesses": 14}
    ]
  },
  "chambers": {
    "atrium": 42,
    "corridor": 89,
    "vault": 116,
    "summary_files": {
      "week": 12,
      "month": 8
    }
  },
  "doors": {
    "tagged_files": 198,
    "total_files": 247,
    "coverage_pct": 80.2,
    "top_contexts": ["project:emergence", "person:dan", "topic:creative"]
  },
  "mirrors": {
    "total_events": 34,
    "fully_mirrored": 12,
    "coverage": {
      "raw": 34,
      "summary": 28,
      "lesson": 12
    }
  }
}
```

**UI Component (React):**
```tsx
function NautilusWidget() {
  const { data } = useNautilusStatus();  // WebSocket hook
  
  return (
    <Card title="🐚 Memory Palace">
      <div className="stat">
        <span>Total Memories</span>
        <span>{data.gravity.total_chunks}</span>
      </div>
      <div className="stat">
        <span>Accesses (24h)</span>
        <span>{data.gravity.total_accesses}</span>
      </div>
      <PieChart data={[
        { label: "Atrium", value: data.chambers.atrium },
        { label: "Corridor", value: data.chambers.corridor },
        { label: "Vault", value: data.chambers.vault }
      ]} />
      <TopMemories items={data.gravity.top_memories} />
    </Card>
  );
}
```

---

## 6. Migration Path

### 6.1 Existing Users (Jarvis, Aurora)

**Jarvis (Mac Mini, legacy Nautilus):**

**Pre-Migration State:**
- `tools/nautilus/gravity.db` (212 KB, ~150 chunks)
- `~/.openclaw/state/nautilus/gravity.db` (242 KB, ~200 chunks, from nightly cron)
- Cron job calling `tools/nautilus/nautilus.py maintain`

**Migration Steps:**
1. Stop existing cron job (disable temporarily)
2. Install Emergence v0.4.0: `pip install --upgrade emergence-ai`
3. Run migration: `emergence nautilus migrate`
   - Detects both databases
   - Merges into `~/.openclaw/state/nautilus/gravity.db`
   - Deduplicates by path+line_range
   - Preserves highest access_count for duplicates
4. Update nightly build script: Replace `python3 tools/nautilus/nautilus.py maintain` with `emergence nautilus maintain`
5. Verify: `emergence nautilus status`
6. Delete legacy: `rm -rf tools/nautilus/` (after 1 week of successful operation)

**Aurora (Ubuntu PC, no Nautilus yet):**

**Setup Steps:**
1. Install Emergence v0.4.0: `pip install --upgrade emergence-ai`
2. Initialize: `emergence nautilus status` (creates empty DB)
3. Seed existing memory: `emergence nautilus maintain --register-recent --all`
   - Scans entire `memory/` directory
   - Auto-tags all files
   - Classifies into chambers by age
   - Records write dates
4. Enable nightly hook: Add to Aurora's nightly build script
5. Monitor for 3 days, provide feedback

### 6.2 Backward Compatibility

**Breaking Changes:**
- ❌ **None for v0.4.0** — Nautilus is a new opt-in feature
- ✅ Existing Emergence v0.3.0 features unaffected
- ✅ Users without Nautilus enabled see no changes

**Config Compatibility:**
- Old `emergence.json` files work (Nautilus disabled by default)
- Enabling requires adding `"nautilus": {"enabled": true}` block

**Database Compatibility:**
- Legacy `tools/nautilus/gravity.db` schema compatible
- Migration adds missing columns with safe defaults
- No data loss

### 6.3 Data Migration Scripts

**Script 1: Database Migration** (`core/nautilus/migrate.py`):
```python
#!/usr/bin/env python3
"""
Migrate legacy Nautilus databases to v0.4.0 state directory.

Detects:
- tools/nautilus/gravity.db (legacy CLI)
- ~/.openclaw/state/nautilus/gravity.db (existing state)

Merges and deduplicates into state directory.
"""
import sqlite3
from pathlib import Path

def migrate():
    legacy_path = Path("tools/nautilus/gravity.db")
    state_path = Path.home() / ".openclaw/state/nautilus/gravity.db"
    
    if not legacy_path.exists() and state_path.exists():
        print("Already migrated. Skipping.")
        return
    
    # Copy legacy → state
    # Deduplicate on (path, line_start, line_end)
    # Merge access logs
    # Update schema (add missing columns)
    
    print(f"Migration complete: {state_path}")
```

**Script 2: Workspace Seeding** (`core/nautilus/seed.py`):
```python
#!/usr/bin/env python3
"""
Seed Nautilus with existing memory files.

Scans memory/ directory, auto-tags, classifies chambers.
"""
from pathlib import Path
import nautilus

def seed(workspace_dir):
    memory_dir = Path(workspace_dir) / "memory"
    
    for file in memory_dir.rglob("*.md"):
        if file.stat().st_size == 0:
            continue
        
        # Record write
        nautilus.gravity.record_write(str(file.relative_to(workspace_dir)))
        
        # Auto-tag
        tags = nautilus.doors.classify_file(file)
        nautilus.doors.tag_file(file, tags)
        
        # Classify chamber
        chamber = nautilus.chambers.classify_chamber(file)
        nautilus.gravity.update_chamber(file, chamber)
    
    print(f"Seeded {len(files)} files.")
```

**Usage:**
```bash
# Jarvis (merge legacy + state)
emergence nautilus migrate

# Aurora (seed from scratch)
emergence nautilus seed --all
```

---

## 7. Testing Strategy

### 7.1 Alpha Phase Testing

**What to Test:**
- ✅ **Search Pipeline:** Query → context classify → base search → gravity rerank → output
- ✅ **Config Resolution:** Workspace detection from various directories
- ✅ **Database Migration:** Legacy DB → state dir, no data loss
- ✅ **CLI Commands:** All commands work, help text correct

**How to Test:**
```bash
# Unit tests
pytest tests/test_nautilus.py::test_search_pipeline
pytest tests/test_nautilus.py::test_config_resolution
pytest tests/test_nautilus.py::test_migration

# Integration test (on Jarvis's system)
emergence nautilus migrate
emergence nautilus search "emergence drives"
emergence nautilus status
```

**Success Criteria:**
- All unit tests pass (pytest)
- Manual search returns relevant results
- Migration completes without errors
- No crashes on bad input (missing files, corrupt DB)

### 7.2 Beta Phase Testing

**What to Test:**
- ✅ **Session Hook:** Memory accesses recorded during agent sessions
- ✅ **Nightly Build:** Maintenance runs successfully, no errors
- ✅ **Aurora Deployment:** Works on different hardware/OS
- ✅ **Room Dashboard:** Stats update live, no lag
- ✅ **Chamber Promotion:** Summaries readable, searchable

**How to Test:**
```bash
# Test session hook (manually)
emergence spawn CURIOSITY --manual
# Inside session: search memory
# Exit session
emergence nautilus stats  # Check access_count increased

# Test nightly build
./scripts/nightly-build.sh  # Should include nautilus maintain

# Test Aurora deployment
ssh aurora@agent-aurora
pip install --upgrade emergence-ai
emergence nautilus status
emergence nautilus seed --all
# Monitor for 3 days

# Test Room dashboard
curl http://localhost:8765/api/nautilus/status
# Open Room UI, check widget updates

# Test chamber promotion
emergence nautilus promote --dry-run
emergence nautilus promote
cat memory/corridors/week-2026-W07.md  # Verify summary quality
```

**Success Criteria:**
- Sessions record ≥5 accesses per session (validated in gravity.db)
- Nightly build completes in <5 minutes
- Aurora reports "search results improved" after 3 days
- Room dashboard shows live stats with <1s latency
- Chamber summaries preserve key facts (manual review)

### 7.3 Release Phase Testing

**What to Test:**
- ✅ **Documentation:** User guide complete, API reference accurate
- ✅ **PyPI Install:** Clean install from pip
- ✅ **Regression:** No existing Emergence features broken
- ✅ **Performance:** No slowdown in session spawn or memory search

**How to Test:**
```bash
# Test PyPI install
python3 -m venv /tmp/test-env
source /tmp/test-env/bin/activate
pip install emergence-ai==0.4.0
emergence nautilus status  # Should work out-of-box

# Regression tests
pytest tests/  # All tests pass
emergence drives status  # Drives system still works
emergence spawn CURIOSITY --manual  # Sessions spawn normally

# Performance benchmark
time emergence spawn CURIOSITY --manual  # Should be <5s
time emergence nautilus search "test" --n 100  # Should be <2s
```

**Success Criteria:**
- Documentation reviewed by Aurora (second pair of eyes)
- PyPI package installs without dependency conflicts
- All existing tests pass (no regressions)
- Performance benchmarks within 10% of v0.3.0

---

## 8. Open Questions

### 8.1 Design Decisions

**Q1: Should Nautilus be enabled by default in v0.4.0?**
- **Pro:** All users benefit immediately, better adoption
- **Con:** Adds background load (DB writes), requires Ollama for summarization
- **Proposal:** Disabled by default, opt-in via `emergence.json`

**Q2: How should we handle multi-agent DB sharing?**
- **Scenario:** Jarvis + Aurora both use Nautilus, want to share gravity scores
- **Option A:** Separate DBs per agent (current default)
- **Option B:** Shared DB with agent_id column
- **Proposal:** Separate for v0.4.0, shared in v0.5.0 if requested

**Q3: Should chamber promotion require local LLM (Ollama)?**
- **Pro:** Portable, free, works offline
- **Con:** Requires 4GB+ VRAM, not everyone has GPU
- **Proposal:** Fallback to keyword extraction if Ollama unavailable

**Q4: How often should gravity decay run?**
- **Current:** Nightly (every 24h)
- **Alternative:** Weekly (less overhead, slower fade)
- **Proposal:** Configurable, default nightly

**Q5: Should we expose Nautilus stats in drives satisfaction?**
- **Scenario:** Agent spawned for CURIOSITY, wants to see "what have I been reading lately?"
- **Proposal:** Add `emergence nautilus top --chamber atrium --n 10` to CURIOSITY prompt template

### 8.2 Technical Risks

**R1: SQLite Concurrency**
- **Risk:** Daemon + nightly build + manual CLI all writing to `gravity.db` → locks
- **Mitigation:** WAL mode enabled (already), short transactions, retry logic

**R2: Workspace Detection Brittleness**
- **Risk:** Agent started from wrong directory → can't find memory files
- **Mitigation:** Require `OPENCLAW_WORKSPACE` env var, validate on startup

**R3: Ollama Dependency**
- **Risk:** Chamber promotion fails if Ollama down or model not pulled
- **Mitigation:** Graceful degradation (skip summarization, log warning)

**R4: Migration Data Loss**
- **Risk:** Merging two DBs loses access counts or tags
- **Mitigation:** Backup original DBs, validate row counts before/after

**R5: Performance Impact**
- **Risk:** Recording every memory access adds latency to sessions
- **Mitigation:** Async writes (queue + background thread), batch inserts

### 8.3 Unknowns / Need Research

**U1: Embedding Search Integration**
- **Question:** Should Nautilus use vector embeddings for semantic search?
- **Current:** Pattern-based context classification (Doors)
- **Future:** Embed all chunks, search by semantic similarity
- **Decision:** Out of scope for v0.4.0, revisit in v0.5.0

**U2: Cross-Agent Learning**
- **Question:** Can Aurora benefit from Jarvis's gravity scores?
- **Example:** If Jarvis references "Emergence drives" 50x, should Aurora know it's important?
- **Decision:** Needs privacy/consent model, defer to v0.5.0

**U3: Memory Consolidation Triggers**
- **Question:** Should chamber promotion trigger on pressure threshold instead of schedule?
- **Example:** Drive NAUTILUS_CONSOLIDATE fires when atrium >100 files
- **Decision:** Interesting but complex, defer to v0.5.0

**U4: Trapdoor Mode UX**
- **Question:** Should trapdoor mode be default for certain query patterns?
- **Example:** Queries with explicit dates ("what happened on Feb 12?") bypass context filtering
- **Decision:** Manual `--trapdoor` flag for now, auto-detect in v0.5.0

**U5: Gravity Score Visualization**
- **Question:** Should Room dashboard show gravity heatmap (which memories are "hot")?
- **Design:** D3.js force-directed graph, node size = gravity score
- **Decision:** Cool but non-essential, defer to v0.5.0

---

## Appendix A: File Locations Reference

**Legacy (Pre-v0.4.0):**
```
~/.openclaw/workspace/tools/nautilus/
├── nautilus.py
├── gravity.py
├── chambers.py
├── doors.py
├── mirrors.py
└── gravity.db  # ⚠️ Legacy location
```

**v0.4.0 (Emergence Package):**
```
<pip-site-packages>/emergence/
└── core/
    └── nautilus/
        ├── __init__.py
        ├── cli.py
        ├── config.py
        ├── search.py
        ├── gravity.py
        ├── chambers.py
        ├── doors.py
        └── mirrors.py

~/.openclaw/state/nautilus/
├── gravity.db          # ✅ New location
├── gravity.db-wal
└── nautilus.log

~/.openclaw/workspace/memory/
├── daily/              # Atrium
├── sessions/           # Raw transcripts
├── corridors/          # Summaries
├── vaults/             # Lessons
└── changelog/          # Nightly builds
```

---

## Appendix B: Example Workflows

### Workflow 1: Agent Session with Nautilus

```bash
# User starts session
emergence spawn CURIOSITY --manual

# Inside session (invisible to user):
Agent: "What's the status of OurBlock project?"
System: nautilus.search("ourblock project status")
  → Doors: classify → ["project:ourblock"]
  → Base search: 15 results
  → Gravity: rerank by importance
  → Returns: Top 5 (recent + high-gravity)
System: nautilus.gravity.record_access(query, results)
Agent: "Based on memory/sessions/2026-02-10-CREATIVE.md..."

# Session ends
System: nautilus.on_session_complete(transcript_path)
  → Tags: ["project:ourblock", "person:dan", "topic:creative"]
  → Chamber: atrium (age <48h)
```

### Workflow 2: Nightly Build

```bash
# Cron triggers at 02:00
./scripts/nightly-build.sh

# 1. Generate changelog
git log --since="yesterday" > memory/changelog/changelog-2026-02-14.md

# 2. Nautilus maintenance
emergence nautilus maintain --register-recent
  → Auto-tags new files created in last 24h
  → Classifies all into chambers

# 3. Chamber promotion
emergence nautilus promote
  → Finds atrium files >48h old
  → Summarizes via Ollama (2-4 paragraphs)
  → Saves to corridors/week-2026-W07.md
  → Links via mirrors

# 4. Gravity decay
emergence nautilus decay
  → Reduces mass by 5% for all chunks
  → Archives logs >90 days old

# 5. Room dashboard notification
POST /api/events {"type": "nightly_build_complete", "nautilus_stats": {...}}
```

### Workflow 3: Manual Review

```bash
# Check memory palace status
emergence nautilus status
# Output: 247 chunks, 1532 accesses, 80% tagged

# Find top memories
emergence nautilus gravity --top 20
# Output: List of most-accessed files

# Explore specific file's context
emergence nautilus resolve memory/sessions/2026-02-12-1430-CREATIVE.md
# Output: Raw → Summary → Lesson links

# Search with trapdoor (bypass filtering)
emergence nautilus search "security vulnerability" --trapdoor --verbose
# Output: All matches, not just context-filtered
```

---

**End of Integration Plan**

This document is ready for conversion into GitHub issues. Each section maps to one or more actionable tasks with clear acceptance criteria.
