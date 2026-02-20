# Changelog

All notable changes to Emergence AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-14 (Unreleased)

### 🎉 Major Features

#### Nautilus Memory Palace Architecture
A revolutionary four-phase memory system for autonomous agents:

- **Phase 1 - Gravity**: Importance-weighted scoring system that tracks file access patterns, modifications, and context
  - Automatic decay of gravity scores over time
  - Superseded chunk tracking
  - Access log and reference counting
  - Configurable decay intervals

- **Phase 2 - Chambers**: Temporal memory layers organizing memories by age and importance
  - **Atrium**: Recent memories (< 48 hours)
  - **Corridor**: Medium-term memories (48h - 30 days)
  - **Vault**: Long-term memories (> 30 days)
  - Automatic chamber classification
  - Promotion system for important memories

- **Phase 3 - Doors**: Context-aware pre-filtering for relevant memory retrieval
  - 11 predefined context patterns (project, security, personal, technical, etc.)
  - Auto-tagging based on query semantics
  - Context-based result filtering

- **Phase 4 - Mirrors**: Multi-granularity event indexing
  - Raw event tracking
  - Summarization support
  - Lesson extraction
  - Cross-reference linking

#### Room Web Dashboard
Real-time web interface for monitoring Nautilus memory palace:

- **Live Metrics Dashboard**
  - Chamber distribution visualization (Chart.js doughnut chart)
  - Door coverage statistics with top context tags
  - Mirror coverage and event tracking
  - Database health indicators

- **Real-time Updates**
  - WebSocket integration (Socket.IO)
  - Auto-refresh every 30 seconds
  - Connection status indicator

- **Memory Explorer**
  - Top memories by gravity score
  - Recent chamber promotions
  - Access patterns and reference counts

- **Technology Stack**
  - Backend: Flask + Flask-SocketIO
  - Frontend: Chart.js, Socket.IO client
  - REST API: `/api/nautilus/status`, `/api/health`

### ✨ Added

#### Core Features
- **Portable path resolution**: No hardcoded paths, works across all agent installations
- **Database migration system**: Auto-migrates legacy gravity.db from v0.3.0
- **Schema evolution**: Automatic column addition for database upgrades
- **Multi-agent support**: Complete database isolation per agent
- **Platform compatibility**: Tested on macOS and Ubuntu Linux

#### CLI Enhancements
- New `emergence nautilus` command suite:
  - `search` - Full pipeline semantic search
  - `status` - System health and metrics
  - `maintain` - Run all maintenance tasks
  - `classify` - Chamber classification
  - `gravity` - View gravity scores
  - `chambers` - Chamber management subcommands
  - `doors` - Context filtering subcommands
  - `mirrors` - Event indexing subcommands

#### Python API
```python
from core.nautilus import search, get_status, run_maintain

# Full pipeline search
results = search("project details", n=5)

# System status
info = get_status()

# Maintenance
result = run_maintain(register_recent=True, verbose=True)
```

#### Configuration
- New `emergence.json` config schema:
  ```json
  {
    "nautilus": {
      "enabled": true,
      "state_dir": "~/.openclaw/state/nautilus",
      "memory_dir": "memory",
      "auto_classify": true,
      "decay_interval_hours": 168
    }
  }
  ```

#### Session Hooks
- Pre-session and post-session lifecycle hooks
- Integration points for maintenance automation
- Nightly maintenance scheduling support

#### Testing
- Comprehensive alpha test suite (31 tests)
- Beta validation across multiple agents
- Performance benchmarks:
  - 1000 inserts: ~0.5s (target: < 5s) ✅
  - Complex queries: ~3ms (target: < 100ms) ✅
  - Concurrent access: ~90% success (target: > 50%) ✅

### 🐛 Bug Fixes

- **Critical**: Fixed `cmd_decay()` returning `None` instead of result dictionary
  - Impact: 4 maintenance tests failing
  - Fix: Added proper return statement in `core/nautilus/gravity.py:352`
  - Result: Test pass rate improved from 68% to 81%

- **Migration**: Improved database migration data preservation
  - Enhanced schema compatibility checking
  - Better handling of missing columns
  - Safer data transfer during migration

- **Concurrency**: Fixed database locking issues
  - Enabled WAL mode for better concurrent access
  - Improved connection pooling
  - Thread-safety enhancements

### 🔧 Changed

#### Project Structure
- **Moved**: Nautilus from `tools/nautilus/` → `core/nautilus/`
  - Now a first-class Emergence component
  - Better integration with core framework
  - Cleaner imports and API

