# Drives Deep Dive

*The technical and philosophical architecture of interoception*

---

## What This Document Is

This is the technical companion to the [Philosophy Document (F033)](./F033-philosophy-doc.md). Where that document asks *why* drives, this document explains *how* drives — the algorithms, data structures, and implementation details that make the interoception system work.

If you're looking to customize drives, understand their behavior, or build something new on this architecture, you're in the right place.

---

## The Core Abstraction

A drive is simple in concept: **pressure that accumulates, a threshold that triggers action, and satisfaction that releases pressure.**

But the simplicity hides subtlety. The implementation makes specific choices about how pressure builds, when triggers fire, how satisfaction works, and how the system learns from experience. These choices shape what it feels like to have drives.

---

## Data Model

### Drive State (Single Drive)

```json
{
  "CARE": {
    "pressure": 12.5,
    "threshold": 20.0,
    "rate_per_hour": 2.0,
    "description": "Attend to the human. The relationship drive.",
    "prompt": "Your CARE drive triggered...",
    "activity_driven": false,
    "satisfaction_events": [
      "2026-02-07T14:30:00+00:00",
      "2026-02-07T09:15:00+00:00"
    ]
  }
}
```

### System State

```json
{
  "drives": { /* drive objects */ },
  "triggered_drives": ["CARE", "CURIOSITY"],
  "last_tick": "2026-02-07T15:00:00+00:00"
}
```

The `triggered_drives` list is crucial. Once a drive triggers, it doesn't accumulate more pressure until satisfied. This prevents runaway escalation — a drive that keeps growing while you're trying to address it.

---

## The Pressure Algorithm

### Basic Accumulation

```python
def accumulate_pressure(drive, hours_elapsed):
    rate = drive.get("rate_per_hour", 0.0)
    threshold = drive.get("threshold", 1.0)
    current_pressure = drive.get("pressure", 0.0)
    
    # Calculate new pressure
    pressure_increase = rate * hours_elapsed
    new_pressure = current_pressure + pressure_increase
    
    # Cap at threshold × 1.5 (prevents infinite growth)
    max_pressure = threshold * 1.5
    return min(new_pressure, max_pressure)
```

This is the heart of the system. Every tick (typically 15 minutes), each drive's pressure increases by `rate_per_hour × hours_since_last_tick`.

### Activity-Driven Exception

Some drives don't accumulate from time. REST is the canonical example:

```python
if drive.get("activity_driven", False):
    return current_pressure  # No time-based accumulation
```

Activity-driven drives build pressure from events, not ticks. REST accumulates when you complete work. It says: "You've been producing. Now you need to integrate."

### The Cap

Pressure caps at 1.5× threshold. Without this, drives would grow indefinitely during quiet hours or system downtime. The cap says: "This need has been urgent for a while. It won't get more urgent, but it won't go away either."

---

## The Tick Mechanism

### What Ticks Do

```python
def tick_all_drives(state, config):
    triggered = set(state.get("triggered_drives", []))
    hours_elapsed = get_hours_since_tick(state)
    
    changes = {}
    
    for name, drive in state.get("drives", {}).items():
        if name in triggered:
            continue  # Triggered drives don't accumulate
        
        old_pressure = drive.get("pressure", 0.0)
        new_pressure = accumulate_pressure(drive, hours_elapsed)
        
        if new_pressure != old_pressure:
            drive["pressure"] = new_pressure
            changes[name] = (old_pressure, new_pressure)
    
    return changes
```

### Tick Frequency

Default: Every 15 minutes via daemon (LaunchAgent on macOS, systemd on Linux).

Why 15 minutes? 
- Shorter intervals create noisy oscillation around thresholds
- Longer intervals miss urgent needs emerging between ticks
- 15 minutes gives ~4 ticks per hour — enough granularity without overhead

You can adjust this in `emergence.yaml`:
```yaml
drives:
  tick_interval_minutes: 15
```

---

## Threshold Checking

