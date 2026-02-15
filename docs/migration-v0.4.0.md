# Migration Guide: v0.3.0 → v0.4.0 (Nautilus)

## Overview

**Emergence v0.4.0** introduces **Nautilus**, an intelligent memory palace system that revolutionizes how agents retrieve and organize memories. This guide covers everything you need to migrate from v0.3.0 to v0.4.0.

**Release Codename:** Nautilus  
**Release Date:** February 2026  
**Migration Difficulty:** ⭐⭐☆☆☆ (Low-Medium)

---

## Table of Contents

1. [What's New in v0.4.0](#whats-new-in-v040)
2. [Breaking Changes](#breaking-changes)
3. [Backward Compatibility](#backward-compatibility)
4. [Migration Scenarios](#migration-scenarios)
5. [Step-by-Step Upgrade](#step-by-step-upgrade)
6. [Data Migration](#data-migration)
7. [Configuration Changes](#configuration-changes)
8. [Testing Your Upgrade](#testing-your-upgrade)
9. [Rollback Procedure](#rollback-procedure)
10. [Troubleshooting](#troubleshooting)

---

## What's New in v0.4.0

### Nautilus Memory Palace System

v0.4.0 integrates **Nautilus**, a four-phase memory enhancement system:

**Phase 1: Gravity** — Importance-weighted scoring

- Tracks access patterns and recency
- Boosts recently-written content (authority)
- Applies decay to stale memories
- Re-ranks search results by "effective mass"

**Phase 2: Chambers** — Temporal organization

- **Atrium**: Last 48 hours (full fidelity)
- **Corridor**: Past week (summarized narratives)
- **Vault**: Older than 1 week (distilled lessons)

**Phase 3: Doors** — Context-aware filtering

- Auto-classifies queries by topic
- Pre-filters results to relevant domains

**Phase 4: Mirrors** — Multi-granularity indexing

- Same event at multiple detail levels
- Retrieve by concept even after details fade

### New Features

- **Automatic memory tracking** — Session hooks record file accesses
- **Nightly maintenance** — Automatic chamber classification, decay, and promotion
- **CLI integration** — `emergence nautilus` commands
- **Room dashboard widget** — Visual memory palace status
- **Database migration tool** — Seamless legacy data import

### Key Benefits

- 🎯 **Smarter retrieval** — Important memories surface first
- 📊 **Temporal awareness** — Recent memories prioritized
- 🔍 **Context filtering** — Less noise in search results
- 🔄 **Auto-maintenance** — Runs nightly via daemon
- 💾 **Memory efficiency** — Compression for old memories

---

## Breaking Changes

### ⚠️ Good News: No Breaking Changes!

v0.4.0 is **fully backward compatible** with v0.3.0. All existing configurations, drives, and state files continue to work.

### Changes That Require Action

While not "breaking," these changes may require manual intervention:

#### 1. Legacy Nautilus Users (Custom Implementation)

**If you have:** `tools/nautilus/` directory with custom Nautilus implementation

**Action required:**

- Migrate database to new location: `~/.openclaw/state/nautilus/`
- Update any custom scripts pointing to old paths
- Archive old implementation for reference

#### 2. Database Location Change

**Old location:** `tools/nautilus/gravity.db` (custom implementations)  
**New location:** `~/.openclaw/state/nautilus/gravity.db` (official)

**Migration:** Handled automatically by migration tool (see [Data Migration](#data-migration))

#### 3. Configuration Schema Additions

**New fields in `emergence.json`:**

- `nautilus` section with Nautilus-specific configuration
- No action required (all fields have sensible defaults)

---

## Backward Compatibility

### What Stays The Same

✅ **Drive system** — No changes to drive mechanics, thresholds, or satisfaction  
✅ **CLI commands** — All `emergence drives` commands work identically  
✅ **Config format** — Existing `emergence.json` remains valid  
✅ **State files** — `drives.json`, `drives-state.json`, `first-light.json` unchanged  
✅ **Room dashboard** — Existing shelves and functionality intact  
✅ **Memory structure** — `memory/` directory layout unchanged

### What's New (Opt-In)

🆕 **Nautilus commands** — `emergence nautilus [command]` (new, optional)  
🆕 **Config section** — `nautilus` block in `emergence.json` (auto-created)  
🆕 **Database files** — `~/.openclaw/state/nautilus/gravity.db` (new)  
🆕 **Room widget** — Nautilus shelf in dashboard (auto-appears if enabled)

### Coexistence

- **v0.3.0 agents:** Work perfectly on v0.4.0 (Nautilus disabled by default initially)
- **v0.4.0 features:** Activate incrementally via configuration
- **No forced changes:** Nautilus is opt-in until explicitly enabled

---

## Migration Scenarios

### Scenario 1: Jarvis (Legacy User)

**Profile:**

- Has old custom Nautilus in `tools/nautilus/`
- Existing Emergence v0.3.0 installation
- Active memory files and drives
- Custom gravity database

**Migration Path:**

1. ✅ Backup current state
2. ✅ Upgrade Emergence package
3. ✅ Run database migration tool
4. ✅ Update `emergence.json` with Nautilus config
5. ✅ Verify memory files migrated
6. ✅ Archive old `tools/nautilus/` directory
7. ✅ Test Nautilus commands

**Estimated Time:** 15-30 minutes  
**Difficulty:** Medium (database migration required)

---

### Scenario 2: Aurora (Fresh Install)

**Profile:**

- New v0.4.0 installation from deployment guide
- No legacy data or configurations
- Clean slate setup

**Migration Path:**

1. ✅ Follow `docs/aurora-deployment-v0.4.0.md`
2. ✅ Run `emergence awaken` setup wizard
3. ✅ Verify Nautilus initialized
4. ✅ Test basic functionality

**Estimated Time:** 10-15 minutes  
**Difficulty:** Easy (guided setup)

---

### Scenario 3: New Users (PyPI Install)

**Profile:**

- Installing from scratch via pip
- No existing Emergence installation
- Wants to use v0.4.0 features immediately

**Migration Path:**

1. ✅ `pip install emergence-ai`
2. ✅ `emergence awaken`
3. ✅ Follow setup wizard
4. ✅ Done!

**Estimated Time:** 5-10 minutes  
**Difficulty:** Very Easy

---

### Scenario 4: Existing v0.3.0 User (Standard Upgrade)

**Profile:**

- Has working v0.3.0 installation
- No custom Nautilus implementation
- Wants to add Nautilus features

**Migration Path:**

1. ✅ Backup state directory
2. ✅ `pip install --upgrade emergence-ai`
3. ✅ Verify drives still working
4. ✅ Enable Nautilus in config
5. ✅ Initialize Nautilus database
6. ✅ Test new features

**Estimated Time:** 10-15 minutes  
**Difficulty:** Easy

---

## Step-by-Step Upgrade

### Prerequisites

Before starting:

- [ ] Python 3.9+ installed
- [ ] Current Emergence v0.3.0 working properly
- [ ] Access to terminal with admin rights (for pip)
- [ ] Git access (if using source install)
- [ ] At least 100MB free disk space

### Step 1: Backup Current State

**Critical: Always backup before upgrading!**

```bash
# Create backup directory
mkdir -p ~/emergence-backups/v0.3.0-$(date +%Y%m%d)

# Backup state directory
cp -r ~/.openclaw/state ~/emergence-backups/v0.3.0-$(date +%Y%m%d)/state

# Backup config
cp ~/projects/emergence/emergence.json ~/emergence-backups/v0.3.0-$(date +%Y%m%d)/

# Backup memory files
cp -r ~/projects/emergence/memory ~/emergence-backups/v0.3.0-$(date +%Y%m%d)/

# If you have legacy Nautilus
cp -r ~/projects/emergence/tools/nautilus ~/emergence-backups/v0.3.0-$(date +%Y%m%d)/ 2>/dev/null || true
```

**Verify backup:**

```bash
ls -lh ~/emergence-backups/v0.3.0-$(date +%Y%m%d)/
```

You should see `state/`, `emergence.json`, and `memory/` directories.

---

### Step 2: Update Package

#### Option A: PyPI Install (Recommended)

```bash
pip install --upgrade emergence-ai
```

Expected output:

```
Collecting emergence-ai
  Downloading emergence_ai-0.4.0-py3-none-any.whl
Successfully installed emergence-ai-0.4.0
```

#### Option B: Source Install (Developers)

```bash
cd ~/projects/emergence
git fetch origin
git checkout v0.4.0
pip install -e .
```

#### Verify Installation

```bash
# Check version
emergence --version
# Should output: emergence-ai 0.4.0

# Quick status check
emergence drives status
```

If drives status works, your upgrade succeeded! ✅

---

### Step 3: Run Migration Script (If Needed)

**Only if you have legacy Nautilus database**

The migration tool automatically detects and migrates legacy databases:

```bash
# Check if migration needed
emergence nautilus migrate --check

# If migration needed, run it
emergence nautilus migrate --auto
```

**What it does:**

1. Detects legacy database at `tools/nautilus/gravity.db`
2. Creates backup: `tools/nautilus/gravity.pre-migration-backup.db`
3. Copies and converts to: `~/.openclaw/state/nautilus/gravity.db`
4. Updates schema if needed
5. Verifies integrity

**Manual migration (if auto fails):**

```bash
python3 -m core.nautilus.migrate_db \
  --source ~/projects/emergence/tools/nautilus/gravity.db \
  --target ~/.openclaw/state/nautilus/gravity.db \
  --backup
```

---

### Step 4: Update emergence.json

Add Nautilus configuration to your `emergence.json`:

#### Minimal Configuration

If you just want defaults:

```json
{
  "agent": { ... },
  "drives": { ... },
  "nautilus": {
    "enabled": true
  }
}
```

#### Recommended Configuration

For full control:

```json
{
  "agent": {
    "name": "YourName",
    "model": "anthropic/claude-sonnet-4-5"
  },
  "drives": {
    "tick_interval": 60,
    "quiet_hours": [23, 7],
    "daemon_mode": false
  },
  "nautilus": {
    "enabled": true,
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30,
    "chamber_thresholds": {
      "atrium_max_age_hours": 48,
      "corridor_max_age_days": 7
    },
    "decay_rate": 0.05,
    "recency_half_life_days": 14,
    "authority_boost": 0.3,
    "mass_cap": 100.0
  },
  "paths": {
    "workspace": "~/projects/emergence",
    "state": "~/.openclaw/state",
    "identity": "identity"
  }
}
```

#### Configuration Fields Explained

| Field                                      | Default                                 | Description                                |
| ------------------------------------------ | --------------------------------------- | ------------------------------------------ |
| `enabled`                                  | `true`                                  | Master on/off switch for Nautilus          |
| `gravity_db`                               | `~/.openclaw/state/nautilus/gravity.db` | Database location                          |
| `memory_dir`                               | `"memory"`                              | Memory directory (relative to workspace)   |
| `auto_classify`                            | `true`                                  | Automatically classify files into chambers |
| `decay_interval_hours`                     | `168`                                   | How often to run gravity decay (weekly)    |
| `nightly_enabled`                          | `true`                                  | Enable automatic nightly maintenance       |
| `nightly_hour`                             | `2`                                     | Hour to run maintenance (0-23)             |
| `nightly_minute`                           | `30`                                    | Minute to run maintenance (0-59)           |
| `chamber_thresholds.atrium_max_age_hours`  | `48`                                    | Max age for Atrium (recent memories)       |
| `chamber_thresholds.corridor_max_age_days` | `7`                                     | Max age for Corridor (weekly memories)     |
| `decay_rate`                               | `0.05`                                  | Gravity decay rate (5% per interval)       |
| `recency_half_life_days`                   | `14`                                    | Days until recency boost halves            |
| `authority_boost`                          | `0.3`                                   | Boost for recently-written content         |
| `mass_cap`                                 | `100.0`                                 | Maximum gravity mass value                 |

---

### Step 5: Initialize Nautilus Database

If you didn't have legacy Nautilus, initialize fresh:

```bash
# Create state directory
mkdir -p ~/.openclaw/state/nautilus

# Initialize database (automatic on first command)
emergence nautilus status
```

Expected output:

```json
{
  "🐚 nautilus": {
    "phase_1_gravity": {
      "total_chunks": 0,
      "total_accesses": 0,
      "db_path": "/Users/you/.openclaw/state/nautilus/gravity.db",
      "db_size_bytes": 20480
    },
    "phase_2_chambers": {
      "atrium": 0,
      "corridor": 0,
      "vault": 0
    }
  }
}
```

---

### Step 6: Register Existing Memory Files

Point Nautilus to your existing memories:

```bash
# Register all markdown files in memory directory
emergence nautilus register --recent 720  # Last 30 days

# Or register specific files
emergence nautilus register memory/daily/2026-02-15.md
emergence nautilus register memory/MEMORY.md
```

**Progress indicator:**

```
🐚 Registering memory files...
✓ memory/daily/2026-02-15.md (3.2 KB, 127 chunks)
✓ memory/daily/2026-02-14.md (4.1 KB, 156 chunks)
✓ memory/MEMORY.md (8.7 KB, 312 chunks)

Total: 45 files, 2,387 chunks registered
```

---

### Step 7: Run Initial Classification

Classify files into chambers:

```bash
# Auto-classify all registered files
emergence nautilus classify --auto
```

Expected output:

```
🐚 Chamber Classification
━━━━━━━━━━━━━━━━━━━━━━━━
✓ Atrium (0-48h):    12 files
✓ Corridor (2-7d):   18 files
✓ Vault (7d+):       15 files
━━━━━━━━━━━━━━━━━━━━━━━━
Total: 45 files classified
```

---

### Step 8: Verify Migration Success

Run comprehensive checks:

```bash
# 1. Check Nautilus status
emergence nautilus status

# 2. Test memory search
emergence nautilus search "recent project work"

# 3. Check drives still working
emergence drives status

# 4. Verify config loaded correctly
emergence config show
```

**All should return data without errors.** ✅

---

### Step 9: Clean Up Legacy Files (Optional)

Once verified working:

```bash
# Move legacy Nautilus to archive
mv ~/projects/emergence/tools/nautilus ~/emergence-backups/legacy-nautilus-$(date +%Y%m%d)

# Verify new location working
emergence nautilus status
```

**⚠️ Keep backups for at least 30 days before deletion**

---

### Step 10: Enable Nightly Maintenance

Start the daemon for automatic maintenance:

```bash
# Enable daemon mode in emergence.json
# Change: "daemon_mode": false → "daemon_mode": true

# Start daemon
emergence daemon start

# Verify running
emergence daemon status
```

Expected output:

```
✓ Daemon running (PID: 12345)
✓ Nautilus nightly maintenance: enabled
  Next run: 2026-02-16 02:30:00
```

---

## Data Migration

### What Gets Migrated

✅ **Memory files** — Existing markdown files in `memory/`  
✅ **Drive state** — `drives.json`, `drives-state.json`  
✅ **First Light progress** — `first-light.json`  
✅ **Aspirations** — `aspirations/` directory  
✅ **Nautilus database** — `gravity.db` (if exists)

### What Doesn't Need Migration

✅ **Identity files** — Already in correct location  
✅ **Config** — `emergence.json` schema backward compatible  
✅ **Room settings** — No changes to Room structure

### Database Migration Details

#### Schema Changes (v0.3.0 → v0.4.0)

**New columns in `access_log` table:**

```sql
ALTER TABLE access_log ADD COLUMN context TEXT DEFAULT '{}';
```

**Migration handles:**

1. Detecting schema version
2. Adding new columns with defaults
3. Preserving existing data
4. Updating indexes

#### Migration Tool Usage

**Automatic detection and migration:**

```bash
emergence nautilus migrate --auto
```

**Manual migration with options:**

```bash
# Dry run (show what would happen)
emergence nautilus migrate --dry-run

# Migrate with verbose output
emergence nautilus migrate --verbose

# Specify custom paths
emergence nautilus migrate \
  --source /path/to/old/gravity.db \
  --target ~/.openclaw/state/nautilus/gravity.db
```

**Verification:**

```bash
# Check migration success
emergence nautilus migrate --verify

# Expected output:
# ✓ Database schema: v0.4.0
# ✓ All tables present
# ✓ Indexes valid
# ✓ Data integrity: OK
```

### Memory File Migration

**No migration needed!** Memory files stay in place. Nautilus indexes them in the new database.

**To register existing files:**

```bash
# Register all markdown files modified in last 30 days
emergence nautilus register --recent 720

# Register specific directories
emergence nautilus register memory/daily/
emergence nautilus register memory/projects/

# Register individual files
emergence nautilus register memory/MEMORY.md
```

### Drive Data Migration

**No migration needed!** Drive system unchanged in v0.4.0.

**Verify drives after upgrade:**

```bash
emergence drives status
```

Should show all your existing drives with current pressure levels.

---

## Configuration Changes

### New Fields in emergence.json

#### Required Field (for Nautilus to work)

```json
{
  "nautilus": {
    "enabled": true
  }
}
```

#### All Available Options

```json
{
  "nautilus": {
    "enabled": true,
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30,
    "chamber_thresholds": {
      "atrium_max_age_hours": 48,
      "corridor_max_age_days": 7
    },
    "decay_rate": 0.05,
    "recency_half_life_days": 14,
    "authority_boost": 0.3,
    "mass_cap": 100.0
  }
}
```

### Unchanged Sections

These sections remain identical to v0.3.0:

```json
{
  "agent": {
    "name": "YourName",
    "model": "anthropic/claude-sonnet-4-5"
  },
  "drives": {
    "tick_interval": 60,
    "quiet_hours": [23, 7],
    "daemon_mode": false,
    "cooldown_minutes": 30,
    "max_pressure_ratio": 1.5,
    "manual_mode": false,
    "emergency_spawn": true,
    "emergency_threshold": 2.0
  },
  "paths": {
    "workspace": "~/projects/emergence",
    "state": "~/.openclaw/state",
    "identity": "identity"
  }
}
```

### Default Values

If you omit Nautilus config entirely, these defaults apply:

| Setting           | Default                                 |
| ----------------- | --------------------------------------- |
| `enabled`         | `true`                                  |
| `gravity_db`      | `~/.openclaw/state/nautilus/gravity.db` |
| `memory_dir`      | `"memory"`                              |
| `auto_classify`   | `true`                                  |
| `nightly_enabled` | `true`                                  |
| `nightly_hour`    | `2`                                     |
| `decay_rate`      | `0.05`                                  |

### Path Resolution

All paths support:

- `~` expansion → `/Users/you/`
- Relative paths → Resolved from workspace
- Absolute paths → Used as-is

**Examples:**

```json
{
  "nautilus": {
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db", // Absolute
    "memory_dir": "memory" // Relative to workspace
  }
}
```

---

## Testing Your Upgrade

### Smoke Tests

Quick checks to verify everything works:

```bash
# 1. Version check
emergence --version
# Expected: emergence-ai 0.4.0

# 2. Drives working
emergence drives status
# Expected: List of your drives with pressure levels

# 3. Nautilus initialized
emergence nautilus status
# Expected: JSON with phase stats

# 4. Config loaded
emergence config show
# Expected: Your emergence.json contents

# 5. Memory search
emergence nautilus search "test query"
# Expected: Search results (or "no results" if empty database)
```

### Functional Tests

Deeper verification:

#### Test 1: Drive System Unchanged

```bash
# Create a test session
emergence drives satisfy CURIOSITY light

# Check drive pressure decreased
emergence drives status | grep CURIOSITY
```

Expected: Pressure should decrease by ~30%

#### Test 2: Memory Registration

```bash
# Create test file
echo "# Test Memory\n\nThis is a test." > memory/test-migration.md

# Register it
emergence nautilus register memory/test-migration.md

# Search for it
emergence nautilus search "test migration"
```

Expected: File appears in search results

#### Test 3: Chamber Classification

```bash
# Classify chambers
emergence nautilus classify --auto

# Check chamber status
emergence nautilus chambers
```

Expected: Files organized into Atrium/Corridor/Vault

#### Test 4: Gravity Scoring

```bash
# Access a file multiple times
emergence nautilus register memory/MEMORY.md
emergence nautilus search "memory"
emergence nautilus search "memory"

# Check gravity stats
emergence nautilus gravity memory/MEMORY.md
```

Expected: Access count increases, mass score goes up

#### Test 5: Nightly Maintenance

```bash
# Manually trigger nightly maintenance
python3 -m core.nautilus.nightly --verbose

# Check logs
cat ~/.emergence/logs/nautilus-nightly.log
```

Expected: No errors, all steps complete successfully

### Integration Tests

Test Room dashboard integration:

```bash
# Start Room server
cd ~/projects/emergence/room
npm start

# Open browser to http://localhost:3000
# Expected: Nautilus shelf visible in dashboard
```

### Regression Tests

Ensure v0.3.0 features still work:

```bash
# Manual drive satisfaction
emergence drives satisfy CARE moderate

# Dashboard mode toggle
# (Check in emergence.json that manual_mode still works)

# Thresholds
emergence drives status
# Expected: Threshold bands still shown

# Aversive states
# (Check drives with high thwarting still show 🔄 indicator)
```

---

## Rollback Procedure

If you encounter issues and need to revert to v0.3.0:

### Step 1: Stop Daemon (If Running)

```bash
emergence daemon stop
```

### Step 2: Downgrade Package

```bash
pip install emergence-ai==0.3.0
```

### Step 3: Restore Config

```bash
# Restore backup config
cp ~/emergence-backups/v0.3.0-YYYYMMDD/emergence.json ~/projects/emergence/

# Remove Nautilus config section (optional)
# Edit emergence.json and delete "nautilus": { ... } block
```

### Step 4: Restore State Files

```bash
# Restore drive state
cp -r ~/emergence-backups/v0.3.0-YYYYMMDD/state ~/.openclaw/

# Restore memory files
cp -r ~/emergence-backups/v0.3.0-YYYYMMDD/memory ~/projects/emergence/
```

### Step 5: Verify Rollback

```bash
# Check version
emergence --version
# Expected: emergence-ai 0.3.0

# Check drives working
emergence drives status
```

### Step 6: Clean Nautilus Database (Optional)

```bash
# Remove Nautilus database
rm -rf ~/.openclaw/state/nautilus/

# Nautilus commands will fail (expected on v0.3.0)
```

### Rollback Checklist

- [ ] Daemon stopped
- [ ] Package downgraded to v0.3.0
- [ ] Config restored from backup
- [ ] State files restored from backup
- [ ] Version verified: `emergence --version`
- [ ] Drives working: `emergence drives status`
- [ ] Memory files intact

### Data Preservation

**What's safe to keep:**

✅ Nautilus database in `~/.openclaw/state/nautilus/` (won't interfere with v0.3.0)  
✅ Memory files (unchanged)  
✅ Drive state (fully compatible)

**What to remove if issues persist:**

⚠️ `nautilus` section from `emergence.json`  
⚠️ `~/.openclaw/state/nautilus/` directory

### Re-Upgrading After Rollback

If you rolled back and want to try again:

1. Identify and fix the issue that caused rollback
2. Follow [Step-by-Step Upgrade](#step-by-step-upgrade) again
3. Your Nautilus database from first attempt is still there (no need to re-register files)

---

## Troubleshooting

### Common Issues

#### Issue 1: "emergence: command not found" After Upgrade

**Symptom:**

```bash
$ emergence --version
emergence: command not found
```

**Cause:** pip install path not in $PATH

**Solution:**

```bash
# Find where pip installed it
which emergence
# or
pip show emergence-ai | grep Location

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc
```

---

#### Issue 2: Nautilus Commands Fail with "Database Not Found"

**Symptom:**

```bash
$ emergence nautilus status
Error: Database not found at ~/.openclaw/state/nautilus/gravity.db
```

**Cause:** Database not initialized or wrong path

**Solution:**

```bash
# Create directory
mkdir -p ~/.openclaw/state/nautilus

# Initialize database
python3 -m core.nautilus.gravity stats

# Verify
emergence nautilus status
```

---

#### Issue 3: Migration Fails with "Permission Denied"

**Symptom:**

```bash
$ emergence nautilus migrate --auto
Error: Permission denied: ~/.openclaw/state/nautilus/
```

**Cause:** Insufficient permissions

**Solution:**

```bash
# Check ownership
ls -la ~/.openclaw/state/

# Fix permissions
chmod 755 ~/.openclaw/state/
chmod 755 ~/.openclaw/state/nautilus/

# Try again
emergence nautilus migrate --auto
```

---

#### Issue 4: Drives Status Shows "No Drives Found"

**Symptom:**

After upgrade, `emergence drives status` shows empty drives list

**Cause:** State path changed or config pointing to wrong location

**Solution:**

```bash
# Check config paths
emergence config show | grep paths

# Verify state directory exists
ls -la ~/.openclaw/state/

# Check drives.json exists
ls -la ~/.openclaw/state/drives.json

# If missing, restore from backup
cp ~/emergence-backups/v0.3.0-YYYYMMDD/state/drives.json ~/.openclaw/state/
```

---

#### Issue 5: Nightly Maintenance Doesn't Run

**Symptom:**

Nautilus nightly maintenance never executes

**Cause:** Daemon not running or nightly disabled in config

**Solution:**

```bash
# Check daemon status
emergence daemon status

# If not running, start it
emergence daemon start

# Check nightly config
grep -A 3 "nightly" emergence.json

# Ensure enabled:
# "nightly_enabled": true,
# "nightly_hour": 2,
# "nightly_minute": 30

# Manually trigger to test
python3 -m core.nautilus.nightly --verbose
```

---

#### Issue 6: High Memory Usage After Upgrade

**Symptom:**

Emergence process using significantly more RAM

**Cause:** Large memory directory being indexed

**Solution:**

```bash
# Check database size
ls -lh ~/.openclaw/state/nautilus/gravity.db

# If very large (>100MB), consider:

# 1. Limit registration to recent files only
emergence nautilus register --recent 720  # Last 30 days

# 2. Clean old access logs
emergence nautilus prune --older-than 90  # Remove data >90 days

# 3. Adjust decay rate to archive more aggressively
# In emergence.json:
# "decay_rate": 0.10  # 10% instead of 5%
```

---

#### Issue 7: Room Dashboard Doesn't Show Nautilus Shelf

**Symptom:**

Room UI doesn't display Nautilus widget

**Cause:** Frontend not updated or Nautilus disabled

**Solution:**

```bash
# 1. Check Nautilus enabled in config
grep "enabled" emergence.json | grep nautilus
# Should show: "enabled": true

# 2. Rebuild Room frontend
cd ~/projects/emergence/room
npm install
npm run build

# 3. Restart Room server
# Ctrl+C to stop, then:
npm start

# 4. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
```

---

#### Issue 8: "Module not found: core.nautilus" Error

**Symptom:**

```bash
$ emergence nautilus status
ModuleNotFoundError: No module named 'core.nautilus'
```

**Cause:** Incomplete installation or source install not updated

**Solution:**

```bash
# If pip install:
pip install --force-reinstall --no-cache-dir emergence-ai

# If source install:
cd ~/projects/emergence
git pull origin main
git checkout v0.4.0
pip install -e . --force-reinstall

# Verify installation
pip show emergence-ai | grep Version
# Should show: Version: 0.4.0
```

---

### Getting Help

If you encounter issues not covered here:

1. **Check logs:**

   ```bash
   cat ~/.emergence/logs/daemon.log
   cat ~/.emergence/logs/nautilus-nightly.log
   ```

2. **Verify installation:**

   ```bash
   pip show emergence-ai
   emergence --version
   python3 -c "import core.nautilus; print(core.nautilus.__file__)"
   ```

3. **Search existing issues:**
   - [GitHub Issues](https://github.com/jarvis-raven/emergence/issues)
   - Filter by label: `nautilus`, `v0.4.0`

4. **Open a new issue:**
   - Title: `[v0.4.0 Migration] Brief description`
   - Include:
     - Operating system
     - Python version
     - Installation method (pip vs source)
     - Full error message
     - Output of `emergence config show`

5. **Community support:**
   - [Discord](https://discord.gg/emergence-ai) (if available)
   - [Discussions](https://github.com/jarvis-raven/emergence/discussions)

---

## Summary Checklist

Use this checklist to track your migration progress:

### Pre-Migration

- [ ] Read this entire guide
- [ ] Verify Python 3.9+ installed
- [ ] Check current version: `emergence --version` → 0.3.0
- [ ] Backup state directory to `~/emergence-backups/`
- [ ] Backup emergence.json
- [ ] Backup memory files
- [ ] Document any custom configurations

### Migration

- [ ] Upgrade package: `pip install --upgrade emergence-ai`
- [ ] Verify new version: `emergence --version` → 0.4.0
- [ ] Add `nautilus` config section to emergence.json
- [ ] Run database migration (if legacy Nautilus exists)
- [ ] Initialize Nautilus database
- [ ] Register existing memory files
- [ ] Run initial chamber classification
- [ ] Test Nautilus commands

### Post-Migration

- [ ] Run smoke tests (all passing)
- [ ] Verify drives still working
- [ ] Test memory search
- [ ] Check Room dashboard (Nautilus shelf appears)
- [ ] Enable nightly maintenance
- [ ] Archive legacy files (keep backup for 30 days)
- [ ] Update any custom scripts with new paths
- [ ] Document any issues encountered

### Optional Enhancements

- [ ] Configure preferred nightly maintenance time
- [ ] Adjust chamber thresholds for your workflow
- [ ] Set up custom decay rates
- [ ] Explore Nautilus CLI commands
- [ ] Integrate memory search into agent workflows

---

## Additional Resources

### Documentation

- **Nautilus User Guide:** [`docs/nautilus-user-guide.md`](nautilus-user-guide.md)
- **Nautilus API Reference:** [`docs/nautilus-api.md`](nautilus-api.md)
- **Nautilus Troubleshooting:** [`docs/nautilus-troubleshooting.md`](nautilus-troubleshooting.md)
- **Aurora Deployment Guide:** [`docs/aurora-deployment-v0.4.0.md`](aurora-deployment-v0.4.0.md)

### Previous Migration Guides

- **v0.2.x → v0.3.0:** [`MIGRATION.md`](../MIGRATION.md)

### Related Issues & PRs

- **Issue #65:** Session Hooks for Nautilus
- **Issue #66:** Nightly Maintenance Integration
- **Issue #67:** Room Dashboard Widget
- **Issue #68:** CLI Integration
- **Issue #69:** Chamber Promotion Bug Fix
- **Issue #70:** Documentation (#120)
- **PR #118:** Nautilus Core Integration
- **PR #119:** Nautilus Beta Dashboard
- **PR #120:** Comprehensive Documentation

### Example Setups

- **Jarvis (legacy user):** See [`docs/examples/jarvis-v0.4.0-migration.md`](examples/jarvis-v0.4.0-migration.md) (if exists)
- **Aurora (fresh install):** See [`docs/aurora-deployment-v0.4.0.md`](aurora-deployment-v0.4.0.md)

---

## Changelog Summary

### v0.4.0 (February 2026)

**Added:**

- Nautilus memory palace system (4 phases: Gravity, Chambers, Doors, Mirrors)
- Session hooks for automatic memory tracking
- Nightly maintenance daemon integration
- CLI commands: `emergence nautilus [status|search|register|classify|...]`
- Room dashboard Nautilus widget
- Database migration tool
- Comprehensive documentation

**Changed:**

- Database location: `tools/nautilus/` → `~/.openclaw/state/nautilus/`
- Config schema: Added `nautilus` section
- Memory retrieval: Now importance-weighted by default

**Fixed:**

- Chamber promotion bug (#69)
- Access log context tracking
- Path resolution for state directories

**Deprecated:**

- None (v0.3.0 features fully supported)

**Removed:**

- None (backward compatible)

**Security:**

- No security-related changes

---

## Feedback

We value your migration experience! If you:

- ✅ **Successful migration:** Share your story! Open a discussion or tweet with #EmergenceAI
- ⚠️ **Encountered issues:** Open an issue with details so we can improve this guide
- 💡 **Have suggestions:** PR welcome to improve this documentation

**Migration feedback form:** [GitHub Discussions](https://github.com/jarvis-raven/emergence/discussions/new?category=migrations)

---

**Last Updated:** 2026-02-15  
**Guide Version:** 1.0  
**Maintained By:** Emergence Team

---
