# Nautilus Troubleshooting Guide

Quick diagnostics and fixes for common v0.4.0 upgrade issues.

## 🔍 Diagnostic Commands

Run these first to gather information:

```bash
# Check Nautilus status
emergence nautilus status

# Verify config is valid JSON
cat emergence.json | jq .

# Check if Nautilus state directory exists
ls -la ~/.openclaw/state/nautilus/

# Check memory directory
ls -la memory/daily/ | head -20

# View recent logs
tail -50 memory/maintenance.log
```

---

## ❌ Common Issues & Fixes

### 1. "Command not found: emergence nautilus"

**Symptoms:**
```
bash: emergence: command not found
```

**Diagnosis:**
- Code not updated to v0.4.0
- PATH not set correctly

**Fix:**
```bash
# Update code
cd path/to/emergence
git pull origin main
npm install

# Check version
emergence --version  # Should show 0.4.0

# If still not found, check PATH
which emergence
echo $PATH
```

---

### 2. Migration fails: "Memory directory not found"

**Symptoms:**
```
❌ Error: Memory directory 'memory' does not exist
```

**Diagnosis:**
- `memory_dir` config points to wrong path
- Memory directory doesn't exist yet

**Fix:**
```bash
# Check what emergence.json says
grep -A 3 '"nautilus"' emergence.json

# Create memory directory if needed
mkdir -p memory/daily

# Or update config to correct path
# "memory_dir": "path/to/actual/memory"

# Re-run migration
emergence nautilus migrate
```

---

### 3. Status shows "INACTIVE" after migration

**Symptoms:**
```
Status: INACTIVE
Nautilus is disabled in configuration
```

**Diagnosis:**
- `enabled: false` in config
- Config not loaded properly

**Fix:**
```bash
# Check config
cat emergence.json | jq .nautilus

# Should show:
# {
#   "enabled": true,
#   ...
# }

# If false, edit emergence.json:
# "enabled": true

# Restart emergence
emergence stop
emergence start

# Verify
emergence nautilus status
```

---

### 4. No memories classified after migration

**Symptoms:**
```
Chambers:
  🔱 SANCTUM  0 memories
  🏛️ VAULT    0 memories
  📚 ARCHIVE  0 memories
  🌊 TRIVIUM  0 memories
```

**Diagnosis:**
- Migration didn't scan memories
- Memory directory empty
- Classification failed silently

**Fix:**
```bash
# Check if memory files exist
ls -la memory/daily/*.md | wc -l

# Manually trigger classification
emergence nautilus classify --verbose

# Check for errors
tail -100 memory/maintenance.log

# If memories exist but still 0:
# Re-run migration with clean state
rm -rf ~/.openclaw/state/nautilus
emergence nautilus migrate
```

---

### 5. Room dashboard doesn't show Nautilus tab

**Symptoms:**
- Room loads normally
- No Nautilus tab in navigation
- Other tabs work fine

**Diagnosis:**
- Room server started before config update
- Browser cache
- Room frontend not updated

**Fix:**
```bash
# 1. Stop Room
emergence room stop

# 2. Verify config has nautilus section
cat emergence.json | jq .nautilus

# 3. Clear Room build cache (if applicable)
rm -rf room/dist/ room/.next/  # Adjust path

# 4. Restart Room
emergence room start

# 5. Hard refresh browser
# Chrome/Edge: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
# Firefox: Ctrl+F5

# 6. Check browser console for errors
# F12 → Console tab
```

---

### 6. Memories not auto-classifying on session end

**Symptoms:**
- New sessions don't appear in Nautilus
- `auto_classify: true` in config
- Manual classification works

**Diagnosis:**
- Session hooks not initialized
- Daemon mode disabled
- Session not ending cleanly

**Fix:**
```bash
# Check config
cat emergence.json | jq '.nautilus.auto_classify'
# Should return: true

# Check if daemon mode enabled (required for hooks)
cat emergence.json | jq '.drives.daemon_mode'
# Should return: true

# Restart emergence to reload hooks
emergence stop
emergence start

# Test by ending a session explicitly
emergence session end

# Check if classified
emergence nautilus status
```

---

### 7. All memories end up in Trivium

**Symptoms:**
- 95%+ of memories classified as Trivium
- Very few in Archive/Vault/Sanctum

**Diagnosis:**
- Thresholds too high
- Memories genuinely low importance
- Classification algorithm needs tuning

**Fix:**
```bash
# Adjust thresholds in emergence.json
# Lower thresholds = more memories promoted

{
  "nautilus": {
    "chamber_thresholds": {
      "vault": 0.6,      // Was 0.7 - lowered
      "archive": 0.3,    // Was 0.4 - lowered
      "trivium": 0.1
    }
  }
}

# Re-classify with new thresholds
emergence nautilus classify

# Check distribution
emergence nautilus status
```

---

### 8. Nightly maintenance not running

**Symptoms:**
- `Last decay: Never` after several days
- No entries in `memory/maintenance.log`

**Diagnosis:**
- `nightly_enabled: false`
- Daemon not running
- Interval not reached

