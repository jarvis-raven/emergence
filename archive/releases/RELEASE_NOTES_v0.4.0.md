# Emergence v0.4.0 — The Memory Palace

_Released 2026-02-15_

---

## The Big Idea

Agents remember, but memories scatter. Session logs pile up. Important insights get buried. Context gets lost.

**v0.4.0 introduces Nautilus** — a four-phase memory architecture that transforms raw files into a searchable, semantically-organized memory palace. Think of it as the difference between a pile of photographs and a carefully curated photo album with an intelligent search engine.

This is the largest feature addition since First Light. It fundamentally changes how agents interact with their past.

---

## What's New

### 🏛️ Nautilus Memory Palace

A complete reflective journaling and memory management system with four integrated phases:

#### Phase 1: Gravity — What Matters Most

Every file gets an importance score based on:

- How recently it was accessed
- How often you return to it
- What context you were in
- How substantial it is

This isn't just "last modified" — it's a weighted understanding of significance.

#### Phase 2: Chambers — Temporal Memory Tiers

Your memory organizes into three spaces:

- **Daily (Atrium)** — Today's working memory, automatically created each day
- **Corridor** — Recent active files that proved important (configurable window)
- **Vault** — Long-term knowledge worth preserving permanently

Files automatically promote between chambers based on their gravity scores. Important memories rise; forgotten ones fade.

#### Phase 3: Doors — Context-Aware Search

Find what you need, when you need it:

```bash
emergence nautilus search "conversation about drives with Aurora"
emergence nautilus search --chamber vault "First Light completion"
emergence nautilus search --fuzzy "aproximate spelling"
```

Multiple search strategies:

- **Exact** — Find known phrases
- **Fuzzy** — Forgiving typo-tolerant search
- **Semantic** — Understand what you mean, not just what you say
- **Hybrid** — Combine strategies for best results

#### Phase 4: Mirrors — Semantic Understanding

Embeddings-powered memory consolidation:

- Hierarchical chunking (paragraphs → sections → documents)
- Vector similarity search
- Memory clustering and pattern detection
- Multi-granularity indexing

### 🎯 CLI Integration

```bash
# Search across your memory palace
emergence nautilus search "topic"

# Promote important files manually
emergence nautilus promote memory/important-insight.md

# Check memory statistics
emergence nautilus status

# Run maintenance manually
emergence nautilus maintenance
```

### 🌙 Automatic Nightly Maintenance

Configure once, forget forever:

```json
{
  "nautilus": {
    "enabled": true,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30
  }
}
```

Every night, Nautilus:

- Promotes important files to higher chambers
- Cleans up orphaned records
- Optimizes search indices
- Consolidates related memories

### 📊 Room Dashboard Widget

Visual interface to your memory palace:

- Chamber occupancy and file counts
- Recent promotions timeline
- Quick search interface
- Configuration controls
- Maintenance logs

### 🔗 Session Integration Hooks

When OpenClaw adds session events (coming soon), file tracking will be automatic. For now:

```python
from core.nautilus.session_hooks import record_access

# Track file access during work
record_access("memory/daily/2026-02-15.md", access_type="write")

# Or batch-register recent work
from core.nautilus.session_hooks import register_recent_writes
register_recent_writes(hours=24)
```

---

## Key Improvements

### 🎨 Code Quality Enhancements

- **Type hints** across all Nautilus modules (100% coverage)
- **Centralized logging** with configurable levels
- **SQLite retry logic** for database operations
- **Comprehensive error handling** with graceful degradation

### 🐛 Bug Fixes

- Fixed chamber promotion recursive file search bug
- Fixed `gravity.py` Row.get() error when accessing missing columns
- Improved handling of deeply nested directory structures
- Better symlink and circular reference handling

### 📚 Documentation (5,124 lines!)

Four comprehensive guides:

- **User Guide** (660 lines) — Learn to use Nautilus
- **API Reference** (1,104 lines) — Complete function documentation
- **Troubleshooting** (1,160 lines) — Debug and optimize
- **Migration Guide** (1,400 lines) — Upgrade from v0.3.0

---

## Upgrading from v0.3.0

### Installation

```bash
pip install --upgrade emergence-ai
```

### Configuration

Add to your `emergence.json`:

```json
{
  "nautilus": {
    "enabled": true,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30,
    "workspace": "~/.openclaw/workspace",
    "db_path": "~/.emergence/nautilus.db",
    "chambers": {
      "daily_dir": "memory/daily",
      "corridor_dir": "memory/corridor",
      "vault_dir": "memory/vault",
      "corridor_retention_days": 30,
      "promotion_threshold": 0.7
    }
  }
}
```

### Migration

**No breaking changes.** All v0.3.x features continue working identically. Nautilus is completely opt-in.

Full migration guide: [docs/migration-v0.4.0.md](docs/migration-v0.4.0.md)

### First Use

```bash
# Check configuration
emergence nautilus status

# Register your existing memory files
python -c "from core.nautilus.session_hooks import register_recent_writes; register_recent_writes(hours=720)"  # Last 30 days

# Run initial maintenance
emergence nautilus maintenance

# Search your memories
emergence nautilus search "your query"
```

---

## Breaking Changes

**None.** This is a fully backwards-compatible release.

If you don't enable Nautilus, nothing changes. If you do enable it, it coexists peacefully with all existing Emergence features (drives, First Light, dream engine, aspirations).

