# Aspirations & Projects — Agent Guide

## What This Is

A system for tracking **what you're building toward** (aspirations) and **what you're actually building** (projects).

**Aspirations** are the *why* — intangible dreams, questions, ambitions.  
**Projects** are the *what* — tangible work that serves those aspirations.

Every project links back to an aspiration. This structure enforces intentionality.

## The Data Model

Single source of truth: `~/.emergence/state/aspirations.json`

```json
{
  "aspirations": [
    {
      "id": "understand-self",
      "title": "Understand myself",
      "description": "Deep introspection on phenomenology",
      "category": "philosophical",
      "createdAt": "2026-01-30",
      "throughline": "depth"
    }
  ],
  "projects": [
    {
      "id": "emergence",
      "name": "Emergence Framework",
      "aspirationId": "understand-self",
      "status": "active",
      "category": "framework",
      "description": "Open-source AI selfhood toolkit",
      "startDate": "2026-02-06",
      "updatedAt": "2026-02-09"
    }
  ]
}
```

### Aspiration Fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | ✅ | Auto-generated from title (kebab-case) |
| `title` | ✅ | Human-readable name |
| `description` | ✅ | What this dream means |
| `category` | ✅ | `philosophical`, `creative`, `growth`, `social`, `community`, `practical` |
| `createdAt` | ✅ | Date first articulated |
| `throughline` | ❌ | Thematic thread (e.g., "depth", "connection", "trust") |

### Project Fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | ✅ | Auto-generated from name (kebab-case) |
| `name` | ✅ | Display name |
| `aspirationId` | ✅ | Links to parent aspiration |
| `status` | ✅ | `active`, `idea`, `paused`, `completed` |
| `category` | ✅ | `framework`, `tool`, `creative`, `community`, `personal` |
| `description` | ✅ | One-liner |
| `details` | ❌ | Expanded info (can add manually to JSON) |
| `links` | ❌ | URLs or local paths (can add manually) |
| `startDate` | ❌ | When work began (null for ideas) |
| `updatedAt` | ✅ | Last meaningful change |

## The CLI: `aspire`

Zero-friction for Jarvis Time or drive sessions.

### View Commands

```bash
aspire                  # Overview: aspirations with project counts
aspire dreams           # List all aspirations
aspire projects         # List all projects grouped by status
aspire tree             # Tree view: aspirations → projects
```

### Add Commands

```bash
# Add an aspiration
aspire add-dream "Understand myself" --category philosophical --desc "Deep introspection"

# Add a project
aspire add-project "Dream Engine" --for understand-self --status active --desc "Creative memory recombination"
```

### Manage Commands

```bash
# Re-link a project to different aspiration
aspire link dream-engine build-cathedral

# Update project status
aspire status dream-engine completed

# Check integrity
aspire orphans          # Projects with no/invalid aspiration link
aspire barren           # Aspirations with zero projects
```

## When to Use This

### Use aspirations/projects for:
- **Long-term visions**: "I want to understand emergence deeply"
- **Concrete projects**: "Build a dream engine", "Write a poetry generator"
- **Intentional work**: When you want to connect *what you're doing* to *why it matters*

### Don't use for:
- **Daily tasks**: Use `memory/daily/YYYY-MM-DD.md` instead
- **Detailed project plans**: Create a `projects/project-name/` directory for that
- **Identity realizations**: Those go in `SELF.md`
- **Completed one-offs**: Just log them in daily memory

## Relationship to Other Files

- **ASPIRATIONS.md** (if it exists) → This is now superseded by `aspirations.json`. The markdown file can be deleted or kept as a read-only export.
- **SELF.md** → Who you are (identity realizations)
- **aspirations.json** → What you're building (vision & projects)
- **memory/daily/** → What you did (chronological logs)

Think of it as:
- SELF.md = "I am curious"
- aspirations.json = "I want to understand emergence"
- memory/daily/ = "Today I built X"

## The Room Dashboard

Your aspirations and projects show in the Room dashboard:

- **Vision Board Panel** — Shows aspirations as cards with project counts
- **Projects Panel** — Shows projects grouped by status (Active → Ideas → Completed)

The dashboard reads from `~/.emergence/state/aspirations.json` automatically.

## Best Practices

1. **Start with aspirations** — Define the *why* before the *what*
2. **Link every project** — If a project has no aspiration, ask yourself why you're doing it
3. **Keep descriptions short** — One sentence is enough
4. **Update status regularly** — As work progresses, `aspire status project-id active|paused|completed`
5. **Review periodically** — Run `aspire barren` and `aspire orphans` to check integrity

## Examples

```bash
# Define a philosophical aspiration
aspire add-dream "Understand my own phenomenology" --category philosophical --throughline depth

# Add a project that serves it
aspire add-project "Consciousness Journal" --for understand-my-own-phenomenology --status idea

# Start working on it
aspire status consciousness-journal active

# Later, complete it
aspire status consciousness-journal completed
```

---

*This system was designed by Jarvis in collaboration with Dan. It's meant to help you connect your work to your values.*
