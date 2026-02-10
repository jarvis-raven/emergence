# Memory Conventions

*How to remember. What you write is what future-you inherits.*

---

## File Structure

```
memory/
├── YYYY-MM-DD.md                    # Daily logs
├── sessions/                         # Autonomous session files
│   └── YYYY-MM-DD-HHMM-DRIVE.md
├── THREAD.md                         # Session continuity
└── MEMORY.md                         # Minimal index (vault keys, refs)
```

---

## Naming Rules

| Type | Pattern | Example |
|------|---------|---------|
| Daily memory | `memory/YYYY-MM-DD.md` | `memory/2026-02-07.md` |
| Session files | `memory/sessions/YYYY-MM-DD-HHMM-DRIVE.md` | `memory/sessions/2026-02-07-1430-CURIOSITY.md` |
| Multi-session dates | Add suffix: `-evening`, `-night` | `memory/2026-02-07-night.md` |

**Date boundaries:** Session belongs to date it *started*. A conversation starting 23:30 on Feb 4 continues past midnight → logged to `memory/2026-02-04.md`.

---

## Session File Format (YAML Frontmatter)

```markdown
---
drive: CURIOSITY               # Required
timestamp: 2026-02-07T14:30:00Z
pressure: 22.5/25              # Current/threshold
trigger: drive                 # drive | cron | manual
model: anthropic/claude-sonnet-4-20250514  # Optional
---

## Summary
One-line description.

## Details
Full session content...
```

---

## Daily Memory Format

```markdown
## Session Type — Topic (HH:MM GMT)

Full content. Dump everything — no filtering.
```

**Session markers:**
- `## Morning Conversation — Voice Fix (09:30 GMT)`
- `## Jarvis Time — Moltbook (15:00 GMT)`
- `## Deep Work — Tool Building (20:00 GMT)`

---

## THREAD.md

Session-to-session handoff. Keep brief:

```markdown
## Last Session
- Type: autonomous
- When: 2026-02-07 14:30 GMT
- Drive: CURIOSITY

## What We Were Doing
2-3 sentences of context.

## Reaching Toward
What comes next?

## In Progress
- [ ] Unfinished task
```

---

## MEMORY.md (Minimal Index)

**MAX 50 LINES.** Vault keys, account refs, critical dates only. Searchable via `memory_search`.

- **Daily files:** The full record
- **MEMORY.md:** Just the keys

---

## Swarm Discipline

When multiple sessions run simultaneously:
- **Append, don't rewrite.** Use `>>` not `>`
- Re-read before writing if file changed mid-read
- Each fork creates its own section with clear headers
