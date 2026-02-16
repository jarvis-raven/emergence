/**
 * Threshold utilities for the graduated threshold system
 *
 * Graduated thresholds are ratios applied to each drive's base threshold:
 * - available: 30% (drive is present but not pressing)
 * - elevated: 75% (drive is building, noticeable)
 * - triggered: 100% (drive triggers autonomous action)
 * - crisis: 150% (high urgency, sustained neglect)
 * - emergency: 200% (critical, needs immediate attention)
 */

/**
 * Default threshold ratios (matches core/drives/config.py)
 */
export const DEFAULT_THRESHOLD_RATIOS = {
  available: 0.3,
  elevated: 0.75,
  triggered: 1.0,
  crisis: 1.5,
  emergency: 2.0,
};

/**
 * Threshold band color schemes
 */
export const THRESHOLD_COLORS = {
  available: {
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/50',
    text: 'text-emerald-600',
    shadow: 'shadow-emerald-500/20',
    gradient: { from: '#10b981', to: '#34d399' }, // emerald-500 to emerald-400
  },
  elevated: {
    bg: 'bg-yellow-500/20',
    border: 'border-yellow-500/50',
    text: 'text-yellow-600',
    shadow: 'shadow-yellow-500/20',
    gradient: { from: '#eab308', to: '#facc15' }, // yellow-500 to yellow-400
  },
  triggered: {
    bg: 'bg-orange-500/20',
    border: 'border-orange-500/50',
    text: 'text-orange-600',
    shadow: 'shadow-orange-500/20',
    gradient: { from: '#f97316', to: '#fb923c' }, // orange-500 to orange-400
  },
  crisis: {
    bg: 'bg-red-500/20',
    border: 'border-red-500/50',
    text: 'text-red-600',
    shadow: 'shadow-red-500/20',
    gradient: { from: '#ef4444', to: '#f87171' }, // red-500 to red-400
  },
  emergency: {
    bg: 'bg-purple-500/20',
    border: 'border-purple-500/50',
    text: 'text-purple-600',
    shadow: 'shadow-purple-500/20',
    gradient: { from: '#a855f7', to: '#c084fc' }, // purple-500 to purple-400
  },
  // Special state for drives below available threshold (dim)
  neutral: {
    bg: 'bg-surface/50',
    border: 'border-surface',
    text: 'text-textMuted',
    shadow: 'shadow-none',
    gradient: { from: '#6b7280', to: '#9ca3af' }, // gray-500 to gray-400
  },
};

/**
 * Threshold band icons
 */
export const THRESHOLD_ICONS = {
  available: '✓',
  elevated: '⚡',
  triggered: '🔥',
  crisis: '⚠️',
  emergency: '🚨',
  neutral: '—',
};

/**
 * Threshold band labels (human-readable)
 */
export const THRESHOLD_LABELS = {
  available: 'Available',
  elevated: 'Elevated',
  triggered: 'Triggered',
  crisis: 'Crisis',
  emergency: 'Emergency',
  neutral: 'Neutral',
};

/**
 * Compute graduated thresholds for a drive
 *
 * @param {number} baseThreshold - The drive's base threshold (100% point)
 * @param {object} customRatios - Optional custom threshold ratios
 * @returns {object} Graduated thresholds { available, elevated, triggered, crisis, emergency }
 */
export function computeGraduatedThresholds(baseThreshold, customRatios = null) {
  const ratios = customRatios || DEFAULT_THRESHOLD_RATIOS;

  return {
    available: baseThreshold * ratios.available,
    elevated: baseThreshold * ratios.elevated,
    triggered: baseThreshold * ratios.triggered,
    crisis: baseThreshold * ratios.crisis,
    emergency: baseThreshold * ratios.emergency,
  };
}

/**
 * Determine which threshold band a drive's pressure falls into
 *
 * @param {number} pressure - Current pressure value
 * @param {object} thresholds - Graduated thresholds object
 * @returns {string} Band name: neutral|available|elevated|triggered|crisis|emergency
 */
export function getThresholdBand(pressure, thresholds) {
  // Check from highest to lowest
  if (pressure >= thresholds.emergency) {
    return 'emergency';
  } else if (pressure >= thresholds.crisis) {
    return 'crisis';
  } else if (pressure >= thresholds.triggered) {
    return 'triggered';
  } else if (pressure >= thresholds.elevated) {
    return 'elevated';
  } else if (pressure >= thresholds.available) {
    return 'available';
  } else {
    return 'neutral';
  }
}

/**
 * Get color scheme for a threshold band
 *
 * @param {string} band - Band name
 * @returns {object} Color scheme object
 */
export function getBandColors(band) {
  return THRESHOLD_COLORS[band] || THRESHOLD_COLORS.neutral;
}

/**
 * Get icon for a threshold band
 *
 * @param {string} band - Band name
 * @returns {string} Icon emoji
 */
export function getBandIcon(band) {
  return THRESHOLD_ICONS[band] || THRESHOLD_ICONS.neutral;
}

/**
 * Get human-readable label for a threshold band
 *
 * @param {string} band - Band name
 * @returns {string} Label text
 */
export function getBandLabel(band) {
  return THRESHOLD_LABELS[band] || 'Unknown';
}

/**
 * Enrich a drive object with threshold data
 *
 * @param {object} drive - Drive object with pressure and threshold
 * @returns {object} Drive with added thresholds, band, and bandColors
 */
export function enrichDriveWithThresholds(drive) {
  const thresholds = computeGraduatedThresholds(drive.threshold);
  const band = getThresholdBand(drive.pressure, thresholds);
  const bandColors = getBandColors(band);

  return {
    ...drive,
    thresholds,
    band,
    bandColors,
    bandIcon: getBandIcon(band),
    bandLabel: getBandLabel(band),
  };
}

/**
 * Group drives by threshold band
 *
 * @param {Array} drives - Array of drive objects
 * @returns {object} Drives grouped by band { emergency: [], crisis: [], ... }
 */
export function groupDrivesByBand(drives) {
  const groups = {
    emergency: [],
    crisis: [],
    triggered: [],
    elevated: [],
    available: [],
    neutral: [],
  };

  drives.forEach((drive) => {
    const enriched = enrichDriveWithThresholds(drive);
    groups[enriched.band].push(enriched);
  });

  return groups;
}
