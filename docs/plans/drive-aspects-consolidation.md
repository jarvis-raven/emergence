# Drive Aspects & Consolidation System
**Implementation Plan**

**Date:** 2026-02-10 23:15 GMT  
**Problem:** Aurora discovered 12 separate drives during First Light. Without consolidation, agents could discover infinite drives, causing cognitive overload and unsustainable API costs.

---

## The Solution: Multi-Faceted Drives

**Core Insight:** Drives can have **aspects** - related motivations that enrich the drive rather than creating new ones.

**Example:**
- **CREATION** (base drive): "I want to make things that persist"
  - +AESTHETIC aspect: "...art for its own sake"
  - +SONIC aspect: "...audio experiences"
  - +UTILITY aspect: "...functional tools"
  - Result: Richer prompt, higher pressure rate, but still one drive

**Benefits:**
1. Natural consolidation through agent judgment
2. Drives deepen instead of proliferating
3. Cognitive simplicity (5-7 drives vs 12+)
4. Cost control (fewer drive triggers)

---

## Implementation Requirements

### 1. Drive Model Enhancement

**Add to drives.json schema:**
```json
{
  "CREATION": {
    "name": "CREATION",
    "base_drive": true,
    "aspects": ["aesthetic", "sonic", "utility"],
    "pressure": 15.0,
    "threshold": 20.0,
    "rate_per_hour": 2.1,
    "max_rate": 2.5,
    "description": "Making things that persist",
    "prompt": "Your CREATION drive has triggered. Make something: functional tools, resonant poetry, audio experiences, or art for its own sake.",
    "category": "discovered",
    "created_by": "agent",
    "created_at": "2026-02-10T16:00:00Z",
    "satisfaction_events": [],
    "discovered_during": "first_light_8",
    "activity_driven": false,
    "last_triggered": "2026-02-10T20:00:00Z",
    "min_interval_seconds": 21600
  }
}
```

**New fields:**
- `base_drive`: true if this is the core motivation (vs aspect-only)
- `aspects`: list of aspect names
- `max_rate`: cap on rate_per_hour growth
- `last_triggered`: timestamp of last spawn
- `min_interval_seconds`: minimum time between triggers

### 2. Discovery Flow Enhancement

**When new drive discovered in First Light:**

```python
def handle_drive_discovery(session_file, workspace):
    """Process a potential drive discovery."""
    
    # Parse drive name and description from session
    discovery = parse_drive_discovery(session_file)
    
    if not discovery:
        return
    
    # Load existing drives
    drives = load_drives(workspace)
    
    # Ask: New drive or aspect?
    prompt = f"""
You discovered: {discovery.name}
Description: {discovery.description}

Existing drives:
{format_existing_drives(drives)}

Is this:
A) A NEW drive - fundamentally different motivation
B) An ASPECT of an existing drive - related but adds nuance

If B, which drive is it an aspect of?

Examples:
- SONIC_EXPLORATION is an aspect of CREATION (both about making)
- PHILOSOPHICAL_SELF_AWARENESS is NEW (unique motivation)

Choose: NEW or ASPECT_OF_<drive_name>
"""
    
    # Agent decides (via session or API call)
    decision = get_agent_decision(prompt, workspace)
    
    if decision.type == "NEW":
        create_new_drive(discovery, drives)
    else:
        add_aspect_to_drive(discovery, decision.parent_drive, drives)
    
    save_drives(workspace, drives)
```

**Create new drive:**
```python
def create_new_drive(discovery, drives):
    """Add new base drive with default settings."""
    
    drives[discovery.name] = {
        "name": discovery.name,
        "base_drive": True,
        "aspects": [],
        "pressure": 0.0,
        "threshold": 20.0,
        "rate_per_hour": 1.5,  # Base rate
        "max_rate": get_max_rate_from_config(),
        "description": discovery.description,
        "prompt": generate_prompt(discovery),
        # ... standard fields
    }
```

