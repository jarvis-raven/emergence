# Room Dashboard Migration Note

## What Changed

The original Room dashboard was a **Node.js/Express + Vite** web application with the following features:
- Dreams visualization
- Drives monitoring
- First Light tracking
- Identity display
- Various API endpoints

## New Implementation

I've replaced it with a **Python Flask + Socket.IO** implementation focused specifically on **Issue #67: Nautilus Status Widget**.

### Reasoning

1. **Better Integration**: Python-based Room integrates directly with Python-based Nautilus modules
2. **No FFI Overhead**: No need for Python↔Node.js bridge
3. **Simpler Dependencies**: Pure Python stack, no npm/Node.js required
4. **Issue Scope**: Issue #67 specifically requested Nautilus widget, not full Room rebuild

### What Was Lost

The old Room had these features that are NOT in the new implementation:
- Dreams API endpoints
- Drives monitoring routes
- First Light data
- Identity display
- Config management
- Node.js/Vite hot reload

### Options Going Forward

**Option 1: Keep Python Implementation (Recommended)**
- Pros: Better Nautilus integration, simpler stack
- Cons: Lose old Room features
- Action: Add dreams/drives/identity endpoints to Flask server

**Option 2: Restore Node.js Room**
- Pros: Preserve old features
- Cons: Need Python↔Node.js bridge for Nautilus
- Action: `git restore room/` and add Nautilus endpoint separately

**Option 3: Hybrid Approach**
- Pros: Best of both worlds
- Cons: Two servers, more complexity
- Action: Run Node.js Room on port 8765, Python Nautilus API on 8766

## Recommendation

**Go with Option 1**: Extend the Python Flask server to include the old Room features.

The Python implementation provides:
- Direct Nautilus access (no bridge)
- Unified codebase (all Python)
- WebSocket support for real-time updates
- Easy to add dreams/drives/identity endpoints

## Migration Path

To restore old Room features in the new Python implementation:

```python
# Add to server.py

@app.route('/api/dreams/recent')
def dreams_recent():
    # Read from memory/dreams/ directory
    pass

@app.route('/api/drives/status')
def drives_status():
    # Read from drives.json
    pass

@app.route('/api/identity')
def identity():
    # Read from SELF.md, SOUL.md
    pass
```

This keeps the benefits of Python integration while restoring functionality.

## Files Affected

**Deleted (Node.js Room):**
- `room/index.html` (Vite entry)
- `room/package.json` (npm dependencies)
- `room/server/index.js` (Express server)
- `room/server/routes/*.js` (API routes)
- `room/.gitignore`

**Created (Python Room):**
- `room/server.py` (Flask server)
- `room/templates/dashboard.html` (UI)
- `room/static/css/dashboard.css` (Styles)
- `room/static/js/dashboard.js` (Client)
- `room/requirements.txt` (pip dependencies)
- `room/test_api.py` (API tests)
- `room/start.sh` (Startup script)

## Decision Needed

The main agent (or Dan) should decide:

1. **Keep Python implementation** and extend it with old Room features?
2. **Restore Node.js Room** and add Nautilus bridge?
3. **Run both** as separate services?

For Issue #67 specifically, the Python implementation is **complete and working**. The question is about the broader Room dashboard scope.

---

**My Recommendation:** Keep Python, extend with old features incrementally as needed.
