# Nautilus Memory Palace - Human README

**What it is:** A four-phase system that makes my memory searchable, organized, and compressed over time.

**Why it matters:** Instead of forgetting everything between sessions, I build a persistent memory that gets smarter as I use it.

---

## How It Works (The Simple Version)

Think of Nautilus like a library that:
1. **Tracks what I read** (Gravity)
2. **Organizes by age** (Chambers: atrium/corridor/vault)
3. **Tags by topic** (Doors: emergence, personal, technical, etc.)
4. **Links related memories** (Mirrors: same event across different files)

### Phase 1: Gravity (Importance Scoring)

**What it does:**
- Tracks every file I access
- Counts reads, writes, references
- Scores importance based on usage patterns

**When it happens:**
- Automatically when I read/write files through OpenClaw
- Manual: `emergence nautilus gravity record-access <file>`

**What you see:**
- "Total chunks: 28" in Room
- Files I use frequently score higher

**What you do:** Nothing. Just use OpenClaw normally.

---

### Phase 2: Chambers (Temporal Organization)

**What it does:**
- **Atrium** (< 48h): Recent, full-detail memories
- **Corridor** (2-7 days): Medium-term, daily summaries
- **Vault** (> 7 days): Long-term, distilled lessons

**When it happens:**
- Auto-classification: Files sorted by age
- Promotion: Creates summaries, moves old content to vault
- Runs nightly (if enabled) or manually

**What you see in Room:**
- Atrium: 0 files
- Corridor: 26 files  
- Vault: 0 files (none promoted yet)

**What you do:**
- **Weekly:** Run `emergence nautilus chambers promote` to create summaries
- Or enable nightly cron: I'll do it automatically
- Check Room to see the distribution

**Example promotion:**
```
Daily log from 7 days ago → compressed summary → vault
Original file marked "superseded"
Summary kept in corridor for quick access
```

---

### Phase 3: Doors (Context Tagging)

**What it does:**
- Tags files by topic (emergence, personal, creative, etc.)
- Filters search results: "Show me creative memories"
- Makes connections across different contexts

**When it happens:**
- Manual tagging: You tag important files
- Auto-tagging: Llama3.2 reads files and suggests tags (optional)
- Runs during nightly maintenance

**What you see in Room:**
- Door Coverage: 28/28 files (100%)
- Each file has 1-5 tags

**What you do:**
- **Let auto-tagging run:** Already set up, tags new files overnight
- **Manual tags:** `emergence nautilus doors tag <file> emergence development`
- **Search by context:** `emergence nautilus search "project" --context emergence`

---

### Phase 4: Mirrors (Multi-Granularity Links)

**What it does:**
- Links the same event across different files
- Example: "v0.4.0 release" appears in:
  - Raw daily log (2026-02-15.md)
  - Weekly summary (corridor-week-7.md)
  - Monthly lesson (vault-feb-2026.md)

**When it happens:**
- Auto-linking during nightly maintenance
- Looks for common themes, dates, keywords

**What you see in Room:**
- Mirror Coverage: 0% (not populated yet)
- Event links between raw/summary/lesson files

**What you do:**
- Nothing manual needed
- Happens automatically as summaries are created

---

## Daily Workflow (What You Need to Do)

### Automatic (No Action Needed)
✅ **File access tracking** - happens when I use OpenClaw  
✅ **Chamber classification** - files auto-sorted by age  
✅ **Auto-tagging** - llama3.2 tags new files overnight

### Weekly (5 minutes)
📅 **Chamber promotion** - Run once a week to create summaries:
```bash
emergence nautilus chambers promote
```

This creates weekly summaries from daily logs, keeps memory lean.

### Optional (For Power Users)
🔧 **Enable nightly cron** - I'll do everything automatically:
```bash
# Edit ~/.openclaw/workspace/emergence.json
"nautilus": {
  "enabled": true,
  "nightly_maintenance": true
}
```

Then in OpenClaw cron, add:
```json
{
  "schedule": {"kind": "cron", "expr": "0 3 * * *"},
  "payload": {"kind": "systemEvent", "text": "Run nightly Nautilus maintenance"},
  "sessionTarget": "main"
}
```

---

## How to Check It's Working

### Room Dashboard
1. Open Room (http://jarviss-mac-mini.tail869e96.ts.net or localhost:3000)
2. Click "Nautilus" tab
3. Check:
   - **Gravity**: Growing chunk count = I'm accessing files
   - **Chambers**: Distribution across atrium/corridor/vault
   - **Doors**: Coverage % increasing = more files tagged
   - **Mirrors**: Links forming as summaries created

### Command Line
```bash
# Full status
emergence nautilus status

# Just chamber distribution
emergence nautilus chambers status

# Run maintenance manually
emergence nautilus maintain --register-recent
```

---

## What "Good" Looks Like

After a few weeks of use:

**Gravity:**
- 200-500 chunks tracked
- Top files are the ones you actually care about
- DB size: 500KB - 2MB

**Chambers:**
- Atrium: 5-10 files (last 2 days)
- Corridor: 50-100 files (last week's summaries)
- Vault: 20-50 files (distilled long-term knowledge)

**Doors:**
- 80%+ coverage (most files tagged)
- 5-10 common tags (emergence, personal, technical, creative...)
- Context filtering speeds up search

**Mirrors:**
- 30-50% of events linked across granularities
- Important events reflected in multiple summaries

---

## Troubleshooting

### "Chamber distribution is all 0s"
- Run: `emergence nautilus chambers classify`
- This sorts files by age into atrium/corridor/vault

### "Door coverage is 0%"
- Auto-tagging hasn't run yet
- Manual: `emergence nautilus doors auto-tag`
- Or wait for nightly maintenance

### "Gravity shows 0 accesses"
- Normal! Accesses only count when I *search* memories
- Writes are tracked (that's why chunks exist)
- Use `emergence nautilus search` to build access patterns

### "Everything is in corridor, nothing in vault"
- Haven't run chamber promotion yet
- Run: `emergence nautilus chambers promote`
- Or enable nightly cron

---

## The Big Picture

**Nautilus learns what matters by watching what I use.**

- Files I access frequently → higher gravity scores
- Recent work stays in atrium (fast access)
- Old daily logs → compressed into corridor summaries
- Really old stuff → distilled into vault lessons
- Tags help find memories by topic
- Mirrors connect the same event across time scales

**You don't have to manage it.** Just:
1. Use OpenClaw normally (I track what you access)
2. Run weekly promotion (or enable nightly cron)
3. Check Room occasionally to see the memory palace grow

**Result:** I remember more, search faster, and keep only what matters.

---

## Quick Reference

| Phase | Purpose | Auto/Manual | Frequency |
|-------|---------|-------------|-----------|
| Gravity | Track importance | Auto | Every file access |
| Chambers | Organize by age | Auto classify, manual promote | Daily classify, weekly promote |
| Doors | Tag by topic | Auto-tag (llama3.2) | Nightly or manual |
| Mirrors | Link across time | Auto | Nightly or manual |

**One command to do everything:**
```bash
emergence nautilus maintain --register-recent
```

Run weekly, or set up nightly cron, and forget about it.

---

**Questions?** Ask me in OpenClaw. I'm learning how this works too. 🐚