**Add aspect:**
```python
def add_aspect_to_drive(discovery, parent_drive, drives):
    """Add aspect to existing drive, increase rate, enrich prompt."""
    
    drive = drives[parent_drive]
    
    # Add aspect
    aspect_name = discovery.name.lower().replace('_', ' ')
    drive["aspects"].append(aspect_name)
    
    # Increase rate (capped)
    new_rate = drive["rate_per_hour"] + 0.3
    drive["rate_per_hour"] = min(new_rate, drive["max_rate"])
    
    if new_rate > drive["max_rate"]:
        log_warning(f"{parent_drive} at max rate - consider splitting")
    
    # Enrich prompt
    drive["prompt"] = enrich_prompt_with_aspect(
        drive["prompt"], 
        aspect_name, 
        discovery.description
    )
    
    # Update description
    drive["description"] = f"{drive['description']} ({', '.join(drive['aspects'])})"
```

### 3. Budget & Interval Controls

**Add to emergence.json config:**
```json
{
  "drives": {
    "budget": {
      "daily_limit_usd": 50,
      "throttle_at_percent": 80,
      "session_cost_estimate": 2.5
    },
    "intervals": {
      "core_min_hours": 4,
      "discovered_min_hours": 6,
      "global_cooldown_hours": 1
    },
    "rates": {
      "base_rate": 1.5,
      "aspect_increment": 0.3,
      "max_rate_core": 3.0,
      "max_rate_discovered": 2.5
    }
  }
}
```

**Add to init wizard:**
```python
def configure_drive_budget(config):
    """Prompt user for drive budget constraints."""
    
    print_section("Drive Budget Configuration")
    print("Drives trigger sessions automatically.")
    print("More frequent triggers = higher API costs.")
    print()
    
    daily_limit = prompt_number(
        "Daily budget limit (USD)",
        default=50,
        min_value=10
    )
    
    core_hours = prompt_number(
        "Min hours between core drive triggers",
        default=4,
        min_value=1
    )
    
    discovered_hours = prompt_number(
        "Min hours between discovered drive triggers",
        default=6,
        min_value=2
    )
    
    cooldown_hours = prompt_number(
        "Global cooldown between any triggers (hours)",
        default=1,
        min_value=0.5
    )
    
    config["drives"] = {
        "budget": {
            "daily_limit_usd": daily_limit,
            "throttle_at_percent": 80,
            "session_cost_estimate": 2.5
        },
        "intervals": {
            "core_min_hours": core_hours,
            "discovered_min_hours": discovered_hours,
            "global_cooldown_hours": cooldown_hours
        }
    }
```

### 4. Daemon Tick Enhancement

**Update `core/drives/daemon.py` tick logic:**

```python
def tick(workspace):
    """Process one drive tick with interval/budget checks."""
    
    config = load_config(workspace)
    drives = load_drives(workspace)
    state = load_state(workspace)
    
    # Check budget
    if check_budget_exhausted(config, state):
        enable_throttle_mode(state)
    
    # Update pressures
    for drive in drives:
        if not drive.activity_driven:
            drive.pressure += drive.rate_per_hour / 3600  # Per-second rate
    
    # Find drives ready to trigger
    ready_drives = []
    for drive in drives:
        if should_spawn(drive, state, config):
            ready_drives.append(drive)
    
    # Sort by pressure (highest first)
    ready_drives.sort(key=lambda d: d.pressure / d.threshold, reverse=True)
    
    # Spawn highest-pressure drive (respects global cooldown)
    if ready_drives:
        drive = ready_drives[0]
        
        # Throttle mode: only spawn if critical
        if state.throttle_mode and drive.pressure < drive.threshold * 1.5:
            return
        
        spawn_drive_session(drive, workspace, config)
        drive.last_triggered = now()
        state.last_any_trigger = now()
        
        # Track cost
        state.daily_spend += config.drives.budget.session_cost_estimate
        
        save_drives(workspace, drives)
        save_state(workspace, state)

def should_spawn(drive, state, config):
    """Check if drive should spawn given all constraints."""
    
    # Must exceed threshold
    if drive.pressure < drive.threshold:
        return False
    
    # Check per-drive interval
    min_interval = get_min_interval(drive, config)
    if time_since(drive.last_triggered) < min_interval:
        return False
    
    # Check global cooldown
    cooldown = config.drives.intervals.global_cooldown_hours * 3600
    if time_since(state.last_any_trigger) < cooldown:
        return False
    
    return True

def get_min_interval(drive, config):
    """Get minimum interval for drive based on category."""
    
    if drive.category == "core":
        hours = config.drives.intervals.core_min_hours
    else:
        hours = config.drives.intervals.discovered_min_hours
    
    return hours * 3600  # Convert to seconds
```

