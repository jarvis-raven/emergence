# Nautilus Widget Integration — Issue #67 ✅

**Status:** Complete  
**Date:** 2026-02-14  
**Integration Time:** ~15 minutes

## Summary

Successfully integrated the Nautilus memory system status visualization into the existing Node.js Room app. The widget displays real-time Nautilus architecture metrics including chambers, doors, mirrors, and gravity stats.

## What Was Added

### 1. Backend API Route

**File:** `room/server/routes/nautilus.js`

- GET `/api/nautilus/status` endpoint
- Calls emergence CLI: `python3 -m core.cli nautilus status`
- Returns normalized JSON with:
  - Gravity: chunks, accesses, DB stats
  - Chambers: atrium/corridor/unknown distribution
  - Doors: file tagging coverage
  - Mirrors: event reflection coverage
  - Summary files: corridor/vault counts

### 2. Built-in Shelf

**File:** `room/server/shelves/builtins/NautilusShelf.js`

- Shelf manifest with metadata
- Priority: 95 (just below Memory shelf)
- Refresh interval: 30 seconds
- Custom data resolver using emergence CLI

### 3. Widget Component

**File:** `room/src/components/Nautilus/NautilusWidget.jsx`

- Main visualization component (10KB)
- Sub-components:
  - `ChamberDistribution` — atrium/corridor/unknown bars
  - `CoverageCard` — door coverage percentage
  - `GravityStats` — chunk stats grid
  - `MirrorCoverage` — reflection layer breakdown
- Auto-refresh every 30 seconds via `useApi` hook
- Loading skeleton and error states
- Responsive design with Tailwind CSS

### 4. Shelf Renderer

**File:** `room/src/components/shelves/custom/NautilusShelfView.jsx`

- Thin wrapper component
- Integrates NautilusWidget into shelf system

### 5. Integration Points

**Modified Files:**

- `room/server/index.js` — imported and registered nautilus route
- `room/server/shelves/index.js` — registered NautilusShelf
- `room/src/components/ShelfPanel.jsx` — added Nautilus tab
- `room/src/components/shelves/ShelfRenderer.jsx` — registered renderer

## Features

✅ Real-time status updates (30s refresh)  
✅ Chamber distribution visualization (atrium/corridor/unknown)  
✅ Door coverage percentage with progress bar  
✅ Mirror coverage breakdown (raw/summary/lesson)  
✅ Gravity statistics (chunks, accesses, DB size)  
✅ Summary file counts (corridors/vaults)  
✅ Responsive design matching Room UI  
✅ Dark theme integration  
✅ Loading and error states  
✅ Matches existing component patterns

## API Endpoints

### Direct Endpoint

```bash
GET http://localhost:8801/api/nautilus/status
```

Response:

```json
{
  "timestamp": "2026-02-14T21:35:50.102Z",
  "gravity": {
    "total_chunks": 738,
    "total_accesses": 0,
    "superseded": 0,
    "db_size": 258048,
    "db_path": "/Users/jarvis/.openclaw/state/nautilus/gravity.db"
  },
  "chambers": {
    "atrium": 30,
    "corridor": 4,
    "unknown": 704,
    "total": 738,
    "categorized": 34,
    "coverage_pct": 4.61
  },
  "doors": {
    "tagged_files": 0,
    "total_files": 738,
    "coverage_pct": 0,
    "coverage_display": "0/738"
  },
  "mirrors": {
    "total_events": 0,
    "fully_mirrored": 0,
    "coverage": {
      "raw": 0,
      "summary": 0,
      "lesson": 0
    },
    "coverage_pct": 0
  },
  "summary_files": {
    "corridors": 0,
    "vaults": 0
  }
}
```

### Shelf Endpoint

```bash
GET http://localhost:8801/api/shelves/nautilus
```

## UI Integration

The Nautilus tab appears in the ShelfPanel between Memory and Journal:

- 🪞 Mirror
- 🧠 Memory
- **🐚 Nautilus** ← NEW
- 📓 Journal
- ✨ Aspirations
- 🚀 Projects

## Existing Features Preserved

✅ All drives functionality intact  
✅ Dreams panel working  
✅ First Light protocol unchanged  
✅ Memory shelf active  
✅ Journal/Workshop panel unchanged  
✅ Aspirations and Projects unchanged  
✅ WebSocket updates for drives still working

## Testing

### Server Test

```bash
cd ~/projects/emergence/room
npm run dev
```

Server starts on: http://0.0.0.0:8801  
Frontend: http://127.0.0.1:3000

### API Test

```bash
curl http://localhost:8801/api/nautilus/status | jq .
curl http://localhost:8801/api/shelves/nautilus | jq .
```

### Frontend Test

1. Open http://127.0.0.1:3000
2. Click Nautilus tab (🐚)
3. Verify visualizations load
4. Check auto-refresh (30s)

## Architecture Notes

### Why Built-in Shelf vs Custom?

- **Built-in shelves** are registered in code (server/shelves/builtins/)
- **Custom shelves** are discovered from state directory (user-specific)
- Nautilus is core infrastructure → built-in shelf is appropriate

### Data Flow

```
Frontend (NautilusWidget)
  ↓ useApi('/api/shelves/nautilus')
ShelfPanel → ShelfRenderer
  ↓ /api/shelves/nautilus
ShelfRegistry → NautilusShelf.resolveData()
  ↓ exec('python3 -m core.cli nautilus status')
Emergence CLI → Nautilus system
  ↓ returns JSON
Frontend displays visualization
```

### Real-time Updates

- Uses `useApi` hook with 30-second refresh interval
- No WebSocket needed (Nautilus state changes slowly)
- Future: could add WebSocket for real-time updates on memory events

## File Checklist

### Created

- [x] `room/server/routes/nautilus.js` (3.9KB)
- [x] `room/server/shelves/builtins/NautilusShelf.js` (3.8KB)
- [x] `room/src/components/Nautilus/NautilusWidget.jsx` (10KB)
- [x] `room/src/components/shelves/custom/NautilusShelfView.jsx` (328B)

### Modified

- [x] `room/server/index.js` (added import + route)
- [x] `room/server/shelves/index.js` (registered NautilusShelf)
- [x] `room/src/components/ShelfPanel.jsx` (added tab)
- [x] `room/src/components/shelves/ShelfRenderer.jsx` (registered renderer)

## Next Steps (Optional Enhancements)

- [ ] Add drill-down into individual chambers
- [ ] Show recent door tagging activity
- [ ] Display mirror coverage trends over time
- [ ] Add real-time WebSocket updates for memory events
- [ ] Create visualization for chunk access patterns
- [ ] Add filtering by chamber type
- [ ] Export Nautilus report as PDF

## Issue Resolution

**Issue #67:** Add Nautilus Widget to Node.js Room ✅

**Requirements Met:**

- ✅ API endpoint created following existing patterns
- ✅ Widget component matches Room UI/UX
- ✅ Integrated into ShelfPanel with tab
- ✅ Real-time updates via polling
- ✅ All existing features preserved
- ✅ No Python Flask code (Node.js only)
- ✅ Responsive design with Tailwind CSS
- ✅ Chart.js not needed (custom visualizations)

**Time Estimate:** 10-15 minutes ✅  
**Actual Time:** ~15 minutes ✅

---

**Integration complete. Nautilus visualization now live in The Room.**
