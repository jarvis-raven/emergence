# Real-Time Drive Updates Investigation

**Branch:** `spike/realtime-drive-updates`
**Goal:** Investigate WebSocket or SSE for real-time drive pressure updates
**Status:** Exploration / Proof of Concept

## Problem Statement

Current architecture (even with PR #9):
- Drive state loads at session start
- Becomes stale as daemon ticks in background
- Agent operates on outdated pressure values
- Heartbeat refresh every 30 min helps but isn't real-time

## Investigation Goals

1. **Can we push drive updates to active sessions in real-time?**
2. **WebSocket vs Server-Sent Events (SSE) - which is simpler?**
3. **What infrastructure changes are needed?**
4. **Proof of concept: working demo or clear failure mode**

## Option A: WebSockets (Bidirectional)

**Architecture:**
```
Daemon (ticks) → Gateway (WebSocket server) → Sessions (WebSocket clients)
```

**Pros:**
- Real-time bidirectional communication
- Can also receive messages from sessions
- Well-established protocol

**Cons:**
- Higher complexity
- Connection management (reconnects, heartbeats)
- Potential for race conditions
- More infrastructure

**Implementation sketch:**
```python
# daemon/tick.py
async def tick_and_broadcast(drives_state):
    for drive in drives_state.drives.values():
        drive.pressure += calculate_increment(drive)
        
    # Broadcast to all connected sessions
    await gateway_ws.broadcast({
        "type": "drive_update",
        "drive": "CARE",
        "pressure": 22.5,
        "threshold": 25.0
    })
```

## Option B: Server-Sent Events (SSE) - Preferred

**Architecture:**
```
Sessions (HTTP client) ← Gateway (SSE endpoint) ← Daemon (publishes updates)
```

**Pros:**
- Simpler than WebSockets (one-way only)
- Uses standard HTTP
- Automatic reconnection handling
- Less infrastructure

**Cons:**
- One-way only (server → client)
- Still needs connection management
- Browser/EventSource specific (but we can polyfill)

**Implementation sketch:**
```python
# gateway/sse_endpoint.py
@app.route('/events')
async def events():
    async def event_stream():
        while True:
            update = await drive_update_queue.get()
            yield f"data: {json.dumps(update)}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')
```

## Investigation Plan

### Phase 1: Research (1-2 hours)
- [ ] Read OpenClaw gateway code to understand session management
- [ ] Research SSE implementation patterns in Python/FastAPI
- [ ] Check if sessions can maintain persistent connections

### Phase 2: Minimal Prototype (2-4 hours)
- [ ] Create SSE endpoint in gateway
- [ ] Modify daemon to publish updates to a queue
- [ ] Test: Can sessions receive updates while running?
- [ ] Test: Does context actually update in real-time?

### Phase 3: Evaluate (1 hour)
- [ ] Does it work reliably?
- [ ] What's the latency?
- [ ] Complexity vs benefit?
- [ ] Decision: implement, iterate, or abandon?

## Key Questions

1. **Can OpenClaw sessions maintain long-lived connections?**
   - Sessions are typically request/response
   - Need to check if they can listen for events

2. **How do we patch context mid-session?**
   - Current: Context is built at session start, immutable
   - Need: Mechanism to update values without restarting session

3. **What happens on disconnect?**
   - SSE auto-reconnects, but may miss updates
   - Need fallback to periodic refresh

4. **Resource overhead?**
   - One connection per session
   - Small messages (~100 bytes per tick)
   - Acceptable for local gateway, maybe not for cloud

## Success Criteria

**Success:**
- Sessions receive drive updates within 5 seconds of daemon tick
- Context updates in real-time (visible to agent)
- No significant resource overhead
- Clean failure mode (falls back to periodic refresh)

**Failure (acceptable):**
- Sessions can't maintain connections
- Context can't be updated mid-session
- Complexity too high for benefit
- Document findings, stick with heartbeat refresh

## Documentation

If successful: Write implementation guide
If failed: Document why, what we tried, lessons learned

---

**Start date:** 2026-02-11
**Investigator:** Jarvis
**Status:** Initial exploration
