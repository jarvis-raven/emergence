import { useMemo } from 'react';
import { getDriveColor } from '../context/ThemeContext.jsx';

/**
 * Get animation state based on pressure percentage
 * 
 * @param {number} percentage - Pressure percentage (0-100+)
 * @returns {object} Animation state config
 */
function getPressureState(percentage) {
  if (percentage >= 100) {
    return { 
      animation: 'animate-pulse-fast', 
      glow: true, 
      icon: '🔥',
      intensity: 'triggered' 
    };
  }
  if (percentage >= 70) {
    return { 
      animation: 'animate-pulse-medium', 
      glow: false, 
      icon: null,
      intensity: 'high' 
    };
  }
  if (percentage >= 30) {
    return { 
      animation: 'animate-pulse-slow', 
      glow: false, 
      icon: null,
      intensity: 'medium' 
    };
  }
  return { 
    animation: '', 
    glow: false, 
    icon: null,
    intensity: 'calm' 
  };
}

/**
 * Vertical pressure bar component (vessel metaphor)
 * 
 * @param {object} props
 * @param {object} props.drive - Drive data object
 * @param {number} props.drive.pressure - Current pressure value
 * @param {number} props.drive.threshold - Pressure threshold
 * @param {number} props.drive.percentage - Computed percentage
 * @param {string} props.drive.name - Drive name
 * @param {boolean} props.isHighest - Whether this is the highest pressure drive
 * @param {boolean} props.isTriggered - Whether drive is in triggered state
 * @param {function} props.onClick - Click handler
 * @param {boolean} props.showDetails - Whether to show extended details
 */
export function PressureBar({ 
  drive, 
  isHighest = false, 
  onClick,
  showDetails = false,
}) {
  const { name, percentage, isTriggered } = drive;
  
  const state = useMemo(() => getPressureState(percentage), [percentage]);
  
  // Get gradient colors for this drive (auto-assigns for discovered drives)
  const colors = getDriveColor(name);
  
  // Clamp height to container for display, but show overflow with glow
  const displayHeight = Math.min(percentage, 100);

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
      aria-label={`${name}: ${percentage}% pressure`}
    >
      {/* Icon row */}
      <div 
        className={`
          text-[10px] font-mono mb-1 flex items-center gap-1
          ${isTriggered ? 'text-warning' : isHighest ? 'text-success' : 'text-textMuted'}
        `}
      >
        {state.icon && <span aria-hidden="true">{state.icon}</span>}
        {isHighest && !isTriggered && <span aria-hidden="true">⚡</span>}
      </div>

      {/* Vessel container */}
      <div 
        className={`
          relative w-12 h-28 bg-surface rounded-lg border-2 overflow-hidden
          transition-all duration-300
          ${isTriggered 
            ? 'border-warning shadow-lg shadow-warning/30' 
            : isHighest 
              ? 'border-success' 
              : 'border-surface'
          }
        `}
      >
        {/* Threshold line at 100% */}
        <div 
          className="absolute top-0 left-0 right-0 border-t border-dashed border-danger/40 z-10"
          aria-hidden="true"
        />
        
        {/* Fill bar */}
        <div 
          className={`
            absolute bottom-0 left-0 right-0 
            rounded-b-md transition-all duration-500 ease-out
            ${state.animation}
          `}
          style={{ 
            height: `${displayHeight}%`,
            background: `linear-gradient(to top, ${colors.to}, ${colors.from})`,
          }}
          aria-hidden="true"
        />
        
        {/* Overflow glow for triggered drives */}
        {isTriggered && (
          <div 
            className="absolute inset-0 bg-warning/20 animate-pulse-fast"
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
          ${isTriggered ? 'text-warning font-semibold' : isHighest ? 'text-success' : 'text-textMuted'}
        `}
      >
        {name}
      </div>

      {/* Extended details (hover/expanded) */}
      {showDetails && (
        <div className="text-[8px] text-textMuted mt-1 text-center">
          {drive.pressure?.toFixed?.(1) || drive.pressure}/{drive.threshold}
        </div>
      )}
    </div>
  );
}

export default PressureBar;
