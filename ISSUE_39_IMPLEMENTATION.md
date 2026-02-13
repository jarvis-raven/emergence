# Issue #39 Implementation: Threshold Visualization in Room UI

## Summary

Added graduated threshold visualization to the Room UI, allowing users to see at a glance which threshold band each drive is in (neutral/available/elevated/triggered/crisis/emergency).

## Changes Made

### 1. New Threshold Utilities (`room/src/utils/thresholds.js`)

Created comprehensive utilities for the graduated threshold system:

**Core Functions:**
- `computeGraduatedThresholds()` - Computes the five threshold levels from a base threshold
- `getThresholdBand()` - Determines which band a drive's pressure falls into
- `enrichDriveWithThresholds()` - Adds threshold data to drive objects
- `groupDrivesByBand()` - Groups drives by their current band

**Threshold Bands:**
- **Neutral** (0-30%): Drive is present but minimal
- **Available** (30-75%): Drive is available but not pressing
- **Elevated** (75-100%): Drive is building, noticeable
- **Triggered** (100-150%): Drive triggers autonomous action
- **Crisis** (150-200%): High urgency, sustained neglect
- **Emergency** (200%+): Critical, needs immediate attention

**Color Schemes:**
Each band has dedicated colors:
- Neutral: Gray
- Available: Emerald green
- Elevated: Yellow
- Triggered: Orange
- Crisis: Red
- Emergency: Purple

### 2. Updated PressureBar Component

**Visual Enhancements:**
- Color-coded fill bars based on threshold band (not drive name)
- Threshold marker lines at 30%, 75%, and 100%
- Band-appropriate animations (pulse for crisis/emergency)
- Band-specific icons (✓, ⚡, 🔥, ⚠️, 🚨)
- Glow effects for urgent states

**Accessibility:**
- ARIA labels include band information
- Screen reader support for threshold state

### 3. Updated DrivePanel Component

**Grouping by Band:**
- Drives are now grouped by threshold band (emergency → neutral)
- Band headers show count (e.g., "Crisis (2)")
- Headers only appear for urgent bands or when multiple bands are active

**Status Display:**
- Header shows count of urgent drives (triggered or higher)
- Special highlight for emergency-level drives
- Maintains responsive design

**Horizontal Bars:**
- Color-coded based on band
- Threshold markers at 30% and 75%
- Smooth transitions between bands
- Band-appropriate hover states

### 4. Updated DriveCard Component

**Threshold Information:**
- Badge showing current band with icon
- Detailed threshold levels panel in expanded view
- Shows all five threshold values
- Current pressure/threshold display

**Visual Feedback:**
- Border and background colors match band
- Expanded cards maintain band color scheme

### 5. Updated DriveSidebar Component

**Consistency:**
- HorizontalBar now uses threshold colors
- Shows threshold markers at 30% and 75%
- Band icons displayed
- Consistent visual language with main panel

## Implementation Notes

### Threshold Ratios

The system uses the same ratios as the Python backend (`core/drives/config.py`):

```javascript
{
  available: 0.30,    // 30%
  elevated: 0.75,     // 75%
  triggered: 1.0,     // 100%
  crisis: 1.5,        // 150%
  emergency: 2.0,     // 200%
}
```

### Backward Compatibility

- Works with existing drive data structure
- Computes thresholds client-side from base threshold
- No backend changes required
- Falls back gracefully if threshold data missing

### Visual Design Principles

1. **Color consistency**: Each band has a dedicated color across all components
2. **Progressive urgency**: Colors progress from cool (green) to hot (red/purple)
3. **Clear markers**: Dashed lines show threshold boundaries
4. **Animation priority**: Only crisis/emergency drives pulse
5. **Accessibility first**: ARIA labels, keyboard navigation, screen reader support

## Testing

Created comprehensive test suite in `thresholds.test.js`:
- Threshold computation tests
- Band detection tests
- Grouping logic tests
- Edge case handling

**Build Status:** ✓ All components compile successfully

## User-Facing Changes

### What Users See:

1. **Drive bars change color based on urgency**, not drive type
   - Green = available/healthy
   - Yellow = getting elevated
   - Orange = triggered
   - Red = crisis
   - Purple = emergency

2. **Threshold markers** show when drives will change state
   - Dashed lines at 30%, 75%, and 100%
   - Helps anticipate when action is needed

3. **Drives are grouped by urgency level**
   - Emergency drives at top
   - Neutral drives at bottom
   - Easy to scan for what needs attention

4. **Expanded cards show detailed threshold info**
   - See exact values for each threshold
   - Current band highlighted
   - Understand where the drive is in its cycle

5. **Consistent visual language** across all UI components
   - Icons indicate band (✓ ⚡ 🔥 ⚠️ 🚨)
   - Colors match between sidebar, panel, and cards

## Acceptance Criteria

✅ **Drive cards show current threshold band with color**
- Color-coded based on band (green/yellow/orange/red/purple)
- Icons indicate state (✓/⚡/🔥/⚠️/🚨)

✅ **Pressure bars reflect band boundaries**
- Threshold markers at 30%, 75%, 100%
- Fill color matches current band
- Smooth transitions between states

✅ **Dashboard groups drives by band**
- Emergency/crisis/triggered at top
- Available/neutral at bottom
- Band headers show counts

✅ **Visual distinction between bands**
- Unique color schemes per band
- Icons for quick identification
- Animations for urgent states
- Glows for crisis/emergency

✅ **Responsive design**
- Works on mobile and desktop
- Maintains clarity at all sizes
- Consistent across components

## Dependencies

- Issue #37 ✓ (Graduated threshold system - merged)
- Issue #38 ✓ (Satisfaction depth - merged)

## Future Enhancements

Potential improvements for future iterations:

1. **User Preferences**
   - Customizable threshold ratios per drive
   - Color scheme preferences
   - Animation intensity settings

2. **Advanced Visualizations**
   - Sparklines showing pressure history
   - Prediction of when drives will trigger
   - Time-to-threshold estimates

3. **Smart Notifications**
   - Browser notifications when drives hit crisis
   - Subtle pulse animations approaching thresholds
   - "Satisfying soon" indicators

4. **Accessibility**
   - High contrast mode
   - Color-blind friendly palettes
   - Configurable icon sets

## Files Changed

```
room/src/utils/thresholds.js              (new)
room/src/utils/thresholds.test.js         (new)
room/src/components/PressureBar.jsx       (updated)
room/src/components/DrivePanel.jsx        (updated)
room/src/components/DriveCard.jsx         (updated)
room/src/components/DriveSidebar.jsx      (updated)
```

## Commit Message

```
feat: add threshold visualization to Room UI (#39)

Implements graduated threshold bands with visual indicators:
- Color-coded pressure bars (green→yellow→orange→red→purple)
- Threshold markers at 30%, 75%, 100%
- Drives grouped by urgency level (emergency → neutral)
- Band-specific icons and animations
- Detailed threshold info in expanded drive cards

Users can now see at a glance:
- Which drives need attention (crisis/emergency)
- How close drives are to triggering
- Visual progression of drive pressure over time

All acceptance criteria met. Responsive design maintained.
```
