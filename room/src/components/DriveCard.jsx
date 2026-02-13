import { useState, useMemo } from 'react';
import { getDriveColor } from '../context/ThemeContext.jsx';
import { enrichDriveWithThresholds, getBandColors } from '../utils/thresholds.js';
import PressureBar from './PressureBar.jsx';

/**
 * Format date for display
 * 
 * @param {string|number} dateValue - Date value to format
 * @returns {string} Formatted date string
 */
function formatDate(dateValue) {
  if (!dateValue) return 'Never';
  
  try {
    const date = new Date(dateValue);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });
  } catch {
    return String(dateValue);
  }
}

/**
 * Expandable drive detail card
 * 
 * @param {object} props
 * @param {object} props.drive - Drive data object
 * @param {boolean} props.isHighest - Whether this is the highest pressure drive
 * @param {function} props.onSatisfy - Callback when drive is satisfied
 * @param {boolean} props.satisfying - Whether satisfaction is in progress
 */
export function DriveCard({ 
  drive, 
  isHighest = false, 
  onSatisfy,
  satisfying = false,
  defaultExpanded = false,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showConfirm, setShowConfirm] = useState(false);
  const [flashSuccess, setFlashSuccess] = useState(false);

  // Enrich drive with threshold data
  const enrichedDrive = useMemo(() => enrichDriveWithThresholds(drive), [drive]);
  const { band, bandLabel, bandIcon, thresholds, bandColors: driveBandColors } = enrichedDrive;

  const { name, description, prompt, rate, last_satisfied, valence, thwarting_count } = drive;
  const colors = getDriveColor(name);
  const isAversive = valence === 'aversive';

  const handleSatisfyClick = () => {
    if (drive.percentage === 0) return; // Already satisfied
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    setShowConfirm(false);
    try {
      await onSatisfy(name);
      // Flash success animation
      setFlashSuccess(true);
      setTimeout(() => setFlashSuccess(false), 1000);
    } catch (err) {
      console.error('Failed to satisfy drive:', err);
    }
  };

  const handleCancel = () => {
    setShowConfirm(false);
  };

  return (
    <div 
      className={`
        bg-surface rounded-xl border-2 transition-all duration-300
        ${expanded ? 'border-primary/50' : 'border-transparent'}
        ${flashSuccess ? 'border-success shadow-lg shadow-success/20' : ''}
        hover:border-primary/30
      `}
    >
      {/* Header row */}
      <div 
        className={`p-4 flex items-center gap-4 ${defaultExpanded ? '' : 'cursor-pointer'}`}
        onClick={defaultExpanded ? undefined : () => setExpanded(!expanded)}
      >
        {/* Pressure Bar — only in collapsible mode when collapsed */}
        {!defaultExpanded && !expanded && (
          <div className="shrink-0">
            <PressureBar 
              drive={drive} 
              isHighest={isHighest}
              showDetails={false}
            />
          </div>
        )}

        {/* Drive info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-text">{name}</h3>
            {isAversive && (
              <span 
                className="text-red-500 font-bold" 
                title={`Aversive state (thwarted ${thwarting_count || 0}x)`}
                aria-label="Aversive state"
              >
                ⚠{thwarting_count > 0 ? thwarting_count : ''}
              </span>
            )}
            {drive.isTriggered && !isAversive && (
              <span className="text-warning" title="Triggered" aria-label="Triggered">🔥</span>
            )}
            {isHighest && !drive.isTriggered && !isAversive && (
              <span className="text-success" title="Highest" aria-label="Highest pressure">⚡</span>
            )}
          </div>
          
          {description && (
            <p className="text-sm text-textMuted">
              {description}
            </p>
          )}
        </div>

        {/* Satisfy button (collapsed only, not in sidebar mode) */}
        {!defaultExpanded && !expanded && !showConfirm && drive.percentage > 0 && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleSatisfyClick();
            }}
            disabled={satisfying}
            className={`
              px-3 py-2 rounded-lg text-xs font-medium
              transition-all duration-200
              min-h-[44px] min-w-[44px]
              ${satisfying 
                ? 'bg-textMuted/20 text-textMuted cursor-wait' 
                : 'bg-primary/20 text-primary hover:bg-primary hover:text-white'
              }
            `}
          >
            {satisfying ? '...' : 'Satisfy'}
          </button>
        )}

        {/* Expand indicator — only in collapsible mode */}
        {!defaultExpanded && (
          <div 
            className={`
              text-textMuted transition-transform duration-200
              ${expanded ? 'rotate-180' : ''}
            `}
            aria-hidden="true"
          >
            ▼
          </div>
        )}
      </div>

      {/* Confirmation dialog */}
      {showConfirm && (
        <div className="px-4 pb-4">
          <div className="bg-surface/50 rounded-lg p-4 border border-warning/30">
            <p className="text-sm text-text mb-3">
              Satisfy <strong>{name}</strong>? This will reset the pressure to 0.
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleConfirm}
                className="px-4 py-2 bg-success text-white rounded-lg text-sm font-medium hover:bg-success/80 transition-colors min-h-[44px]"
              >
                Confirm
              </button>
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-surface text-textMuted rounded-lg text-sm font-medium hover:bg-surface/80 transition-colors min-h-[44px]"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Expanded view */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-surface pt-4">
          <div className="space-y-3">
            {/* Aversive state warning */}
            {isAversive && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className="text-red-500 text-lg">⚠️</span>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-red-400 mb-1">
                      Aversive State - Drive in Distress
                    </h4>
                    <p className="text-xs text-red-300/80 mb-2">
                      This drive has been thwarted {thwarting_count || 0} time{thwarting_count !== 1 ? 's' : ''}.
                      Consider investigating blockages instead of forcing satisfaction.
                    </p>
                    <div className="text-xs text-red-300/60">
                      💡 Tip: Aversive drives often need reflection, not action
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Threshold status badge */}
            <div className={`
              inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
              ${driveBandColors.bg} ${driveBandColors.border} border
            `}>
              <span>{bandIcon}</span>
              <span className={driveBandColors.text}>{bandLabel}</span>
              <span className="text-textMuted">
                ({drive.pressure?.toFixed?.(1) || drive.pressure}/{drive.threshold})
              </span>
            </div>
            
            {/* Threshold bands info */}
            {thresholds && (
              <div className="bg-background/50 rounded-lg p-3">
                <h4 className="text-xs uppercase tracking-wider text-textMuted mb-2">Threshold Bands</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1">
                    <span className="text-emerald-500">✓</span>
                    <span className="text-textMuted">Available:</span>
                    <span className="text-text font-mono">{thresholds.available?.toFixed?.(1)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-500">⚡</span>
                    <span className="text-textMuted">Elevated:</span>
                    <span className="text-text font-mono">{thresholds.elevated?.toFixed?.(1)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-orange-500">🔥</span>
                    <span className="text-textMuted">Triggered:</span>
                    <span className="text-text font-mono">{thresholds.triggered?.toFixed?.(1)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-red-500">⚠️</span>
                    <span className="text-textMuted">Crisis:</span>
                    <span className="text-text font-mono">{thresholds.crisis?.toFixed?.(1)}</span>
                  </div>
                </div>
              </div>
            )}
            
            {/* Prompt */}
            {prompt && (
              <div>
                <h4 className="text-xs uppercase tracking-wider text-textMuted mb-1">Prompt</h4>
                <p className="text-sm text-textMuted italic">"{prompt}"</p>
              </div>
            )}

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-4 pt-2">
              {valence && (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-textMuted mb-1">Valence</h4>
                  <p className={`text-sm font-medium ${
                    valence === 'aversive' ? 'text-red-400' : 
                    valence === 'appetitive' ? 'text-green-400' : 
                    'text-gray-400'
                  }`}>
                    {valence === 'aversive' && '⚠️ '}{valence}
                  </p>
                </div>
              )}
              
              {rate !== undefined && (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-textMuted mb-1">Rate</h4>
                  <p className="text-sm text-text">{rate}/hr</p>
                </div>
              )}
              
              <div>
                <h4 className="text-xs uppercase tracking-wider text-textMuted mb-1">Last Satisfied</h4>
                <p className="text-sm text-text">{formatDate(last_satisfied)}</p>
              </div>
            </div>

            {/* Satisfy button in expanded view */}
            {!showConfirm && drive.percentage > 0 && (
              <div className="pt-2">
                {isAversive ? (
                  <div className="space-y-2">
                    <button
                      onClick={handleSatisfyClick}
                      disabled={satisfying}
                      className={`
                        w-full px-4 py-3 rounded-lg text-sm font-medium
                        transition-all duration-200
                        min-h-[44px]
                        ${satisfying 
                          ? 'bg-textMuted/20 text-textMuted cursor-wait' 
                          : 'bg-orange-600 text-white hover:bg-orange-700'
                        }
                      `}
                    >
                      {satisfying ? 'Investigating...' : `Investigate ${name}`}
                    </button>
                    <p className="text-xs text-center text-textMuted">
                      Aversive drives benefit from investigation over forced satisfaction
                    </p>
                  </div>
                ) : (
                  <button
                    onClick={handleSatisfyClick}
                    disabled={satisfying}
                    className={`
                      w-full px-4 py-3 rounded-lg text-sm font-medium
                      transition-all duration-200
                      min-h-[44px]
                      ${satisfying 
                        ? 'bg-textMuted/20 text-textMuted cursor-wait' 
                        : 'bg-gradient-to-r text-white hover:opacity-90'
                      }
                    `}
                    style={{
                      background: !satisfying 
                        ? `linear-gradient(to right, ${colors.from}, ${colors.to})` 
                        : undefined
                    }}
                  >
                    {satisfying ? 'Satisfying...' : `Satisfy ${name}`}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default DriveCard;
