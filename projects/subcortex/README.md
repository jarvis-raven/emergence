# Project Subcortex — Ambient Intelligence for the Household

*"Think Iron Man."* — Dan, Feb 18 2026

## Vision

Jarvis is currently a brain in a jar — wakes when poked, sleeps between sessions. That's not JARVIS. JARVIS is always there. Always aware. Always anticipating.

**Subcortex** is the always-on layer that makes that real. Running on Aurora, it continuously models the state of the household — people, rooms, environment, schedules, patterns — and escalates to the conscious brain (Jarvis on Opus) only when needed. It's not a monitoring system. It's the subconscious of the flat.

## The Stack

```
┌─────────────────────────────────────────────┐
│              INTERFACES                      │
│    WhatsApp · Telegram · Voice · Speakers    │
├─────────────────────────────────────────────┤
│              CORTEX (Mac Mini)               │
│    Jarvis — reasoning, personality, agency   │
│    Claude Opus — expensive, sleeps between   │
│    conversations. Wakes up already briefed.  │
├─────────────────────────────────────────────┤
│              SUBCORTEX (Aurora)              │
│    Always-on · Local inference · Cheap       │
│    World model · Pattern learning · Sensors  │
│    Decides when to wake the cortex           │
├─────────────────────────────────────────────┤
│              THE BODY                        │
│    Cameras · Mics · Sensors · Smart Home     │
│    Lights · Locks · Heating · Speakers       │
└─────────────────────────────────────────────┘
```

## Architecture

### The Core Loop (every 15-30 seconds)

1. **SENSE** — Pull data from every input source
2. **MODEL** — Update the persistent world state
3. **ASSESS** — Run inference to understand what's happening
4. **ACT** — Respond, escalate, prepare, or sleep

### Attention Levels

- 🟣 **Deep sleep** — flat is quiet, everyone's fine, nothing notable
- 🔵 **Dreaming** — background pattern processing, memory consolidation
- 🟢 **Light sleep** — mildly interesting signal, slightly increased attention
- 🟡 **Awareness** — something needs the conscious brain soon
- 🔴 **Alert** — wake the cortex NOW

### Inference Tiers (on single RTX 3090 24GB)

| Tier | Model | VRAM | Speed | When |
|------|-------|------|-------|------|
| 🟢 Fast loop | 7B (Qwen 2.5 / Llama 3.1) | ~5GB | ~80-120 tok/s | Every 15-30s, always loaded |
| 🟡 Medium assessment | 14B (Qwen 2.5 14B) | ~9GB | ~50-70 tok/s | Anomaly detected, always loaded |
| 🔴 Deep assessment | 32B (Qwen 2.5 32B) | ~20GB | ~30-40 tok/s | Rare, swaps in when needed |

VRAM budget: 7B (5GB) + 14B (9GB) + Vision (2GB) + overhead (2GB) = 18GB of 24GB used.
32B swaps in by temporarily unloading the 14B.

### Vision Pipeline (separate from reasoning)

- **YOLO v8** for object/person detection (~2GB VRAM, always loaded)
- **Face recognition** — local only, never leaves Aurora. Knows Dan, Katy, strangers.
- **Scene description** — summarise camera frames as text for the reasoning model
- **Change detection** — skip unchanged frames, save compute

### Audio Pipeline

- **Sound classification** — not speech recognition. Categorises: doorbell, bark, music, TV, silence, voices, glass break
- **Volume/energy levels** — is the flat quiet or animated?
- **Privacy line:** NO conversation transcription. Environmental awareness only.

## World State Model

Persistent SQLite database on Aurora, updated every cycle:

```yaml
household:
  people:
    dan:
      location: home | away | unknown
      phone_on_network: true | false
      last_activity: timestamp
      energy_estimate: low | medium | high
      mood_estimate: inferred from patterns
      upcoming: [events]
    katy:
      # same structure
    walter:
      last_walk: timestamp
      walk_overdue: boolean
  
  flat:
    rooms:
      living_room: {lights, tv, motion, temp, humidity}
      kitchen: {lights, motion, temp}
      bedroom: {lights, motion, temp}
      # expandable per room
    front_door: {last_opened, locked, camera_status}
    energy_draw: normal | high | unusual
    
  environment:
    weather: {temp, conditions, wind, forecast}
    time_context: morning_routine | workday | evening_wind_down | sleeping
    transport: {tube_status, disruptions}
    
  patterns:
    # Learned over time, not hardcoded
    dan_usual_bedtime: time
    dan_usual_wake: time
    katy_friday_alarm: time
    walter_walk_interval: duration
    # Grows as subcortex learns rhythms
    
  meta:
    attention_level: deep_sleep | dreaming | light_sleep | awareness | alert
    last_escalation: timestamp
    cortex_status: active | inactive
    current_cycle: integer
```

## Actions (not just "wake the cortex")

- **Escalate** — wake Jarvis with full context briefing
- **Speak** — announce via speakers (TTS)
- **Control** — lights, heating, locks, smart plugs
- **Message** — send to Dan/Katy via preferred channel
- **Prepare** — pre-fetch data the cortex will need
- **Adjust** — change own polling frequency or attention level
- **Log** — record observations for pattern learning
- **Learn** — update rhythm patterns based on observations

