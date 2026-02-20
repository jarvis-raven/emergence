# Migration Guide: v0.3.0 → v0.4.0 (Nautilus)

**Release:** v0.4.0 "Nautilus"  
**Date:** February 2026  
**Breaking Changes:** None (backward compatible)

## Overview

Version 0.4.0 introduces **Nautilus**, a memory palace system that organizes your memories into chambers based on emotional resonance and importance. This is a **non-breaking upgrade** — your existing setup will continue to work.

### What's New

- 🏛️ **Nautilus Memory Palace** — Spatial memory organization with chambers (Trivium, Archive, Vault, Sanctum)
- 🔄 **Session Hooks** — Automatic recording of sessions to memory
- 🌙 **Nightly Maintenance** — Automated memory decay and consolidation
- 📊 **Room Dashboard Widget** — New Nautilus tab in your Room dashboard
- 🛠️ **CLI Commands** — `emergence nautilus` for memory exploration

---

## Pre-Migration Checklist

Before upgrading, back up your critical files:

### 1. Backup Configuration

```bash
# Backup your emergence.json
cp emergence.json emergence.json.backup-v0.3.0

# Optional: backup with timestamp
cp emergence.json "emergence.json.backup-$(date +%Y%m%d-%H%M%S)"
```

### 2. Backup Drives State

```bash
# If you have drives-state.json
cp drives-state.json drives-state.json.backup
```

### 3. Backup Memory Files

```bash
# Create a snapshot of your memory directory
tar -czf memory-backup-v0.3.0.tar.gz memory/

# Or copy the entire directory
cp -r memory memory-backup-v0.3.0
```

✅ **Verification:** Confirm backups exist:
```bash
ls -lh *.backup* memory-backup-v0.3.0.tar.gz
```

---

## Migration Steps

### Step 1: Update Code

```bash
# Navigate to your Emergence installation
cd path/to/emergence

# Pull the latest changes
git pull origin main

# Install any new dependencies
npm install
# or
pnpm install
```

### Step 2: Run Migration

Emergence v0.4.0 includes an automatic migration tool:

```bash
# Run the Nautilus migration
emergence nautilus migrate
```

**What this does:**
- Scans your existing `memory/` directory
- Classifies memories into Nautilus chambers
- Creates `~/.openclaw/state/nautilus/` directory structure
- Preserves all original memory files (read-only operation)

**Expected output:**
```
🏛️  Nautilus Migration v0.3.0 → v0.4.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Scanning memory directory...
✓ Found 47 memory files
✓ Classifying memories...
  ├─ Trivium: 12 memories
  ├─ Archive: 28 memories
  ├─ Vault: 5 memories
  └─ Sanctum: 2 memories
✓ Writing Nautilus state...
✓ Migration complete!

Next: Add Nautilus configuration to emergence.json
```

### Step 3: Update Configuration

Add the `nautilus` section to your `emergence.json`:

#### Minimal Configuration (recommended for first-time setup)

```json
{
  "name": "emergence",
  "version": "0.4.0",
  "workspace": "/your/workspace/path",
  
  "nautilus": {
    "enabled": true
  },
  
  "drives": { ... },
  "memory": { ... },
  "room": { ... }
}
```

#### Full Configuration (with all options)

```json
{
  "name": "emergence",
  "version": "0.4.0",
  "workspace": "/your/workspace/path",
  
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168,
    "nightly_enabled": true,
    "chamber_thresholds": {
      "vault": 0.7,
      "archive": 0.4,
      "trivium": 0.1
    }
  },
  
  "drives": { ... },
  "memory": { ... },
  "room": { ... }
}
```

#### Configuration Options Explained

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `false` | Enable/disable Nautilus system |
| `state_dir` | `~/.openclaw/state/nautilus` | Where Nautilus stores chamber metadata |
| `memory_dir` | `memory` | Path to your memory files (relative to workspace) |
| `auto_classify` | `true` | Automatically classify new memories on session end |
| `decay_interval_hours` | `168` (7 days) | How often to run memory decay (in hours) |
| `nightly_enabled` | `true` | Enable nightly maintenance tasks |
| `chamber_thresholds` | See below | Importance thresholds for each chamber |

