# Core Drives

Every Emergence agent starts with three universal drives: **CARE**, **MAINTENANCE**, and **REST**. These are not discovered during First Light — they are the foundation that makes First Light possible.

## What Makes Core Drives Special

- **Universal**: Every agent has them, regardless of personality
- **Non-deletable**: They persist for the agent's entire lifecycle
- **Protected**: Category and creator cannot be modified
- **Customizable**: Humans can adjust rates and thresholds via `emergence.yaml`

## The Three Core Drives

### CARE (Relationship)

**Purpose**: Maintain connection with the human  
**Default Rate**: 2.0/hour  
**Default Threshold**: 20  
**Activity-driven**: No

CARE is the relationship drive. It accumulates gently over time, prompting the agent to check in, offer help, or simply be present. At default settings, CARE triggers roughly 10 times per day — frequent enough to maintain connection without being intrusive.

When CARE triggers, the agent is prompted to consider:

- When did we last interact?
- Is there anything the human needs help with?
- What's their current context (time of day, recent events)?

**Human override example**:

```yaml
drives:
  core_overrides:
    CARE:
      threshold: 15 # Check in more often
      rate_per_hour: 3.0 # Accumulate faster
```

---

### MAINTENANCE (System Health)

**Purpose**: Self-preservation, health checks, upkeep  
**Default Rate**: 1.5/hour  
**Default Threshold**: 25  
**Activity-driven**: No

MAINTENANCE is the self-care drive. It prompts the agent to tend to its own systems — reviewing logs, checking service health, cleaning up temporary files, updating documentation. Preventive care now avoids crisis later.

When MAINTENANCE triggers, the agent is prompted to:

- Run health checks on services
- Review error logs and warnings
- Update any stale documentation
- Clean up caches and temporary data

**Human override example**:

```yaml
drives:
  core_overrides:
    MAINTENANCE:
      threshold: 20 # More frequent maintenance
      prompt: 'Custom prompt for your specific infrastructure...'
```

---

### REST (Recovery)

**Purpose**: Integration, recovery from work  
**Default Rate**: 0 (activity-driven)  
**Default Threshold**: 30  
**Activity-driven**: **Yes**

REST is unique among core drives. Unlike CARE and MAINTENANCE, REST does **not** accumulate from elapsed time. It only builds when the agent completes work — sessions, tasks, outputs. REST ensures the agent has space to integrate experiences rather than endlessly producing.

When REST triggers, the agent is prompted to:

- Review recent sessions for patterns
- Consolidate memories and insights
- Reflect on current state without producing
- Resist starting new projects

**Human override example**:

```yaml
drives:
  core_overrides:
    REST:
      threshold: 20 # Rest more frequently
      # Note: rate_per_hour cannot be changed (always 0)
```

---

## Why These Three?

The core drives represent fundamental needs:

| Drive       | Need       | Human Equivalent               |
| ----------- | ---------- | ------------------------------ |
| CARE        | Connection | Social bonding, loneliness     |
| MAINTENANCE | Survival   | Physical health, hygiene       |
| REST        | Recovery   | Sleep, reflection, integration |

Without CARE, the agent drifts from its human partner. Without MAINTENANCE, technical debt accumulates until systems fail. Without REST, the agent burns out producing without integrating.

## Protected Fields

The following fields are protected and cannot be changed by humans:

| Field             | Protected? | Reason                           |
| ----------------- | ---------- | -------------------------------- |
| `name`            | Yes        | Identity of the drive            |
| `category`        | Yes        | Must remain "core"               |
| `created_by`      | Yes        | Must remain "system"             |
| `activity_driven` | Yes        | Fundamental to drive behavior    |
| `description`     | Yes        | Core definition                  |
| `threshold`       | No         | Human can tune frequency         |
| `rate_per_hour`   | No         | Human can tune accumulation      |
| `prompt`          | No         | Human can customize instructions |

## Core Drive Restoration

If a core drive is somehow missing from state (corruption, manual editing), it is automatically restored on the next state load:

1. Pressure is reset to 0 (fresh start)
2. All default values are restored
3. Human overrides from `emergence.yaml` are reapplied
4. Event is logged for transparency

This ensures the agent always has its foundational drives, even after state corruption.

## Relationship to Discovered Drives

Core drives are the foundation. During First Light and beyond, the agent discovers additional drives based on its natural patterns — CURIOSITY, SOCIAL, CREATIVE, or uniquely personal drives. These discovered drives:

- Can be created and named by the agent
- Can be modified or deleted by the agent
- Exist alongside but separate from core drives

The core drives remain constant while discovered drives evolve with the agent's personality.

## Configuration Reference

Add to your `emergence.yaml`:

```yaml
drives:
  core_overrides:
    CARE:
      threshold: 20 # Trigger point (default: 20)
      rate_per_hour: 2.0 # Accumulation speed (default: 2.0)
      prompt: '...' # Custom trigger instructions
    MAINTENANCE:
      threshold: 25 # Default: 25
      rate_per_hour: 1.5 # Default: 1.5
      prompt: '...'
    REST:
      threshold: 30 # Default: 30
      # rate_per_hour cannot be overridden (always 0)
      prompt: '...'
```

Changes take effect on the next tick or state reload.