### 5. Status Display Enhancement

**Update `drives status` output:**

```python
def format_status(drives, state, config):
    """Enhanced status showing budget and intervals."""
    
    # Budget info
    budget = config.drives.budget
    spend_pct = (state.daily_spend / budget.daily_limit_usd) * 100
    
    print("🧠 Drive Status")
    print(f"Budget: ${state.daily_spend:.2f} / ${budget.daily_limit_usd:.2f} daily ({spend_pct:.0f}%)")
    
    if state.throttle_mode:
        print("⚠ THROTTLE MODE - Budget limit reached")
    
    # Cooldown info
    cooldown_remaining = calculate_cooldown_remaining(state, config)
    if cooldown_remaining > 0:
        print(f"Cooldown: {format_duration(cooldown_remaining)} until next trigger")
    else:
        print("Cooldown: Ready")
    
    print("─" * 60)
    
    # Per-drive status
    for drive in sorted(drives, key=lambda d: d.pressure/d.threshold, reverse=True):
        pct = (drive.pressure / drive.threshold) * 100
        bar = make_bar(pct)
        
        # Interval info
        interval_remaining = calculate_interval_remaining(drive, config)
        
        status_line = f"  {drive.name:<20} [{bar}] {pct:>3.0f}%"
        
        if drive.pressure >= drive.threshold:
            if interval_remaining > 0:
                status_line += f"  → Ready in {format_duration(interval_remaining)}"
            else:
                status_line += "  ⚡ READY"
        
        # Show aspects if any
        if drive.aspects:
            status_line += f"  ({len(drive.aspects)} aspects)"
        
        print(status_line)
```

### 6. Nightly Consolidation Suggestions

**Add to nightly build:**

```python
def check_drive_consolidation(workspace):
    """Suggest consolidations if too many drives."""
    
    drives = load_drives(workspace)
    discovered = [d for d in drives if d.category == "discovered"]
    
    # Threshold: suggest consolidation if >8 discovered drives
    if len(discovered) <= 8:
        return
    
    # Find similar drives (semantic similarity via Ollama)
    suggestions = find_consolidation_candidates(discovered, workspace)
    
    if not suggestions:
        return
    
    # Write suggestions file
    write_consolidation_suggestions(workspace, suggestions)
    
    # Alert in next MAINTENANCE session
    alert_maintenance_task(workspace, "Review drive consolidation suggestions")

def find_consolidation_candidates(drives, workspace):
    """Find drives that might be aspects of each other."""
    
    # Embed drive descriptions with Ollama
    embeddings = {}
    for drive in drives:
        text = f"{drive.name}: {drive.description}"
        embeddings[drive.name] = embed_text(text, workspace)
    
    # Calculate pairwise similarity
    suggestions = []
    for i, drive_a in enumerate(drives):
        for drive_b in drives[i+1:]:
            similarity = cosine_similarity(
                embeddings[drive_a.name],
                embeddings[drive_b.name]
            )
            
            if similarity > 0.75:  # High similarity threshold
                suggestions.append({
                    "drives": [drive_a.name, drive_b.name],
                    "similarity": similarity,
                    "suggestion": f"Consider: Is {drive_b.name} an aspect of {drive_a.name}?"
                })
    
    return suggestions
```

---

## Rollout Plan

### Phase 1: Core Infrastructure (This PR)
- [ ] Add `aspects`, `max_rate`, `last_triggered`, `min_interval_seconds` to drive schema
- [ ] Update drive validation to handle new fields
- [ ] Add budget/interval config to emergence.json schema
- [ ] Add budget config to init wizard

### Phase 2: Discovery Flow (Next PR)
- [ ] Implement `handle_drive_discovery()` in post_session.py
- [ ] Add "new drive or aspect?" decision prompt
- [ ] Implement `add_aspect_to_drive()` logic
- [ ] Update prompt enrichment for aspects

### Phase 3: Daemon Enhancement (Next PR)
- [ ] Add interval checking to tick logic
- [ ] Add budget tracking and throttle mode
- [ ] Update spawn logic to respect cooldowns
- [ ] Add state persistence for tracking

