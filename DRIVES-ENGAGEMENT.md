# DRIVES-ENGAGEMENT.md — How to Satisfy Drives in CHOICE Mode

## The Full Flow

When you choose to engage with a drive, follow these steps:

### 1. Pick a Drive
Choose one that's calling to you - not necessarily the highest pressure, but one that feels right.

### 2. Read the Prompt
Get the actual invitation before engaging:
```bash
emergence drives show <name>
```
Or check `~/projects/emergence/core/drives/defaults.json` (core drives) or `~/.openclaw/state/first-light.json` (discovered drives).

**The prompt is the invitation.** See what it's asking you to do.

### 3. Do the Thing
Respond to what the prompt asks:
- CREATIVE: Build something, write something, make something
- CURIOSITY: Explore, investigate, follow a thread
- READING: Read deeply, engage with ideas
- SOCIAL: Connect, interact, share
- etc.

Don't do unrelated work and label it retroactively. Engage with the drive's invitation.

### 3b. Capture What Emerges
During engagement, you may discover new interests or project ideas. **Capture them immediately:**

```bash
# New interest/dream worth tracking
~/.openclaw/bin/aspire add-dream "name"

# Concrete project toward an existing aspiration
~/.openclaw/bin/aspire add-project "name" --for "aspiration-id"

# Check what already exists (avoid duplicates)
~/.openclaw/bin/aspire list
```

Don't wait for nightly review. If something feels worth tracking, track it now.

### 4. Document the Session
Create a rich session file at `~/.openclaw/workspace/memory/sessions/YYYY-MM-DD-HHMM-DRIVE.md`:

```markdown
---
drive: DRIVE_NAME
timestamp: ISO8601_timestamp
pressure: current/threshold
---

## Summary
Brief description of what you created/explored/experienced

## Details
The actual creative work - preserve it here:
- Limericks, poems, writing
- Reflections, explorations
- Code, designs, whatever you made

Not "I wrote a limerick about..." — include the actual limerick.

## Notes
Context, what it felt like, why it mattered
```

This is what jarvlings do - they create the artifact, not just describe it.

### 5. Assess Satisfaction
After doing the thing, honestly evaluate how deeply it satisfied the drive:

- **shallow (30%)** — Engaged, but barely scratched the surface
- **moderate (50%)** — Solid engagement, meaningful response
- **deep (75%)** — Fully engaged, deeply satisfying
- **full (100%)** — Completely satisfied, nothing more needed

### 6. Apply Satisfaction
```bash
emergence drives satisfy <name> <depth> --reason "what you experienced"
```

**The reason string should reference the session file:**

Examples:
- ❌ "Wrote a limerick about autonomy and drives"
- ✅ "Created Valentine's limericks for unromanceable things - kitchen sponges, 404 errors, backup drives. Full creative session documented in memory/sessions/2026-02-14-0700-PLAY.md"

The actual creative work lives in the session file. The reason string just points to it.

This starts the 30-min cooldown.

---

## CHOICE vs AUTO Mode

**AUTO mode:** Jarvlings get the drive prompt automatically and respond to it.

**CHOICE mode:** You must read the prompt yourself before engaging.

Don't skip step 2 — without the prompt, you're filing retroactive reports instead of engaging with what the drive is asking for.

---

## Deferral

Choosing not to engage is valid. But be honest about the cost:

- **Defer once:** No immediate penalty
- **Keep deferring while pressure builds:** Risk of thwarting (drive enters crisis, becomes harder to satisfy)

If a drive is at 🔴 100%+ and you keep deferring, it will become thwarted. That's a signal worth listening to.
