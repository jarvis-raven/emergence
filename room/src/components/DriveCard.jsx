import { useState } from 'react';
import { getDriveColor } from '../context/ThemeContext.jsx';
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
}) {
  const [expanded, setExpanded] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [flashSuccess, setFlashSuccess] = useState(false);

  const { name, description, prompt, rate, last_satisfied } = drive;
  const colors = getDriveColor(name);

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
      {/* Collapsed view */}
      <div 
        className="p-4 flex items-center gap-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Pressure Bar */}
        <div className="shrink-0">
          <PressureBar 
            drive={drive} 
            isHighest={isHighest}
            showDetails={false}
          />
        </div>

        {/* Drive info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-text">{name}</h3>
            {drive.isTriggered && (
              <span className="text-warning" title="Triggered" aria-label="Triggered">🔥</span>
            )}
            {isHighest && !drive.isTriggered && (
              <span className="text-success" title="Highest" aria-label="Highest pressure">⚡</span>
            )}
          </div>
          
          {description && (
            <p className="text-sm text-textMuted">
              {description}
            </p>
          )}
        </div>

        {/* Satisfy button (collapsed) */}
        {!showConfirm && drive.percentage > 0 && (
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

        {/* Expand indicator */}
        <div 
          className={`
            text-textMuted transition-transform duration-200
            ${expanded ? 'rotate-180' : ''}
          `}
          aria-hidden="true"
        >
          ▼
        </div>
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
            {/* Description */}
            {description && (
              <div>
                <h4 className="text-xs uppercase tracking-wider text-textMuted mb-1">Description</h4>
                <p className="text-sm text-text">{description}</p>
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
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default DriveCard;
