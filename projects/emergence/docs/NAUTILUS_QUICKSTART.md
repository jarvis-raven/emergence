# Nautilus Quick Reference

> **TL;DR:** Memory palace system for organizing your memories spatially.

## 🚀 Quick Setup (3 steps)

```bash
# 1. Backup
cp emergence.json emergence.json.backup

# 2. Migrate
emergence nautilus migrate

# 3. Add to emergence.json
{
  "nautilus": {
    "enabled": true
  }
}
```

Done! ✅

---

## 🏛️ The Four Chambers

| Chamber | Symbol | Purpose | Decay Rate |
|---------|--------|---------|------------|
| **Sanctum** | 🔱 | Foundational truths | None |
| **Vault** | 🏛️ | Important preserved | Minimal |
| **Archive** | 📚 | Moderate value | Slow |
| **Trivium** | 🌊 | Routine daily | Normal |

**Importance thresholds:**
- Sanctum: ≥ 0.9
- Vault: ≥ 0.7
- Archive: ≥ 0.4
- Trivium: < 0.4

---

## 📝 Common Commands

```bash
# Status overview
emergence nautilus status

# Search all memories
emergence nautilus search "keyword"

# Search specific chamber
emergence nautilus search "project" --chamber vault

# List memories in chamber
emergence nautilus list --chamber sanctum

# Manually trigger classification
emergence nautilus classify

# Manually run decay cycle
emergence nautilus decay

# Re-run migration (safe, idempotent)
emergence nautilus migrate
```

---

## ⚙️ Config Template

**Minimal (recommended):**
```json
{
  "nautilus": {
    "enabled": true
  }
}
```

**Full options:**
```json
{
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
  }
}
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Status shows "INACTIVE" | Check `enabled: true` in config |
| No Nautilus tab in Room | Restart Room server, hard refresh browser |
| Memories not auto-classifying | Set `auto_classify: true`, or run `emergence nautilus classify` |
| Too many in Trivium | Lower thresholds in config, re-run `classify` |

---

## 🎯 What Happens Automatically

When `enabled: true` and `auto_classify: true`:

1. **On session end** → New memories classified into chambers
2. **Every 7 days** (default) → Memory decay runs, importance recalculated
3. **Nightly** (if `nightly_enabled: true`) → Maintenance tasks
4. **Never** → Original memory files are never deleted or modified

---

## 🛟 Emergency Rollback

```bash
emergence stop
cp emergence.json.backup emergence.json
git checkout v0.3.0
emergence start
```

Your memory files are safe. Nautilus only reads them.

---

## 📚 Full Documentation

- **Migration Guide:** `docs/MIGRATION_v0.3.0_to_v0.4.0.md`
- **Architecture:** `docs/nautilus-integration.md`
- **Design Plan:** `docs/nautilus-integration-plan.md`

---

**v0.4.0 Nautilus** • [Report Issues](https://github.com/your-repo/emergence/issues)