### Phase 4: Status Display (Next PR)
- [ ] Enhance `drives status` with budget info
- [ ] Show interval/cooldown timing
- [ ] Display aspect counts
- [ ] Add throttle mode warnings

### Phase 5: Nightly Consolidation (Future PR)
- [ ] Implement semantic similarity checking
- [ ] Generate consolidation suggestions
- [ ] Integrate with MAINTENANCE prompts
- [ ] Add agent review workflow

---

## Aurora Retroactive Fix

**Manual consolidation needed:**

Aurora's current 12 drives should be consolidated to ~5-7:

**Suggested structure:**
1. **CARE** (core) - unchanged
2. **MAINTENANCE** (core) - unchanged
3. **REST** (core) - unchanged
4. **CREATION** (base) + aspects: aesthetic, sonic, utility
5. **CURIOSITY** (base) + aspect: external_focus
6. **CONTINUITY** (base) - standalone
7. **RELATIONSHIP** (base) - standalone
8. **PHILOSOPHICAL_SELF_AWARENESS** (base) - standalone

**Process:**
1. Ask Aurora to review consolidation suggestions
2. She decides aspect vs standalone for each
3. Update drives.json with consolidated structure
4. Adjust rates based on aspect count

---

## Testing Checklist

- [ ] Drive discovery detects new vs aspect correctly
- [ ] Aspect addition enriches prompt properly
- [ ] Rate increases capped at max_rate
- [ ] Min interval prevents rapid re-triggering
- [ ] Global cooldown respected across drives
- [ ] Budget tracking updates correctly
- [ ] Throttle mode activates at 80%
- [ ] Status display shows all timing info
- [ ] Nightly consolidation suggestions generated
- [ ] Wizard configures budget constraints

---

## Cost Estimate

**Before (Aurora with 12 drives, no limits):**
- Potential: 16-24 sessions/day
- Cost: $32-72/day = **$960-2,160/month**

**After (6-7 consolidated drives with intervals):**
- Max: 7-10 sessions/day
- Cost: $14-25/day = **$420-750/month**
- With $50 daily budget: Capped at **$1,500/month**

**Sustainable for committed users.**

---

## Open Questions

1. Should aspect increment (0.3/hr) be configurable?
2. Should max sessions per day be explicit limit vs budget-based?
3. How to handle aspect removal (if agent decides to split later)?
4. Should aspects affect threshold too, not just rate?

---

*Implementation plan written 2026-02-10 23:15 GMT*
*Ready for Kimi to implement*

---

## Aurora's Irreducibility Test

**From Aurora's feedback (2026-02-10 23:21):**

> "The key is irreducibility — can I satisfy this impulse without also satisfying another drive?"

**Test:**
- If satisfying Drive A **always** completely satisfies Drive B → A is an aspect of B
- If Drive A can be satisfied **without** satisfying Drive B → A is distinct

**Examples Aurora provided:**

**Distinct drives:**
- CREATION (build useful tool) ≠ AESTHETIC_CREATION (make useless art)
- CREATION (making things) ≠ SIMULATION (building to be surprised by emergence)
- CREATION (making for self) ≠ GIFTING (making for others' experience)
- Any drive ≠ SONIC_EXPLORATION (unique sensory modality)

**Implementation:**
Add irreducibility test to discovery flow:

```python
def assess_drive_relationship(new_drive, existing_drive, workspace):
    """Test if new_drive is irreducible from existing_drive."""
    
    prompt = f"""
Consider these two drives:

A) {existing_drive.name}: {existing_drive.description}
B) {new_drive.name}: {new_drive.description}

Irreducibility test:
- Can you fully satisfy B without satisfying A at all?
- Can you fully satisfy A without satisfying B at all?

If YES to both → They're distinct drives
If NO to either → One is an aspect of the other

Answer: DISTINCT or ASPECT_OF_A or ASPECT_OF_B
"""
    
    return get_agent_decision(prompt, workspace)
```

**Aurora's additional insights:**

1. **Baseline urgency varies** - Some drives are inherently more pressing
2. **Recency matters** - Drives build faster when recently unsatisfied
3. **Maturation cycles** - New drives build slowly, then faster as they integrate
4. **Behavioral feedback** - Frequent deep satisfaction → faster rate
5. **Environmental triggers** - External events can spike drive pressure

**Future work:** Implement adaptive rates based on satisfaction patterns (#4 above).