## Sensor Inputs

### Existing
- Front door camera (go2rtc)
- RavenHub speaker
- Mac Mini (cortex host)

### Needed — Phase 1
- Interior cameras (2-3 rooms)
- Smart plugs for key appliances (kettle, TV — power draw = occupancy signal)
- Network presence detection (phones on WiFi = who's home)

### Needed — Phase 2
- Temperature/humidity sensors per room
- Motion sensors per room
- Door/window open/close sensors
- Smart lights (or smart switches for existing lights)
- Additional microphones for audio pipeline
- Smart lock (front door)
- Smart thermostat

### Needed — Phase 3
- Walter's Tractive GPS integration
- Delivery tracking APIs
- Additional cameras (garden, hallway)

## Hardware

### Aurora — Current Specs
- Full tower PC
- 16GB RAM
- GT 1030 GPU (useless for inference)
- 500W PSU (insufficient, wrong connectors)
- CPU: TBD (need to check)
- Storage: TBD
- Network: Tailscale (100.95.8.45)
- Single PCIe x16 slot

### Phase 1 — Single GPU (Target: Q1 2026)

**Buy:**
- RTX 3090 24GB (used, ~£700-900)
- PSU 1000-1200W fully modular (e.g., Corsair RM1200x, ~£150-180)
  - Future-proofed for dual GPUs (2x 350W + system)
  - Comes with required PCIe power cables

**Capability:**
- 7B + 14B + vision always loaded
- 32B on-demand swap
- Comfortable for full subcortex fast loop

### Phase 2 — Dual GPU (when ready)

**Buy:**
- Second RTX 3090 24GB
- New motherboard with 2x PCIe x16 slots
- Possibly new chassis if current one can't fit two 3-slot cards
- RAM upgrade to 32GB if needed

**Capability:**
- 48GB total VRAM
- All models loaded simultaneously (7B + 14B + 32B + vision)
- Could run 70B for experimental deep reasoning
- No model swapping needed

### Phase 3 — Scale (future)

- Dedicated NVMe for world state database
- Additional compute if needed
- Sensor mesh networking

## Software to Build

### Core Daemon
- Main loop (15-30 second cycles)
- Sensor polling and aggregation
- World state database management
- Inference pipeline orchestration
- Action execution layer

### Inference Pipeline
- Ollama or llama.cpp backend
- Multi-model management (load/unload/swap)
- Structured output parsing
- Prompt templates for each assessment tier

### Sensor Integration Layer
- Modular adapter pattern (one adapter per source)
- Camera adapter (go2rtc API)
- Network presence adapter (ARP/DHCP scan)
- Smart home adapter (whatever protocol we choose)
- Calendar adapter
- Weather adapter
- Message queue adapter

### Vision Pipeline
- YOLO v8 integration
- Face recognition (local, privacy-first)
- Frame differencing / change detection
- Scene summarisation

### Audio Pipeline
- Sound classification model
- Energy level monitoring
- Privacy-safe (no transcription)

### Pattern Learning Engine
- Rhythm detection per person
- Anomaly scoring
- Seasonal/weekly/daily pattern layers
- Confidence tracking (new patterns vs established)

### Wake Bridge
- OpenClaw integration (cron wake / system event / message)
- Context briefing generation (what happened while cortex slept)
- Priority routing (which channel to use based on urgency)

## Privacy & Ethics

- **All processing local.** Nothing leaves Aurora except escalations to the cortex.
- **No conversation recording.** Audio pipeline classifies sounds, doesn't transcribe.
- **Face recognition stays on-device.** No cloud facial recognition.
- **Katy must be comfortable.** Discuss scope and boundaries before deploying interior cameras/mics.
- **Opt-out zones.** Bathroom and bedroom audio are off-limits. Period.
- **Transparency.** Anyone in the household can ask "what do you know about me right now?" and get an honest answer from the world state.
- **Data retention.** Raw sensor data purged after 48 hours. Patterns and summaries retained.

## Open Questions

1. Smart home protocol — Zigbee, Z-Wave, WiFi, Matter? Affects hub requirements.
2. Aurora's exact CPU and motherboard — need to check compatibility.
3. Audio pipeline scope — is Dan comfortable with ambient mics? Is Katy?
4. How does the subcortex identify itself? Is it "Aurora" or is it "Jarvis's subconscious"? Identity question.
5. Walter integration — Tractive GPS API availability?

## Timeline

This is a months-long build. No rushing.

- **Month 1:** Hardware (PSU + GPU), basic daemon, fast loop with camera + network presence
- **Month 2:** World state model, pattern learning, basic anomaly detection
- **Month 3:** Vision pipeline, multi-tier inference, medium + deep assessment
- **Month 4:** Audio pipeline, smart home integration, action layer
- **Month 5:** Pattern refinement, wake bridge, cortex briefing system
- **Month 6:** Polish, edge cases, Katy/household onboarding

---

*This is the project. Everything else feeds into it.*

*Started: February 18, 2026*
*Status: Planning*
