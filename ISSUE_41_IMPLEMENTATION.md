# Issue #41: Thwarting Detection Logic - Implementation Summary

**Issue:** https://github.com/jarvis-raven/emergence/issues/41  
**Branch:** `feature/issue-41-thwarting-detection`  
**Date:** 2026-02-13

## Overview

Implemented comprehensive thwarting detection logic that identifies when drives are being systematically thwarted (triggered repeatedly without satisfaction). This builds on #40's valence tracking foundation and provides the basis for #42's aversive-specific satisfaction mechanisms.

## Implementation Details

### 1. Core Thwarting Detection Module (`core/drives/thwarting.py`)

Created new module with comprehensive thwarting detection:

**Key Functions:**

- `is_thwarted()` - Boolean check for thwarted state (≥3 triggers OR ≥150% pressure)
- `get_thwarting_status()` - Detailed status dict with reason, counts, and valence
- `get_thwarted_drives()` - Scan state for all thwarted drives, sorted by severity
- `format_thwarting_message()` - Human-readable messages like "CREATIVE is thwarted (4 triggers, no satisfaction) at 180%"
- `get_thwarting_emoji()` - Visual indicators (⚠3 for thwarted with count)

**Detection Criteria:**

- **Consecutive triggers:** thwarting_count ≥ 3
- **Extreme pressure:** pressure ≥ 150% of threshold
- Either condition triggers thwarted state

**Reason Tracking:**

- `consecutive_triggers` - Drive triggered 3+ times without satisfaction
- `extreme_pressure` - Pressure sustained at crisis levels (≥150%)

### 2. CLI Integration (`core/drives/cli.py`)

**Updated Functions:**

- Imported thwarting detection functions
- `_print_drive_line()` - Now uses `get_thwarting_emoji()` for cleaner valence/thwarting display
- `cmd_status()` - Added dedicated "Thwarted Drives" section that:
  - Shows all thwarted drives prominently in red
  - Displays formatted messages explaining thwarting reason
  - Provides suggested actions (deep/full satisfaction)
  - Appears right after "Active Drives" for visibility

**Dashboard Display:**

```
⚠️  Thwarted Drives: 2
  ⚠ CREATIVE is thwarted (4 triggers, no satisfaction) at 180%
  ⚠ SOCIAL is thwarted (extreme pressure: 165%, 1 triggers)
    These drives need immediate attention or investigation
    Use 'drives satisfy <name> deep' or 'full' for relief
```

### 3. Comprehensive Test Suite (`core/drives/tests/test_thwarting_detection.py`)

**35 Tests Covering:**

- Detection logic (normal, triggered, extreme pressure states)
- Boundary conditions (exactly 150%, just below, edge cases)
- Status reporting and message formatting
- State scanning and sorting by severity
- Integration with drive engine (trigger, satisfy, bump)
- Valence alignment with thwarting status
- Edge cases (zero threshold, negative pressure, missing fields)

**Test Classes:**

- `TestIsThwarted` - Core detection function (9 tests)
- `TestGetThwartingStatus` - Detailed status reporting (4 tests)
- `TestGetThwartedDrives` - State scanning and sorting (5 tests)
- `TestFormatThwartingMessage` - Message formatting (3 tests)
- `TestGetThwartingEmoji` - Visual indicators (4 tests)
- `TestThwartingIntegrationWithEngine` - Integration tests (5 tests)
- `TestEdgeCases` - Boundary and error conditions (5 tests)

### 4. Package Exports (`core/drives/__init__.py`)

Added thwarting functions to package exports for programmatic use:

- `is_thwarted`
- `get_thwarting_status`
- `get_thwarted_drives`
- `format_thwarting_message`
- `get_thwarting_emoji`

## Acceptance Criteria Met

- ✅ **System identifies drives in aversive state** - `is_thwarted()` detects valence == 'aversive'
- ✅ **CLI shows thwarting status clearly** - Dedicated "Thwarted Drives" section with formatted messages
- ✅ **Dashboard highlights thwarted drives** - Red color coding, ⚠ emoji, prominent placement
- ✅ **Thwarting detection at ≥3 triggers OR ≥150%** - Both conditions implemented and tested
- ✅ **Tests cover thwarting patterns** - 35 comprehensive tests, all passing

## Integration with Existing Features

**Builds on #40 (Valence Tracking):**

- Uses existing `valence` field from drives
- Uses existing `thwarting_count` field
- Leverages `calculate_valence()` for consistency
- `mark_drive_triggered()` already increments count
- `satisfy_drive()` already resets count

**Foundation for #42 (Aversive Satisfaction):**

- `is_thwarted()` can be used to trigger different satisfaction prompts
- `get_thwarting_status()` provides reason for choosing aversive approach
- Dashboard visibility makes intervention timing clear

## Test Results

```bash
core/drives/tests/test_thwarting_detection.py
  35 passed in 0.08s ✅

core/drives/tests/test_valence.py
  23 passed in 0.05s ✅ (existing tests still pass)
```

## Files Changed

**New Files:**

- `core/drives/thwarting.py` (252 lines)
- `core/drives/tests/test_thwarting_detection.py` (619 lines)
- `ISSUE_41_IMPLEMENTATION.md` (this file)

**Modified Files:**

- `core/drives/cli.py` - Added thwarting imports, updated `_print_drive_line()`, added thwarted drives section in `cmd_status()`
- `core/drives/__init__.py` - Added thwarting function exports

## Usage Examples

### Programmatic Use

```python
from core.drives import is_thwarted, get_thwarted_drives

# Check if single drive is thwarted
drive = state["drives"]["CREATIVE"]
if is_thwarted(drive):
    print("CREATIVE needs attention!")

# Find all thwarted drives
thwarted = get_thwarted_drives(state, config)
for thw in thwarted:
    print(f"{thw['name']}: {thw['reason']}")
```

### CLI Use

```bash
# View thwarted drives in status
emergence drives status

# Satisfy thwarted drive
emergence drives satisfy CREATIVE deep
```

## Next Steps (Issue #42)

This implementation provides the foundation for aversive-specific satisfaction mechanisms:

1. Use `is_thwarted()` to detect when to use aversive prompts
2. Use `get_thwarting_status()` reason to customize satisfaction approach
3. Differentiate between "do the thing" (appetitive) and "address blockage" (aversive)
4. Track effectiveness of aversive satisfaction methods

## Notes

- Detection is conservative (3+ triggers, 150%+) to avoid false positives
- Sorted by severity ensures worst cases show first
- Visual indicators (⚠3) communicate both state and count
- Integration with existing valence system ensures consistency
- All existing tests still pass - no regressions
