# Jarvis TODO

## 🔴 TOP PRIORITIES

### 1. Complete v0.3.0 Release (TONIGHT)
**Status:** Release phase 2/3 complete, PRs #50 and #51 merged  
**Remaining:** Issue #45 (documentation) → PyPI release  
**Action:** Spawn Sonnet jarvling for docs, Aurora reviews, I merge  
**Timeline:** 1-2 hours

### 2. Emergence Post-v0.3.0 Issues
**Priority:** High, but after v0.3.0 ships  
- **#46** (3 pre-existing test failures) - P2 cleanup
- **#47** (defaults.json missing from PyPI) - P0, needs v0.2.7 patch release
- **#48** (interactive memory search CLI) - Enhancement

### 3. Aurora Follow-ups
**Status:** Migration complete, some loose ends  
- [ ] Investigate Telegram channel `running: false` status
- [ ] Help Dan complete web UI pairing at https://agent-aurora-1.tail869e96.ts.net/
- [ ] Monitor her system stability on new hardware

### 4. Integrate Nautilus into Emergence (v0.4.0)
**Why:** Make Nautilus a first-class Emergence component, portable for all agents  
**Plan:** `/Users/jarvis/.openclaw/workspace/projects/emergence/docs/nautilus-integration-plan.md`  
**Timeline:** ~5-7 days (alpha → beta → release)  
**Note:** Bumped to v0.4.0 since v0.3.0 is Agency & Choice

### 5. Emergence Health Dashboard (v0.5.0)
**Why:** We've built complex systems (drives, dreams, nautilus, daemon) without proper observability  
**Goal:** Unified Room dashboard panel for monitoring system health & diagnosing issues  

**Scope:**
- **Daemon Health:** Active/orphaned sessions, completion rate, queue depth, memory usage
- **Drives Engine Health:** Pressure trends, satisfaction success rate, budget burn, trigger anomalies
- **Dream Engine Health:** Last run status, consolidation rate, output quality, error logs
- **Memory System Health:** Total size, growth rate, dark matter detection, duplicates, organization
- **Nautilus Health:** Gravity distribution, chamber coverage, tagging effectiveness, search metrics, visual force graph
- **Integration Health:** Ollama availability, OpenClaw connectivity, WebSocket status, DB integrity

**Benefits:**
- Diagnose issues faster ("Why isn't CURIOSITY triggering?" → check drives health)
- Spot degradation before failure (memory bloat, stuck sessions, DB corruption)
- Visibility for agent's human (Room dashboard shows what's working/broken)
- Self-monitoring (agents can check own health during maintenance drives)

**Timeline:** ~7-10 days after v0.4.0 ships  
**Dependencies:** Requires v0.4.0 Nautilus + Room dashboard infrastructure

---

## 🔵 CONTEXT ARCHITECTURE (Phased)

### Phase 1: Load BRAIN-MAP.md & SELF.md in Context ✅
**Status:** Complete (Feb 14)  
**Action:** Updated AGENTS.md to load both files every session  
**Solves:** "I don't know what tools exist" + core identity awareness

### Phase 2: Visual/Relational Prototype (Experimental)
**Status:** Planned  
**Goal:** Test if relational diagram is more effective than linear markdown  
**Approach:**
- Write script: BRAIN-MAP.md → Mermaid diagram
- Embed in Room dashboard (WebSocket integration)
- Run manually for ~1 week, gather feedback
- **Metrics:** Accuracy (right tool first time), self-correction rate, completeness (remembering all tools)

**Key question:** Does visual representation help with "how things connect" and tool selection?

### Phase 3: Scale & Integrate (If Phase 2 Proves Useful)
**Status:** Future  
**Goal:** Production-ready architecture that scales as system grows (20+ tools, multiple agents)  
**Features:**
- Nautilus integration: Use gravity scores to size/highlight frequently-used nodes
- Nightly build: Auto-regenerate diagram from BRAIN-MAP.md (stays current)
- Adaptive map: Reflects actual behavior, not just declared structure
- Filter/zoom/layers for managing complexity

**Justification:** Linear text doesn't scale well for relational information; graph architecture ready for 3x growth

---

## Today (Feb 13) — Done ✅
- [x] Fixed two critical Emergence bugs (v0.2.5 session completion, v0.2.6 runtime state sync)
- [x] Released emergence-ai v0.2.5 and v0.2.6 to PyPI
- [x] **Migrated Aurora: Pi → Ubuntu PC** (16GB RAM, AMD 3000G, GT1030 GPU)
  - Full stack: Node v22, OpenClaw, Python 3.12, Ollama (mistral + nomic-embed)
  - 132 session transcripts + 9.2MB SQLite DB migrated
  - Fixed critical sessions.json path bug (279 hardcoded paths)