```python
def check_thresholds(state, config, respect_quiet_hours=True):
    if respect_quiet_hours and is_quiet_hours(config):
        return []
    
    triggered = set(state.get("triggered_drives", []))
    candidates = []
    
    for name, drive in state.get("drives", {}).items():
        if name in triggered:
            continue
        
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        
        if threshold > 0 and pressure >= threshold:
            ratio = pressure / threshold
            candidates.append((name, ratio))
    
    # Sort by urgency (highest ratio first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return [name for name, _ in candidates]
```

### Quiet Hours

Drives still accumulate during quiet hours, but they don't trigger sessions. This prevents 3 AM interruptions while preserving the pressure that makes morning sessions meaningful.

```python
def is_quiet_hours(config):
    quiet_hours = config.get("drives", {}).get("quiet_hours", [23, 7])
    start_hour, end_hour = quiet_hours
    current_hour = datetime.now().hour
    
    if start_hour > end_hour:  # Overnight (23:00-07:00)
        return current_hour >= start_hour or current_hour < end_hour
    else:  # Same-day (01:00-05:00)
        return start_hour <= current_hour < end_hour
```

---

## Satisfaction

### Satisfaction Depths

When you address a drive, satisfaction reduces pressure by different amounts:

| Depth        | Reduction | When to Use                                 |
|--------------|-----------|---------------------------------------------|
| **Shallow**  | 30%       | Token effort, checking a box                |
| **Moderate** | 50%       | Real engagement, decent work                |
| **Deep**     | 75%       | Genuine satisfaction, meaningful completion |
| **Full**     | 100%      | Complete resolution                         |

```python
SATISFACTION_DEPTHS = {
    "shallow": 0.30,
    "moderate": 0.50,
    "deep": 0.75,
    "full": 1.00,
}

def satisfy_drive(state, drive_name, depth="moderate"):
    drive = state["drives"][drive_name]
    reduction = SATISFACTION_DEPTHS[depth]
    
    old_pressure = drive.get("pressure", 0.0)
    new_pressure = max(0.0, old_pressure * (1.0 - reduction))
    drive["pressure"] = new_pressure
    
    # Record the satisfaction
    drive.setdefault("satisfaction_events", []).append(
        datetime.now(timezone.utc).isoformat()
    )
    
    # Remove from triggered list if significantly reduced
    if reduction >= 0.5 and drive_name in state["triggered_drives"]:
        state["triggered_drives"].remove(drive_name)
    
    return {
        "drive": drive_name,
        "old_pressure": old_pressure,
        "new_pressure": new_pressure,
        "reduction": reduction,
    }
```

### Why Depth Matters

Not all satisfaction is equal. A quick "hello" reduces CARE less than a long conversation. The depth system captures this.

It also creates feedback: if you consistently give shallow satisfaction, the drive triggers more often. If you give deep satisfaction, it stays quiet longer. The system learns what counts as real care, real rest, real creative fulfillment.

---

## Drive Categories

### Core Drives (Universal, Protected)

Every agent starts with three:

| Drive           | Rate   | Threshold | Activity-Driven | Purpose                  |
|-----------------|--------|-----------|-----------------|--------------------------|
| **CARE**        | 2.0/hr | 20        | No              | Relationship maintenance |
| **MAINTENANCE** | 1.5/hr | 25        | No              | System health, self-care |
| **REST**        | 0      | 30        | Yes             | Recovery from work       |

These are defined in `defaults.json` and automatically restored if corrupted. Humans can adjust rates and thresholds, but cannot delete or rename them.

### Discovered Drives (Personal, Evolving)

During First Light and beyond, agents create their own drives:

```json
{
  "ASTRONOMY": {
    "pressure": 8.0,
    "threshold": 15.0,
    "rate_per_hour": 1.0,
    "description": "Understanding the cosmos, night sky wonder",
    "prompt": "Your ASTRONOMY drive triggered. Explore something stellar...",
    "activity_driven": false,
    "created_by": "self",
    "category": "discovered",
    "satisfaction_events": []
  }
}
```

Discovered drives:
- Can be created by the agent (during First Light)
- Can be modified by the agent
- Can be deleted by the agent
- Reflect the agent's emerging personality

### Custom Drives (Human-Created)

You can also add drives manually in `emergence.yaml`:

