import { useMemo } from 'react';
import { 
  enrichDriveWithThresholds, 
  getBandColors,
  DEFAULT_THRESHOLD_RATIOS 
} from '../utils/thresholds.js';

/**
 * Get animation state based on threshold band
 * 
 * @param {string} band - Threshold band name
 * @returns {object} Animation state config
 */
function getAnimationForBand(band) {
  switch (band) {
    case 'emergency':
      return { animation: 'animate-pulse-fast', glow: true };
    case 'crisis':
      return { animation: 'animate-pulse-fast', glow: true };
    case 'triggered':
      return { animation: 'animate-pulse-medium', glow: false };
    case 'elevated':
      return { animation: 'animate-pulse-slow', glow: false };
    default:
      return { animation: '', glow: false };
  }
}

/**
 * Vertical pressure bar component with graduated threshold visualization
 * 
 * Shows color-coded bands and threshold markers to visualize drive state.
 * 
 * @param {object} props
 * @param {object} props.drive - Drive data object with pressure and threshold
 * @param {boolean} props.isHighest - Whether this is the highest pressure drive
 * @param {function} props.onClick - Click handler
 * @param {boolean} props.showDetails - Whether to show extended details
 * @param {boolean} props.showThresholdMarkers - Whether to show threshold lines
 */
export function PressureBar({ 
  drive, 
  isHighest = false, 
  onClick,
  showDetails = false,
  showThresholdMarkers = true,
}) {
  // Enrich drive with threshold data
  const enrichedDrive = useMemo(() => enrichDriveWithThresholds(drive), [drive]);
  
  const { 
    name, 
    pressure, 
    threshold, 
    percentage, 
    band, 
    bandIcon, 
    thresholds,
    bandColors 
  } = enrichedDrive;
  
  const animationState = useMemo(() => getAnimationForBand(band), [band]);
  
  // Clamp display height to 100% for container, but show overflow with visual indicators
  const displayHeight = Math.min(percentage, 100);
  
  // Calculate threshold marker positions (as % of bar height)
  const markerPositions = useMemo(() => ({
    available: DEFAULT_THRESHOLD_RATIOS.available * 100,
    elevated: DEFAULT_THRESHOLD_RATIOS.elevated * 100,
    triggered: 100, // This is always at the top
  }), []);

  return (
    <div 
      className={`
        flex flex-col items-center justify-end cursor-pointer
        transition-transform duration-200
        ${isHighest ? 'scale-105' : ''}
        ${onClick ? 'hover:scale-110' : ''}
      `}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
      aria-label={`${name}: ${percentage}% pressure (${band})`}
    >
      {/* Icon and status row */}
      <div 
        className={`
          text-xs mb-1 flex items-center gap-1
          ${bandColors.text}
        `}
      >
        {bandIcon && <span aria-hidden="true">{bandIcon}</span>}
        {isHighest && band === 'available' && <span aria-hidden="true">⚡</span>}
      </div>

      {/* Vessel container */}
      <div 
        className={`
          relative w-12 h-28 bg-surface rounded-lg border-2 overflow-hidden
          transition-all duration-300
          ${bandColors.border}
          ${animationState.glow ? `${bandColors.shadow} shadow-lg` : ''}
        `}
      >
        {/* Threshold markers */}
        {showThresholdMarkers && (
          <>
            {/* Available threshold (30%) */}
            <div 
              className="absolute left-0 right-0 border-t border-dashed border-emerald-500/30 z-10"
              style={{ bottom: `${markerPositions.available}%` }}
              aria-hidden="true"
              title="Available threshold (30%)"
            />
            
            {/* Elevated threshold (75%) */}
            <div 
              className="absolute left-0 right-0 border-t border-dashed border-yellow-500/40 z-10"
              style={{ bottom: `${markerPositions.elevated}%` }}
              aria-hidden="true"
              title="Elevated threshold (75%)"
            />
            
            {/* Triggered threshold (100%) - top edge */}
            <div 
              className="absolute top-0 left-0 right-0 border-t-2 border-dashed border-orange-500/50 z-10"
              aria-hidden="true"
              title="Triggered threshold (100%)"
            />
          </>
        )}
        
        {/* Fill bar with gradient based on band */}
        <div 
          className={`
            absolute bottom-0 left-0 right-0 
            rounded-b-md transition-all duration-500 ease-out
            ${animationState.animation}
          `}
          style={{ 
            height: `${displayHeight}%`,
            background: `linear-gradient(to top, ${bandColors.gradient.from}, ${bandColors.gradient.to})`,
          }}
          aria-hidden="true"
        />
        
        {/* Overflow glow for crisis/emergency drives */}
        {animationState.glow && (
          <div 
            className={`absolute inset-0 ${bandColors.bg} ${animationState.animation}`}
            aria-hidden="true"
          />
        )}
        
        {/* Percentage label */}
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <span 
            className={`
              font-mono font-bold text-xs 
              drop-shadow-lg
              ${percentage > 40 ? 'text-white' : 'text-text'}
            `}
          >
            {percentage}%
          </span>
        </div>
      </div>

      {/* Drive name */}
      <div 
        className={`
          text-[9px] font-mono mt-1 uppercase tracking-wider
          ${bandColors.text}
        `}
      >
        {name}
      </div>

      {/* Extended details */}
      {showDetails && (
        <div className="text-[8px] text-textMuted mt-1 text-center space-y-0.5">
          <div>{pressure?.toFixed?.(1) || pressure}/{threshold}</div>
          <div className={`${bandColors.text} font-semibold`}>
            {band}
          </div>
        </div>
      )}
    </div>
  );
}

export default PressureBar;