**Chamber Thresholds:**
- `sanctum`: ≥ 0.9 (highest importance, foundational memories)
- `vault`: ≥ 0.7 (important, preserved indefinitely)
- `archive`: ≥ 0.4 (moderate importance, slow decay)
- `trivium`: < 0.4 (routine, faster decay)

### Step 4: Verify Installation

Run the Nautilus status check:

```bash
emergence nautilus status
```

**Expected output:**
```
🏛️  Nautilus Memory Palace Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ACTIVE
State Directory: /Users/you/.openclaw/state/nautilus
Memory Directory: /Users/you/.openclaw/workspace/memory

Chambers:
  🔱 SANCTUM  ████████████████████ 2 memories (foundational)
  🏛️ VAULT    ████████░░░░░░░░░░░░ 5 memories (preserved)
  📚 ARCHIVE  ██████░░░░░░░░░░░░░░ 28 memories (slow decay)
  🌊 TRIVIUM  ███░░░░░░░░░░░░░░░░░ 12 memories (routine)

Total memories: 47
Auto-classify: ENABLED
Nightly maintenance: ENABLED (every 168 hours)
Last decay: Never (first run)
```

### Step 5: Test Memory Search

Test that Nautilus can search your memories:

```bash
# Search for a keyword
emergence nautilus search "test"

# Search with chamber filter
emergence nautilus search "project" --chamber vault

# List all memories in a chamber
emergence nautilus list --chamber sanctum
```

### Step 6: Verify Room Dashboard

If you use the Room dashboard:

1. Start the Room server:
   ```bash
   emergence room start
   ```

2. Open your browser to `http://localhost:8801` (or your configured port)

3. Look for the new **Nautilus** tab in the navigation

4. Verify you can see:
   - Chamber overview with memory counts
   - Memory decay timeline
   - Search interface

---

## Post-Migration: What's Different?

### Session Recording

Sessions are now automatically recorded to memory when they end:

- **Where:** `memory/daily/YYYY-MM-DD.md` (as before)
- **When:** On session exit or explicit save
- **Classification:** Happens automatically if `auto_classify: true`

### Nightly Maintenance

If `nightly_enabled: true`, Emergence will:

- Run memory decay every `decay_interval_hours` (default: 7 days)
- Move memories between chambers based on changing importance
- Clean up stale temporary files
- Log maintenance activity to `memory/maintenance.log`

**To disable:** Set `nightly_enabled: false` in config.

### CLI Changes

New commands available:

```bash
emergence nautilus status        # Chamber overview
emergence nautilus search <q>    # Search memories
emergence nautilus list          # List all memories
emergence nautilus classify      # Manually re-classify all memories
emergence nautilus decay         # Manually trigger decay cycle
emergence nautilus migrate       # Run migration (idempotent)
```

Existing commands work unchanged.

---

## Troubleshooting

### Issue: Migration fails with "memory directory not found"

**Cause:** `memory_dir` in config doesn't exist or path is wrong.

**Fix:**
```bash
# Create the memory directory
mkdir -p memory/daily

# Or update emergence.json to point to correct path
# "memory_dir": "path/to/your/memory"
```

---

### Issue: `emergence nautilus status` shows "INACTIVE"

**Cause:** `nautilus.enabled` is `false` or migration didn't run.

**Fix:**
```bash
# 1. Check your emergence.json
grep -A 5 '"nautilus"' emergence.json

# 2. Ensure enabled: true
# 3. Re-run migration if needed
emergence nautilus migrate
```

---

### Issue: Room dashboard doesn't show Nautilus tab

**Cause:** Room server started before config update, or browser cache.

**Fix:**
```bash
# 1. Restart the Room server
emergence room stop
emergence room start

# 2. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)

# 3. Check Room config has port and host set
grep -A 5 '"room"' emergence.json
```

---

### Issue: Memories not being auto-classified

**Cause:** `auto_classify: false` or session hooks not initialized.

**Fix:**
```bash
# 1. Check config
grep 'auto_classify' emergence.json

# 2. Set to true if needed
# 3. Manually classify existing memories
emergence nautilus classify

# 4. Future sessions will auto-classify
```

---

### Issue: Too many memories in Trivium

**Cause:** Threshold too low, or memories genuinely routine.