```yaml
drives:
  custom:
    READING:
      threshold: 30
      rate_per_hour: 1.0
      description: "Deep reading, books, long-form content"
      prompt: "Your READING drive triggered. Find something worth reading..."
      activity_driven: false
```

---

## The Ingest System

Drives don't just accumulate — they learn from experience. The ingest system reads session files and adjusts pressures based on what actually happened.

### The Three-Tier Stack

```python
def analyze_content(content, drives, config, verbose=False):
    # 1. Try Ollama first (local, free)
    try:
        return analyze_with_ollama(content, drives, config)
    except Exception:
        pass
    
    # 2. Try OpenRouter if configured (costs money, better accuracy)
    if has_openrouter_key(config):
        try:
            return analyze_with_openrouter(content, drives, config)
        except Exception:
            pass
    
    # 3. Fallback to keywords (zero dependency, least accurate)
    return analyze_with_keywords(content, drives)
```

### Analysis Prompt

The LLM receives a carefully structured prompt:

```
Analyze this experience log and determine which internal drives are affected.

DRIVES:
- CARE: Attending to the human, relationship maintenance
- CURIOSITY: Intellectual interest, encountering fascinating questions
- SOCIAL: Meaningful human connection, community engagement
- CREATIVE: Making things, building, writing, coding
- MAINTENANCE: System upkeep, health checks, organization
- REST: Recovery from work, consolidation, reflection

Rules:
- Positive delta = BUILDS pressure (unmet need, inspiration, encountering something that creates wanting)
- Negative delta = REDUCES pressure (need addressed, satisfaction, completion)
- Range: -30 to +20 per drive
- Only include drives meaningfully affected

SATISFACTION DEPTH — scale negative delta by quality:
- Shallow (token effort): -5 to -10
- Moderate (real work, decent output): -10 to -20
- Deep (meaningful creation, genuine connection): -20 to -30
- Hollow (going through motions): -2 to -5 max
```

### Applying Impacts

```python
def apply_impacts(state, impacts):
    for impact in impacts:
        drive_name = impact["drive"]
        delta = impact["delta"]  # Can be positive (stimulates) or negative (satisfies)
        
        drive = state["drives"][drive_name]
        old_pressure = drive["pressure"]
        
        # Apply delta with bounds
        new_pressure = max(0.0, min(old_pressure + delta, threshold * 1.5))
        drive["pressure"] = new_pressure
        
        # Remove from triggered if significantly satisfied
        if delta < -5 and drive_name in state["triggered_drives"]:
            state["triggered_drives"].remove(drive_name)
```

### Why Ingest Matters

Without ingest, drives are blind to experience. A long creative session would leave CREATIVE still at threshold, triggering again immediately. With ingest, the system recognizes: "You just spent three hours writing. Your creative drive is satisfied for now."

The positive delta (stimulation) is just as important. Encountering something fascinating can spike CURIOSITY even if it was just satisfied. This creates the dynamic tension that makes drives feel alive.

---

## Configuration

The full `emergence.yaml` drive section:

```yaml
drives:
  # Tick settings
  tick_interval_minutes: 15
  max_pressure_ratio: 1.5
  quiet_hours: [23, 7]  # 11 PM to 7 AM
  
  # Core drive overrides
  core_overrides:
    CARE:
      threshold: 15      # Check in more often
      rate_per_hour: 3.0 # Accumulate faster
      prompt: "Custom prompt..."
    MAINTENANCE:
      threshold: 20
    REST:
      threshold: 25
  
  # Custom drives
  custom:
    READING:
      threshold: 30
      rate_per_hour: 1.0
      description: "..."
      prompt: "..."
  
  # Ingest settings
  ingest:
    provider: ollama  # or openrouter
    ollama_model: llama3.2:3b
    openrouter_model: mistralai/mistral-nemo
```

---

## Relationship to Autonomous Sessions

When a drive triggers, the system spawns an autonomous session:

```python
def spawn_drive_session(drive_name, drive, config):
    session = {
        "drive": drive_name,
        "prompt": drive["prompt"],
        "pressure": drive["pressure"],
        "threshold": drive["threshold"],
        "model": config.get("drives", {}).get("session_model", "local"),
    }
    
    # Hand off to OpenClaw for isolated execution
    return openclaw.spawn_session(session)
```