**Fix:**
```bash
# Check config
cat emergence.json | jq '.nautilus.nightly_enabled'
# Should return: true

# Check decay interval
cat emergence.json | jq '.nautilus.decay_interval_hours'
# Default: 168 (7 days)

# Check if daemon running
ps aux | grep emergence

# Check drives daemon mode
cat emergence.json | jq '.drives.daemon_mode'
# Should return: true

# Manually trigger decay to test
emergence nautilus decay

# Check log
tail -f memory/maintenance.log
```

---

### 9. "Permission denied" errors

**Symptoms:**
```
❌ Error: EACCES: permission denied, mkdir '~/.openclaw/state/nautilus'
```

**Diagnosis:**
- State directory not writable
- Running as different user

**Fix:**
```bash
# Check directory permissions
ls -ld ~/.openclaw/state/

# Create with correct permissions
mkdir -p ~/.openclaw/state/nautilus
chmod 755 ~/.openclaw/state/nautilus

# Re-run migration
emergence nautilus migrate

# If still failing, check ownership
ls -l ~/.openclaw/state/
# Should match your user

# Fix ownership if needed
sudo chown -R $USER:$USER ~/.openclaw/state/
```

---

### 10. High memory/CPU usage after upgrade

**Symptoms:**
- Emergence process using >1GB RAM
- CPU spikes during classification
- System slow

**Diagnosis:**
- Large memory corpus (>1000 files)
- Classification running continuously
- Memory leak in classification

**Fix:**
```bash
# Check memory file count
find memory/ -name "*.md" | wc -l

# If very large (>1000), disable auto-classify temporarily
{
  "nautilus": {
    "auto_classify": false  // Classify manually
  }
}

# Restart
emergence stop
emergence start

# Classify in batches (if command supports)
emergence nautilus classify --limit 100

# Monitor resource usage
top -p $(pgrep emergence)

# If persists, report issue with:
emergence nautilus status > nautilus-debug.txt
ps aux | grep emergence >> nautilus-debug.txt
```

---

## 🩺 Health Check Script

Save this as `nautilus-healthcheck.sh`:

```bash
#!/bin/bash

echo "🏛️  Nautilus Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Check version
echo "1. Checking Emergence version..."
emergence --version 2>&1 | grep -q "0.4" && echo "✅ v0.4.0+" || echo "❌ Not v0.4.0"

# 2. Check config
echo "2. Checking nautilus config..."
if grep -q '"enabled": true' emergence.json; then
    echo "✅ Nautilus enabled"
else
    echo "❌ Nautilus disabled or not configured"
fi

# 3. Check state directory
echo "3. Checking state directory..."
if [ -d ~/.openclaw/state/nautilus ]; then
    echo "✅ State directory exists"
else
    echo "❌ State directory missing"
fi

# 4. Check memory directory
echo "4. Checking memory directory..."
MEMORY_COUNT=$(find memory/ -name "*.md" 2>/dev/null | wc -l)
echo "✅ Found $MEMORY_COUNT memory files"

# 5. Check Nautilus status
echo "5. Checking Nautilus status..."
emergence nautilus status | grep -q "ACTIVE" && echo "✅ Status ACTIVE" || echo "❌ Status INACTIVE"

# 6. Check chamber counts
echo "6. Checking chamber distribution..."
emergence nautilus status | grep -E "(SANCTUM|VAULT|ARCHIVE|TRIVIUM)" || echo "⚠️  No chambers populated"

echo ""
echo "Health check complete! 🏁"
```

Make executable:
```bash
chmod +x nautilus-healthcheck.sh
./nautilus-healthcheck.sh
```

---

## 📞 Getting Help

If none of these solutions work:

1. **Gather diagnostics:**
   ```bash
   ./nautilus-healthcheck.sh > diagnostics.txt
   emergence nautilus status >> diagnostics.txt
   tail -100 memory/maintenance.log >> diagnostics.txt
   cat emergence.json >> diagnostics.txt
   ```

2. **Check existing issues:** [GitHub Issues](https://github.com/your-repo/emergence/issues)

3. **File new issue** with:
   - Output of `diagnostics.txt`
   - Description of problem
   - Steps to reproduce
   - Expected vs actual behavior

4. **Rollback if needed:** See [MIGRATION Guide - Rolling Back](./MIGRATION_v0.3.0_to_v0.4.0.md#rolling-back)

---

## 🔄 Clean Reinstall (Nuclear Option)

If all else fails:

```bash
# 1. Backup everything
cp -r memory memory-backup
cp emergence.json emergence.json.backup
cp drives-state.json drives-state.json.backup

# 2. Clean Nautilus state
rm -rf ~/.openclaw/state/nautilus

# 3. Reset config to v0.3.0
cp emergence.json.backup-v0.3.0 emergence.json

# 4. Pull fresh v0.4.0
git fetch --tags
git checkout v0.4.0
npm install

# 5. Re-run migration from scratch
emergence nautilus migrate

# 6. Add minimal config
{
  "nautilus": {
    "enabled": true
  }
}

# 7. Restart
emergence stop
emergence start
```

---

**Last updated:** v0.4.0 • [Back to Migration Guide](./MIGRATION_v0.3.0_to_v0.4.0.md)