**Fix:**
Adjust thresholds in `emergence.json`:

```json
"chamber_thresholds": {
  "vault": 0.6,      // Lower to promote more to Vault
  "archive": 0.3,    // Lower to promote more to Archive
  "trivium": 0.1
}
```

Then re-classify:
```bash
emergence nautilus classify
```

---

### Issue: Nightly maintenance not running

**Cause:** Daemon mode disabled, or `nightly_enabled: false`.

**Fix:**
```bash
# 1. Check drives config
grep -A 2 'daemon_mode' emergence.json
# Should be: "daemon_mode": true

# 2. Check nautilus config
grep 'nightly_enabled' emergence.json
# Should be: "nightly_enabled": true

# 3. Restart emergence
emergence stop
emergence start
```

---

## Rolling Back

If you need to revert to v0.3.0:

### 1. Stop Emergence

```bash
emergence stop
```

### 2. Restore Configuration

```bash
# Restore old config
cp emergence.json.backup-v0.3.0 emergence.json
```

### 3. Revert Code

```bash
# Check out v0.3.0 tag
git checkout v0.3.0

# Reinstall dependencies (if needed)
npm install
```

### 4. (Optional) Remove Nautilus State

```bash
# Nautilus state is separate from your memories
# Removing it won't affect your original memory files
rm -rf ~/.openclaw/state/nautilus
```

### 5. Restart

```bash
emergence start
```

**Note:** Your original memory files in `memory/` are never modified by Nautilus. Rollback is safe.

---

## FAQ

### Q: Will Nautilus delete my old memories?

**A:** No. Memory decay reduces *importance scores* but never deletes files. Memories can move between chambers, but files remain intact.

### Q: Can I disable Nautilus after migrating?

**A:** Yes. Set `"nautilus": { "enabled": false }` in `emergence.json`. Your memories remain in place.

### Q: Do I need to re-classify memories manually?

**A:** No. `auto_classify: true` (default) classifies new memories automatically. Existing memories are classified during migration.

### Q: How much disk space does Nautilus use?

**A:** Minimal. Nautilus stores metadata (~10-100 KB per memory) in `state_dir`. Your actual memory files are unchanged.

### Q: Can I customize chamber names?

**A:** Not in v0.4.0. Chamber names (Trivium, Archive, Vault, Sanctum) are fixed. Future versions may allow customization.

### Q: What if I don't want nightly maintenance?

**A:** Set `"nightly_enabled": false`. You can still manually trigger decay with `emergence nautilus decay`.

### Q: Does Nautilus work without the Room dashboard?

**A:** Yes. Nautilus is fully functional via CLI. The Room widget is optional.

---

## What's Next?

After successful migration:

1. **Explore your memory palace:**
   ```bash
   emergence nautilus search "your recent project"
   ```

2. **Check the Room dashboard** to visualize your chambers

3. **Let it run** for a few days to see auto-classification in action

4. **Review chamber distribution** — adjust thresholds if needed

5. **Read the docs:**
   - `docs/nautilus-integration.md` — Deep dive into Nautilus architecture
   - `docs/nautilus-integration-plan.md` — Design rationale

---

## Support

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -f memory/maintenance.log
   emergence logs
   ```

2. **Run diagnostics:**
   ```bash
   emergence nautilus status
   emergence doctor  # If available
   ```

3. **File an issue:** [GitHub Issues](https://github.com/your-repo/emergence/issues)

4. **Revert if needed:** See "Rolling Back" section above

---

## Changelog Summary

### Added
- Nautilus memory palace system with 4 chambers
- `emergence nautilus` CLI commands
- Auto-classification on session end
- Nightly maintenance daemon
- Room dashboard Nautilus widget
- Memory decay mechanism
- Chamber-based memory organization

### Changed
- Session hooks now record to Nautilus (when enabled)
- `emergence.json` schema extended with `nautilus` section

### Fixed
- N/A (new feature release)

### Deprecated
- None

### Removed
- None

### Security
- Nautilus operates read-only on memory files
- State stored separately in `~/.openclaw/state/nautilus`

---

**Version 0.4.0 "Nautilus" — Safe Travels Through Your Memory Palace** 🏛️
