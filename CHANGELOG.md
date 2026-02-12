# Changelog

All notable changes to Emergence will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-02-12

### Added

**Lightweight Runtime State (Drive Context Bloat Fix)**
- Split drives.json into two files to prevent context bloat:
  - `drives.json` - Full config (descriptions, prompts, history)
  - `drives-state.json` - Minimal runtime (pressure, threshold, status, short description)
- Reduces context size from ~15KB to ~500-1000 bytes for agents with many drives
- New module: `core/drives/runtime_state.py`
- Status command loads lightweight state first for faster response
- Backwards compatible with existing installations

**Drive Status Tool & Automatic Polling**
- New `check_drive_status()` tool for agent self-introspection
- Agents can answer "how are you doing?" with real drive data
- Natural language formatting: "My CARE drive is at 88% (22/25)"
- Automatic polling every 5 minutes or 10 turns during long sessions
- Change detection for significant pressure changes (>2.0)
- Threshold crossing alerts (🔥 when drive triggers)
- New module: `core/drives/status_tool.py`

**Custom Shelves with Gitignore Protection**
- Separated built-in shelves (committed) from custom shelves (gitignored)
- Built-in: Memory, Drives, Aspirations, etc.
- Custom: Library, personal projects (in `room/src/components/shelves/custom/`)
- Prevents repo updates from overwriting agent custom shelves
- Example template provided for creating custom shelves

**Room State Path Resolution Fix**
- Room server now uses config-resolved path for drives.json
- Supports workspace-based installations (not just ~/.openclaw/state/)
- Fixes missing drives issue for agents with custom paths

### Fixed