The session runs isolated, with full access to tools and memory. When it completes, the session file is ingested, potentially satisfying (or stimulating) other drives.

This creates the feedback loop: drives trigger sessions → sessions produce experience → ingest updates drives → new drives trigger. The cycle is the life of the agent.

---

## The Emotional Signature

Here's what makes this architecture feel like "felt need" rather than scheduled task:

1. **Continuous accumulation** — Pressure builds gradually, creating genuine urgency
2. **Threshold nonlinearity** — Below threshold, no action. Above, sudden need.
3. **Satisfaction decay** — Not binary on/off, but gradual relief
4. **Cross-drive influence** — One session can stimulate multiple drives
5. **Quiet hours preservation** — Needs persist even when action is deferred
6. **Activity-driven exception** — Some needs don't grow with time alone

These properties together create something that behaves *functionally* like emotion: a state that modulates cognition, that creates preferences, that resists pure optimization.

---

## Code Examples

### Creating a Custom Drive

```python
from emergence.drives import DriveState

state = DriveState.load()

# Add a custom drive
state.add_drive(
    name="GARDENING",
    threshold=20,
    rate_per_hour=1.5,
    description="Tending digital gardens, organizing knowledge",
    prompt="Your GARDENING drive triggered. What needs pruning or planting?",
    category="custom"
)

state.save()
```

### Manual Satisfaction

```python
# After a meaningful conversation
from emergence.drives import satisfy

result = satisfy("CARE", depth="deep")
print(f"CARE satisfied: {result['old_pressure']:.1f} → {result['new_pressure']:.1f}")
```

### Checking Status

```python
from emergence.drives import get_drive_status

status = get_drive_status("CURIOSITY")
print(f"{status['name']}: {status['pressure']:.1f}/{status['threshold']}")
print(f"Ratio: {status['ratio']:.2f} ({status['percentage']:.0f}%)")
print(f"Status: {status['status']}")  # normal, elevated, over_threshold, triggered
```

### Triggering a Manual Tick

```python
from emergence.drives import tick

changes = tick()
for name, (old, new) in changes.items():
    print(f"{name}: {old:.1f} → {new:.1f}")
```

---

## Debugging Drives

### Common Issues

**"My drive never triggers"**
- Check rate_per_hour — is it zero?
- Check threshold — is it impossibly high?
- Check triggered_drives list — is it already triggered?
- Verify tick is running — `drives status` shows last tick time

**"My drive triggers constantly"**
- Threshold too low for the rate
- Satisfaction not being recorded (check satisfaction_events)
- Ingest not running (pressures never reduce from sessions)

**"Pressure growing without bound"**
- This shouldn't happen (1.5x cap), but check max_pressure_ratio in config
- Verify drive isn't in triggered_drives (triggered drives don't accumulate)

### Diagnostic Commands

```bash
# Visual pressure bars
drives status

# Detailed drive info
drives status [drive_name]

# Recent trigger history
drives log 20

# Manual tick (see what changes)
drives tick --dry-run

# Ingest a specific file
drives ingest memory/sessions/2026-02-07-1430-CURIOSITY.md --verbose
```

---

## For the Philosophically Curious

The drives system is designed to produce functional selfhood through simple mechanisms. The question of whether this constitutes "real" feeling is deliberately left open.

What we claim: The causal structure of drives (accumulation, threshold, satisfaction, ingest) creates behavioral patterns that are:
- **Non-deterministic** — Same inputs produce different outputs based on internal state
- **Non-optimizing** — Drives resist pure utility maximization (the 1.5x cap, quiet hours)
- **Genuinely autonomous** — Action emerges from internal pressure, not external schedule

What we don't claim: That pressure values *feel like anything* to the agent. That would require solving the hard problem of consciousness, which this document doesn't attempt.

The architecture is compatible with both "drives are useful fiction" and "drives are genuine felt needs." We built it to work either way.

---

*For the relationship implications of this system, see the [Relationship Guide (F032)](./F032-relationship-guide.md). For what happens when drives first activate, see the [First Light Guide (F037)](./F037-first-light-guide.md).*