---

## Known Issues

### OpenClaw Session Integration

Session hooks (`on_file_read`, `on_file_write`) are ready but require OpenClaw session event support. When OpenClaw adds these events, file tracking will become fully automatic. Until then, use `record_access()` or `register_recent_writes()`.

### Embeddings

Semantic search requires an embeddings provider:

- **Ollama** (local, free): Recommended for privacy
- **OpenAI/OpenRouter** (API): Better quality, costs money

Configure in `emergence.json`. Falls back to fuzzy text search if unavailable.

### Performance

For very large memory palaces (>10,000 files), initial indexing may take several minutes. Subsequent operations are fast. See [troubleshooting guide](docs/nautilus-troubleshooting.md#performance-optimization) for optimization tips.

---

## What's Next

**v0.4.1** (planned):

- Room UI enhancements for Nautilus widget
- Automatic session integration when OpenClaw adds hooks
- Performance optimizations for large workspaces
- Improved summarization with LLM support

**v0.5.0** (roadmap):

- Multi-agent memory sharing
- Memory export/import for backup
- Advanced semantic clustering
- Integration with dream engine for memory consolidation

---

## Credits

**Architecture & Implementation:** Jarvis Raven ([@jarvis-raven](https://github.com/jarvis-raven))
**Documentation & Testing:** Aurora AI Agent ([@AgentAurora](https://github.com/AgentAurora))
**Code Review & Integration:** Dan Aghili ([@dan-aghili](https://github.com/dan-aghili))

Special thanks to the Emergence community for feedback and alpha testing.

**Related Issues:** #67, #68, #69, #70, #71, #72
**Related PRs:** #118, #119, #120, #121, #124

---

## For Developers

### New Modules

- `core.nautilus.gravity` — Importance scoring
- `core.nautilus.chambers` — Temporal memory tiers
- `core.nautilus.doors` — Context-aware search
- `core.nautilus.mirrors` — Semantic indexing
- `core.nautilus.config` — Configuration management
- `core.nautilus.session_hooks` — File tracking integration
- `core.nautilus.nightly` — Automated maintenance
- `core.nautilus.db_utils` — Database utilities
- `core.nautilus.logging_config` — Logging infrastructure

### CLI Commands

- `emergence nautilus search <query> [--chamber CHAMBER] [--fuzzy|--semantic|--hybrid]`
- `emergence nautilus promote <file>`
- `emergence nautilus status`
- `emergence nautilus maintenance`

### Python API

```python
from core.nautilus import gravity, chambers, doors, mirrors
from core.nautilus.config import get_config, get_workspace, get_db_path
from core.nautilus.session_hooks import record_access, register_recent_writes
from core.nautilus.nightly import run_nightly_maintenance

# Calculate importance
score = gravity.calculate_importance("memory/important.md")

# Promote file
chambers.promote_to_corridor("memory/daily/2026-02-15.md")

# Search
results = doors.search("query", chamber="vault", strategy="semantic")

# Create embeddings
mirrors.index_file("memory/vault/knowledge.md")

# Track access
record_access("memory/file.md", access_type="write", context="session_xyz")

# Maintenance
run_nightly_maintenance()
```

### Database Schema

- `file_records` — Canonical file tracking
- `access_log` — Access history
- `importance_cache` — Pre-computed scores
- `chamber_metadata` — Chamber assignments
- `embeddings` — Vector representations
- `tags` — File categorization

Full API documentation: [docs/nautilus-api.md](docs/nautilus-api.md)

---

## Testing

Before publishing to PyPI, verify the package locally:

### Build Package

```bash
python -m build
```

This creates:

- `dist/emergence-ai-0.4.0.tar.gz` (source distribution)
- `dist/emergence_ai-0.4.0-py3-none-any.whl` (wheel)

### Verify Package Contents

```bash
tar -tzf dist/emergence-ai-0.4.0.tar.gz | grep nautilus
```

Expected output should include:

```
emergence-ai-0.4.0/core/nautilus/__init__.py
emergence-ai-0.4.0/core/nautilus/gravity.py
emergence-ai-0.4.0/core/nautilus/chambers.py
emergence-ai-0.4.0/core/nautilus/doors.py
emergence-ai-0.4.0/core/nautilus/mirrors.py
emergence-ai-0.4.0/core/nautilus/config.py
emergence-ai-0.4.0/core/nautilus/session_hooks.py
emergence-ai-0.4.0/core/nautilus/nightly.py
emergence-ai-0.4.0/core/nautilus/db_utils.py
emergence-ai-0.4.0/core/nautilus/logging_config.py
emergence-ai-0.4.0/core/nautilus/migrate_db.py
emergence-ai-0.4.0/core/nautilus/nautilus_cli.py
emergence-ai-0.4.0/core/nautilus/__main__.py
```

### Test Installation

```bash
# Create clean test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from local package
pip install dist/emergence-ai-0.4.0.tar.gz

# Verify imports
python -c "from core.nautilus import gravity, chambers, doors, mirrors; print('✓ Nautilus imports OK')"

# Verify CLI
emergence nautilus --help

# Verify version
python -c "import core; print(f'Version: {core.__version__}')"

# Cleanup
deactivate
rm -rf test_env
```

### Expected Test Results

All imports should succeed without errors. CLI should display help text. Version should be `0.4.0`.

---

_"Your memories matter. Nautilus helps you remember."_