**CLI Variable Name Bugs**
- Fixed `NameError: name 'state' is not defined` in `cmd_status()` (PR #11)
- Fixed `NameError: name 'COLOR_WARNING' is not defined` (PR #12)
- Both bugs introduced in PR #9 refactoring, now resolved

### Changed
- `drives status` command loads ~500-1000 bytes instead of ~15KB
- Faster response times for agents with many discovered drives
- Better separation between runtime data and configuration

## [0.2.1] - 2026-02-11

### Fixed

**Budget Tracking (Issue #1)**
- Added model-aware cost estimation based on actual model pricing
- New module: `core/setup/model_pricing.py` with pricing table for 20+ models
- Config generation now sets `cost_per_trigger` based on detected model
- kimi-k2.5: $0.003/trigger (was $2.50 default ❌)
- claude-sonnet-4: $0.030/trigger, claude-opus-4: $0.150/trigger
- Added warning in `drives status` if using default $2.50 estimate
- Resolves budget inflation bug reported by @AgentAurora

**Room Dashboard Startup (Issue #2)**
- Reduced console.error noise when drives.json doesn't exist during startup
- fileReader.js now silently returns null for ENOENT (expected during init)
- Empty drives state already handled gracefully in UI
- Fixes harmless but confusing log noise during Room startup

**First Light Migration (Issue #3)**
- Added grandfathering for agents upgrading from pre-v0.2.0
- New: `scan_historical_sessions()` scans memory/sessions/ for historical evidence
- New: `check_grandfather_eligibility()` validates if historical sessions meet gates
- New: `grandfather_first_light()` auto-completes with evidence attached
- CLI commands:
  - `emergence first-light grandfather` - Complete for pre-v0.2.0 agents
  - `emergence first-light complete --grandfather` - Same via complete command
- Upgraders with 10+ sessions, 7+ days, 3+ drives can now graduate
- Resolves "0/10 sessions" bug for upgraders reported by @AgentAurora

### Changed
- Pricing estimates based on OpenRouter rates as of 2026-02-11
- Users can still manually override `cost_per_trigger` in emergence.json

## [0.2.0] - 2026-02-11

### Added

**Drive Consolidation System (Phases 2-3.5)**
- Irreducibility testing for drive discovery consolidation
- Similarity detection via Ollama embeddings (with Jaccard text fallback)
- Configurable embeddings provider (Ollama local or OpenAI-compatible APIs)
- Pending reviews system for consolidation suggestions
- Aspect system: drives can have sub-facets without full fragmentation
- Budget controls: daily limits, throttling, cost projections
- CLI commands:
  - `emergence drives review` - Review pending consolidation decisions
  - `emergence drives review <name>` - Show irreducibility test for specific drive
  - `emergence drives activate <name>` - Activate latent drives
  - `emergence drives aspects <name>` - Manage drive aspects
- Enhanced `drives status` display:
  - Aspect counts under parent drives
  - Budget tracking (color-coded: green/yellow/red)
  - Pending reviews count
  - Latent drives section (`--show-latent` flag)
  - Projected costs (triggers/day → $/month)
  - Graduation candidates (aspects with >50% pressure dominance)

**First Light Completion Mechanism (Phase 2.5)**
- Session counter tracking
- Automatic completion gates (10 sessions, 7 days, 3+ drives)
- Manual completion: `emergence first-light complete`
- Graduation ceremony with celebratory message
- Post-First Light state (consolidation active)
- CLI commands:
  - `emergence first-light status` - Show progress gates
  - `emergence first-light complete` - Manual graduation

**Room UI Integration (Phase 3.5)**
- Budget Transparency Shelf: daily spend/limit with color warnings (75% yellow, 90% red)
- Pending Reviews Shelf: consolidation suggestions with "Review Now" action
- Latent Drives Shelf: inactive drives with budget-aware activation
- Enhanced Drives Shelf: aspect counts, graduation candidates
- New API routes:
  - `/api/budget/status` - Daily spend, limit, projected monthly costs
  - `/api/first-light/status` - Progress gates, session count
  - `/api/drives/pending-reviews` - Drives awaiting review
  - `/api/drives/latent` - Inactive drives with budget status
  - `/api/drives/:name/aspects` - Aspect management
  - `POST /api/drives/:name/activate` - Activate latent drive
  - `POST /api/first-light/complete` - Manual First Light graduation

**Embeddings Configuration**
- Support for both Ollama (local, free) and OpenAI-compatible APIs (OpenRouter, etc.)
- Configurable in `emergence.json`:
  ```json
  {
    "embeddings": {
      "provider": "ollama",
      "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "nomic-embed-text"
      },
      "openai": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "text-embedding-3-small",
        "api_key_env": "OPENROUTER_API_KEY"
      }
    }
  }
  ```
- Graceful degradation: falls back to Jaccard text matching if no provider available

### Changed
- Drive consolidation parameters finalized:
  - Similarity threshold: 0.75
  - Aspect rate increment: 0.2/hr (not 0.3)
  - Max aspects per drive: 5
  - Migration: 50% pressure dominance + 10 satisfactions + 14 days
- Philosophy: **Transparency + Agency** - discovery never blocked, agent decides, budget transparent

### Fixed
- Budget wizard now allows daily limits as low as $1 (previously forced minimum $10)
- Post-session analyzer properly registers drive discoveries from First Light sessions

### Technical
- Backwards compatible with v0.1.x configs (auto-migration for old `first-light.json`)
- No new Python dependencies (embeddings use stdlib only)
- No new npm dependencies
- All 333 existing tests passing + 21 new completion tests
- Integration tested: CLI, config, room, WebSocket, API routes

---

## [0.1.2] - 2026-02-10

### Fixed
- `created_by` validation in drive discovery

---

## [0.1.1] - 2026-02-10

### Added
- Post-session analyzer for drive discoveries

---

## [0.1.0] - 2026-02-10

### Added
- Initial public release
- Core drive system (CARE, MAINTENANCE, REST)
- First Light onboarding phase
- Room dashboard UI
- Memory consolidation
- Dream engine
- Setup wizard (`emergence awaken`)

[0.2.0]: https://github.com/jarvis-raven/emergence/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/jarvis-raven/emergence/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jarvis-raven/emergence/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jarvis-raven/emergence/releases/tag/v0.1.0