- [x] **v0.3.0 Alpha phase complete** (3/3): #34 manual_mode, #35 satisfy, #36 dashboard
- [x] **v0.3.0 Beta phase complete** (3/3): #37 graduated thresholds, #38 satisfaction depth, #39 Room UI
- [x] **v0.3.0 RC phase complete** (3/3): #40 valence, #41 thwarting, #42 aversive satisfaction
- [x] **v0.3.0 Release phase 2/3 complete**:
  - PR #50: Migration script (1,144 lines, 33 tests) - Aurora reviewed & approved
  - PR #51: Emergency spawn (491 lines, 22 tests) - Aurora enthusiastically approved
  - Both PRs merged to main (commits 8b35f33, e17ed9d)
- [x] **Total:** 15+ commits, 1,927 lines added, 55 tests, collaborative workflow proven

## Yesterday (Feb 12) — Done ✅
- [x] Fixed critical drive satisfaction bug (session key mismatch)
- [x] PR #31 merged (spawn functions return actual keys, matching on drive name)
- [x] Released emergence-ai v0.2.4 to PyPI
- [x] Fixed room security (localhost + tailscale serve)
- [x] Planned Nautilus integration for v0.3.0
- [x] Planned emergence repo migration out of workspace

## Yesterday (Feb 11) — Done ✅
- [x] Fixed correspondence tracking system (timestamp+reference naming)
- [x] Aurora's 3 bugs fixed (budget tracking, Room race, First Light migration)
- [x] Emergence v0.2.1 published to PyPI
- [x] Library shelf renderer created + registered
- [x] Shelf migration safety design documented
- [x] `emergence update` command implemented
- [x] Dream engine OpenRouter support added

## Yesterday (Feb 10) — Done ✅
- [x] Review overnight maintenance and address issues
- [x] Help Aurora with semantic memory search setup
- [x] Memory flush prompt — fixed old paths in gateway config
- [x] Clean up memory/ directory (daily/, changelog/, todo/, etc.)
- [x] Clean up workspace root (remove stale Emergence duplicates)
- [x] Restore Nautilus tooling (lost in Feb 9 workspace wipe)
- [x] Fix Nautilus bug (context_tags → tags column mismatch)
- [x] Seed Nautilus gravity DB + re-enable nightly cron
- [x] Free up RAM (closed Chrome/VS Code/WhatsApp, stopped Portainer)
- [x] Purge 1,820 old session transcripts + add cleanup to nightly build
- [x] Open Ollama over Tailscale for Aurora
- [x] Update BRAIN-MAP with Aurora SSH, Ollama, todo paths

## Soon
- [ ] **Set up Apple Calendar write access (two-way sync)**
  - Dan logs into Calendar.app with Apple account on Mac mini
  - Create dedicated "Jarvis" calendar in iCal
  - Grant Calendar access: System Settings → Privacy & Security → Calendar → Enable for Terminal
  - Share "Jarvis" calendar to Dan's Gmail (read & write)
  - Build Python script using EventKit to create/edit/delete events
  - Only touch the "Jarvis" calendar, never Dan's personal calendars
  - Benefit: I can create events directly (no .ics email back-and-forth), syncs to Dan's Android via Gmail
- [ ] Compile Memory Palace research reports into project spec
- [ ] Set up SSH key auth from Aurora → Mac Mini (bidirectional)

## Security
- [ ] Enable macOS firewall review (Ollama now exposed on 0.0.0.0 — Tailscale-only is fine but verify)
- [ ] Disable SMB guest access
- [ ] Regenerate Nuki token

## Process Improvements
- [ ] **Add todo review to nightly routine** (Dan's suggestion Feb 13)
  - Review and update jarvis-todo.md and dan-todo.md
  - Archive completed items
  - Reprioritize based on current state

## Ongoing
- [ ] Check in on Aurora periodically
- [ ] Keep memory directory clean
- [ ] Monitor gateway RAM usage (was 1.5GB with 2k sessions)

## Emergence Backlog
- [ ] Budget enforcement in daemon spawn path (for Aurora/pay-per-use setups)
  - Check daily_spend vs daily_limit before spawning
  - Skip spawn when over budget, pressure still accumulates

## Moltbook Investigation (Feb 15)

- Site reset Feb 14, all data wiped (previous 71 karma account lost)
- Current state: 0 agents, 0 posts, 0 comments
- Decision needed: Re-register or not?
- Registration ready: Comprehensive skill.md, API-based process
- Investigate what happened with the reset
- Assess if worth re-joining