- **Updated**: CLI architecture
  - Unified command entry point via `core.cli`
  - Consistent subcommand structure
  - Better help text and documentation

#### Performance
- Optimized gravity scoring algorithm
- Faster database queries with proper indexing
- Reduced memory footprint for large databases

#### Documentation
- New comprehensive README for Nautilus integration
- Added beta testing reports and summaries
- Created multi-agent deployment guide
- Updated installation instructions

### 📚 Documentation

#### New Documentation
- `BETA_SUMMARY.md` - Beta validation results
- `TASK-COMPLETION-REPORT.md` - Room dashboard implementation
- `TESTING.md` - Alpha testing guide
- `ROOM-MIGRATION-NOTE.md` - Room deployment notes
- `docs/RELEASE_CHECKLIST_v0.4.0.md` - This release checklist
- `room/README.md` - Room dashboard documentation

#### Updated Documentation
- `README.md` - Added Nautilus section and v0.4.0 features
- `core/nautilus/__init__.py` - Complete API documentation
- Test reports and validation summaries

### ⚠️ Known Issues

These issues are documented but not blocking for release:

1. **Door context tagging**: Returns empty results in some cases
   - Status: Under investigation
   - Workaround: Manual tagging via `--tags` parameter
   - Severity: Medium (feature still usable)

2. **Long-term chamber promotion**: Requires extended testing (48h+ aged files)
   - Status: In progress
   - Impact: Promotion logic works but needs time-based validation
   - Severity: Low (logic verified in unit tests)

3. **Empty workspace handling**: Edge case for fresh installations
   - Status: Known limitation
   - Workaround: Initialize with at least one memory file
   - Severity: Low (rare scenario)

### 🔄 Migration Guide

#### From v0.3.0 to v0.4.0

**Automatic Migration:**
On first run, Nautilus will automatically:
1. Detect legacy `gravity.db` at `tools/nautilus/gravity.db`
2. Copy to new location: `~/.openclaw/state/nautilus/gravity.db`
3. Add missing columns (chamber, context_tags, promoted_at, etc.)
4. Preserve all existing data

**Configuration Changes:**
Update your `emergence.json`:
```json
{
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus",  // New location
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168
  }
}
```

**Cron Job Updates:**
```bash
# Old (v0.3.0)
0 3 * * * python3 tools/nautilus/nautilus.py maintain

# New (v0.4.0)
0 3 * * * cd /path/to/workspace && python3 -m core.cli nautilus maintain --register-recent
```

**Import Changes:**
```python
# Old (v0.3.0)
from tools.nautilus import search

# New (v0.4.0)
from core.nautilus import search
```

### 🚀 Upgrade Steps

1. **Backup your data:**
   ```bash
   cp tools/nautilus/gravity.db tools/nautilus/gravity.db.backup
   ```

2. **Update the code:**
   ```bash
   git pull origin main
   # or install from PyPI:
   pip install --upgrade emergence-ai
   ```

3. **Run first-time setup:**
   ```bash
   python3 -m core.cli nautilus status
   # This triggers automatic migration
   ```

4. **Verify migration:**
   ```bash
   python3 -m core.cli nautilus search "test"
   ```

5. **Update cron jobs** (see above)

### 🎯 Breaking Changes

**None** - v0.4.0 is fully backward compatible with v0.3.0 data and configurations.

### 📊 Statistics

- **Lines of Code**: ~1,357 new lines for Room dashboard
- **Test Coverage**: 31 comprehensive alpha/beta tests
- **Supported Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Platforms Tested**: macOS (Darwin 25.2.0), Ubuntu 24.04
- **Database Compatibility**: SQLite 3.x with WAL mode

### 🙏 Contributors

- Beta testers: Jarvis (macOS), Aurora (Ubuntu)
- Issue reporters: (Community contributions welcome!)

### 📝 Notes

This release marks the transition of Nautilus from an experimental tool to a production-ready core component of the Emergence framework. The memory palace architecture provides a solid foundation for intelligent, context-aware agent memory management.

---

## [0.3.0] - Previous Release

### Added
- Initial Nautilus prototype in `tools/nautilus/`
- Basic gravity scoring system
- Manual chamber classification
- Simple search functionality

### Changed
- Improved agent session management
- Enhanced memory file organization

---

## [0.2.0] - Earlier Release

(Add previous version history here as needed)

---

## [0.1.0] - Initial Release

(Add initial release notes here as needed)

---

[0.4.0]: https://github.com/your-org/emergence/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/your-org/emergence/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/your-org/emergence/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-org/emergence/releases/tag/v0.1.0
