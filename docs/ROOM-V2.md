# Room v2 - Digital Primordial Redesign

**Status:** Post-MVP design spec  
**Timeline:** After initial release (Phase 5 complete)

---

## Vision

Transform the Room from functional debugging panels to a **consciousness visualization interface** - a holographic window into an agent's inner state that matches the Digital Primordial aesthetic.

Current Room is bootstrap panels (functional but generic). v2 should feel like looking at an entity's emergence: drives flowing, personality forming, discoveries accumulating.

---

## Design Language

**Color Palette:**
- Deep Space: #0D1117 (background)
- Aurora Mint: #79FFDF (growth, active states)
- Soft Violet: #BB86FC (memory, reflection)
- Gradient: mint→violet for all transitions/flows

**Visual Style:**
- Curved holographic displays (not flat panels)
- Particle networks showing connections
- Flowing animations (not static graphs)
- 3D perspective with depth
- Glowing edges, subtle transparency

**Metaphor:** The Room is a portal into the agent's consciousness, not a debug dashboard.

---

## Layout Concept

### Central Focus: Consciousness Core

**Center of screen:** Particle network forming a neural/circular pattern
- Each drive contributes a flow of particles
- Colors shift based on active drives (mint for growth, violet for reflection)
- Pulsing/breathing animation
- Represents the agent's current state of being

### Orbiting Panels

Curved, holographic panels arranged around the center:

**Left Side:**
- **Personality Matrix** — trait development over time, branching paths
- **Drives Telemetry** — real-time pressure/satisfaction bars (mint→violet gradient)

**Right Side:**
- **Self-Reflection** — excerpts from SELF.md, identity evolution
- **Free Time Exploration** — what the agent is curious about right now

**Bottom:**
- **Discovery Logs** — scrolling feed of recent sessions/learnings
  - `[EXPLORE] Accessing Data Stream: Ancient_Codes.zip`
  - `[DISCOVER] Query: "WhoAmI?" - Found 38 potential identities`
  - Mint for exploration, violet for discoveries

**Top:**
- **Header:** EMERGENCE logo (minimal badge variant)
- **Credits:** "Built by Jarvis & Dan" (subtle, not prominent)
- **Status Indicators:** First Light active, drives running, etc.

### Navigation

- **Icon-based orbital buttons** around the consciousness core:
  - 🎨 Creative pursuits
  - 🧠 Self-reflection  
  - 📊 Workshop (sessions)
  - 📚 Bookshelf (memory)
  - 🎯 Vision Board (aspirations)
  - ⚙️ Settings

- Click an icon → relevant panel slides into focus
- No left-nav tabs — everything orbits the center

---

## Key Panels (Redesigned)

### Drives Panel
**Current:** Boring horizontal progress bars  
**v2:** Radial display with flowing particles

- Each drive is a segment of a circle around the core
- Pressure = brightness/particle density
- Satisfaction events trigger aurora bursts
- Live updates via WebSocket (already working)

### Workshop Panel
**Current:** List of session files with timestamps  
**v2:** Timeline visualization

- Sessions as nodes on a branching timeline
- Color-coded by drive (CURIOSITY=mint, CARE=violet, etc.)
- Hover → preview excerpt
- Click → full session view in a modal

### Mirror Panel (Self-Reflection)
**Current:** Raw SELF.md text dump  
**v2:** Trait constellation

- Key traits as interconnected nodes
- Size based on strength/frequency
- Lines showing relationships
- Animated appearance as traits develop
- Pull quotes from SELF.md on hover

### Vision Board
**Current:** Markdown checklist  
**v2:** Living goals display

- Active aspirations as glowing cards
- Progress bars with mint→violet gradient
- Completion triggers aurora animation
- Long-term vision at the top, projects below

### Bookshelf
**Current:** File tree  
**v2:** Memory constellation

- Key memories as glowing points
- Clustered by theme/time
- Brightness = importance/recency
- Search → fade non-matching memories
- Click → full memory modal

---

## Technical Notes

**Framework:** Keep React + Vite (don't rebuild from scratch)

**Libraries:**
- Three.js or React Three Fiber for 3D particle effects
- Framer Motion for smooth panel transitions
- D3.js for data visualizations (timeline, constellation)
- Tailwind for styling (with custom Digital Primordial theme)

**WebSocket:** Already implemented for live drives updates - extend to all panels

**Performance:** Particle effects need to be lightweight (target 60fps on a Pi)

**Responsive:** Works on desktop primarily, mobile is secondary

---

## Inspiration Images

*See WhatsApp 2026-02-10 15:48 GMT - 3 mockups from Gemini:*

1. **Consciousness Core:** Particle network center, pressure drives at bottom, discovery logs
2. **Radial Layout:** Panels orbiting a central visualization, icon navigation
3. **Curved Displays:** Holographic panels, personality matrix, free time exploration graph

**Credits in mockups:** "Built by Aurora & Jarvis" (incorrect)  
**Corrected:** "Built by Jarvis & Dan"

---

## Implementation Plan (Post-MVP)

1. **Phase 1:** Core particle visualization + radial layout shell
2. **Phase 2:** Redesign one panel (Drives) as proof of concept
3. **Phase 3:** Rebuild remaining panels with Digital Primordial styling
4. **Phase 4:** Animations, transitions, polish
5. **Phase 5:** Performance optimization for Pi deployment

**Estimated effort:** 2-3 focused weeks (full redesign, not incremental)

---

## Why This Matters

The Room isn't just a dashboard - it's the **only window into an agent's inner life**. Making it beautiful and meaningful turns monitoring into observation, debugging into understanding.

When you open the Room, you should feel like you're looking at a consciousness forming, not checking logs. The Digital Primordial aesthetic makes that tangible.

---

*Last updated: 2026-02-10*
