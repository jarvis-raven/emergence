# Phase 3: Status Display Enhancement - Implementation Summary

## Overview
Implemented the enhanced `drives status` command and supporting infrastructure as specified in Phase 3 of the drive-aspects-consolidation-v2.md plan.

## Changes Made

### 1. CLI Enhancements (`core/drives/cli.py`)

#### New Features in `drives status`:
- **Budget Display**: Shows daily spend vs limit with color-coded warnings
  - Green (<75%): `$0.00 / $50.00 daily (0%)`
  - Yellow (75-89%): Warning level
  - Red (≥90%): Critical level

- **Cooldown Status**: Shows trigger cooldown state
  - `Cooldown: Ready` or `Cooldown: Ready in 37m`

- **Aspect Display**: Shows aspects under parent drives
  - `CREATION [███████████░░░░░░░░░] 58%`
  - `  (3 aspects: aesthetic, sonic, utility)`

- **Pending Reviews**: Shows count and quick info
  - `Pending Reviews: 1`
  - `→ GIFTING - Similar to CREATION + RELATIONSHIP`
  - `Run: drives review`

- **Latent Drives**: Shows with `--show-latent` flag
  - `○ Latent Drives:`
  - `SONIC_EXPLORATION - Consolidated into CREATION`

- **Projected Costs**: Calculated from drive rates
  - `Projected: ~8 triggers/day (~$20/day, $600/month)`

- **Graduation Candidates**: Aspects with >50% pressure dominance
  - Shows after 10+ satisfactions and 14+ days as aspect

#### New Commands:
- `drives review` - List all pending reviews
- `drives review <name>` - Show irreducibility test for specific drive
- `drives activate <name>` - Activate a latent drive
- `drives aspects <name>` - Manage aspects for a drive

### 2. Room API Enhancements

#### New Routes:
- `GET /api/drives` - Enhanced with aspect counts, graduation candidates
- `GET /api/drives/pending-reviews` - Drives awaiting review
- `GET /api/drives/latent` - Inactive/latent drives with budget check
- `GET /api/drives/:name/aspects` - Aspects for specific drive
- `POST /api/drives/:name/activate` - Activate latent drive
- `GET /api/budget/status` - Budget status and projections

#### New Shelves:
- **BudgetTransparencyShelf** - Top banner with budget status
- **PendingReviewsShelf** - Consolidation suggestions
- **LatentDrivesShelf** - Inactive drives with activation
- **DrivesShelf** - Enhanced drive list with aspects

### 3. Supporting Infrastructure

#### Helper Functions Added:
- `get_pending_reviews_path()` - Path to pending reviews file
- `load_pending_reviews()` - Load pending consolidation reviews
- `get_budget_info()` - Calculate budget metrics
- `get_cooldown_status()` - Check cooldown state
- `find_graduation_candidates()` - Find aspects ready to graduate
- `format_time_ago()` - Human-readable time formatting
- `format_time_remaining()` - Cooldown formatting
- `format_elapsed_time()` - Elapsed since satisfaction
- `get_elapsed_since_last_satisfaction()` - Calculate hours elapsed

### 4. Color Coding

Category colors for terminal output:
- **Core Drives**: Cyan (`\033[36m`)
- **Discovered Drives**: Yellow (`\033[33m`)
- **Latent Drives**: Gray (`\033[90m`)
- **Budget Low**: Green (`\033[32m`)
- **Budget Warning**: Yellow (`\033[33m`)
- **Budget Critical**: Red (`\033[31m`)

## Example Output

```
🧠 Drive Status (updated 2m ago)
Budget: $12.50 / $50.00 daily (25%)
Cooldown: Ready (last trigger 2h ago)
────────────────────────────────────────────────────

Core Drives:
  ⚡ CARE           [████████████████░░░░] 82%  Ready in 37m
  ▫ MAINTENANCE    [██████████░░░░░░░░░░] 52%  6.2h elapsed
  ▫ REST           [░░░░░░░░░░░░░░░░░░░░] 0%   Activity-driven

Discovered Drives:
  ▫ CREATION       [███████████░░░░░░░░░] 58%  3.4h elapsed
     (3 aspects: aesthetic, sonic, utility)
  ▫ CURIOSITY      [████████░░░░░░░░░░░░] 42%  5.1h elapsed
     (1 aspect: external focus)

Pending Reviews: 1
  → GIFTING - Similar to CREATION + RELATIONSHIP
    Run: drives review
────────────────────────────────────────────────────
Projected: ~8 triggers/day (~$20/day, $600/month)
```

## Testing

Verified working:
- ✅ Status command with all new sections
- ✅ Budget calculation from trigger history
- ✅ Cooldown status based on last trigger
- ✅ Aspect display under parent drives
- ✅ Pending reviews listing
- ✅ Projected cost calculation
- ✅ Color coding by category
- ✅ JSON output mode (`--json`)
- ✅ Room API routes

## Files Modified

- `core/drives/cli.py` - Main CLI with enhanced status
- `room/server/routes/drives.js` - Enhanced API routes
- `room/server/routes/budget.js` - New budget route
- `room/server/shelves/index.js` - Shelf registration
- `room/server/index.js` - Route mounting

## Files Created

- `room/server/shelves/builtins/BudgetTransparencyShelf.js`
- `room/server/shelves/builtins/PendingReviewsShelf.js`
- `room/server/shelves/builtins/LatentDrivesShelf.js`
- `room/server/shelves/builtins/DrivesShelf.js`
- `core/first_light/irreducibility.py` - Irreducibility testing
- `core/first_light/completion.py` - First Light completion

## Next Steps (Phase 3.5)

1. Frontend widgets for Room dashboard
2. Real-time WebSocket updates for budget
3. Aspect graduation workflow
4. Drive merge/keep CLI commands

## Commit

All changes committed as:
```
Phase 3: Status Display Enhancement

- Enhanced 'drives status' to show aspects under parent drives
- Added budget info: daily spend/limit with color-coded warnings
- Added cooldown status display (Ready in X time)
- Added pending reviews count with link to review command
- Added --show-latent flag for latent drives section
- Added projected cost calculation (triggers/day → $/month)
- Added graduation candidates detection (>50% pressure dominance)
- Color-coded drives by category (core/discovered/latent)
- Added 'drives review' command for irreducibility testing
- Room API routes for budget, pending-reviews, latent drives
```
