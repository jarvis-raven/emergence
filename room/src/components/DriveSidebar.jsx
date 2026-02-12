import { useState, useMemo } from 'react';
import { useDrives } from '../hooks/useDrives.js';
import { getDriveColor } from '../context/ThemeContext.jsx';
import ModeToggle from './ModeToggle.jsx';
import DreamView from './DreamView.jsx';
import { useDreams } from '../hooks/useDreams.js';
import DriveCard from './DriveCard.jsx';

/**
 * Horizontal pressure bar for the sidebar layout
 */
function HorizontalBar({ drive, isHighest, onClick, isExpanded }) {
  const { name, percentage, isTriggered } = drive;
  const colors = getDriveColor(name);
  const displayWidth = Math.min(percentage, 100);

  const statusIcon = isTriggered ? '🔥' : percentage >= 90 ? '⚡' : '';

  return (
    <div
      className={`
        group cursor-pointer rounded-lg px-2 py-1.5 transition-all duration-200
        ${isExpanded
          ? 'bg-accent/10 border border-accent/30'
          : isTriggered 
            ? 'bg-warning/10 border border-warning/30' 
            : 'border border-transparent hover:bg-background/50'
        }
      `}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      aria-label={`${name}: ${percentage}% pressure`}
    >
      {/* Drive name + percentage row */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          {statusIcon && <span className="text-[10px]">{statusIcon}</span>}
          <span className={`
            text-[11px] font-medium uppercase tracking-wider
            ${isTriggered ? 'text-warning' : isHighest ? 'text-accent' : 'text-textMuted'}
          `}>
            {name}
          </span>
        </div>
        <span className={`
          text-[11px] font-mono font-bold
          ${isTriggered ? 'text-warning' : percentage >= 70 ? 'text-text' : 'text-textMuted'}
        `}>
          {percentage}%
        </span>
      </div>

      {/* Horizontal bar */}
      <div className="relative h-2 bg-background/60 rounded-full overflow-hidden">
        <div
          className={`
            absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out
            ${isTriggered ? 'animate-pulse' : ''}
          `}
          style={{
            width: `${displayWidth}%`,
            background: `linear-gradient(to right, ${colors.from}, ${colors.to})`,
          }}
        />
      </div>
    </div>
  );
}

/**
 * DriveSidebar — Compact left-column drives display
 * 
 * Horizontal pressure bars with awake/dream toggle.
 * Clicking a bar expands its detail card below.
 */
export default function DriveSidebar({ agentName = 'Agent' }) {
  const [isAwake, setIsAwake] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [expandedDrive, setExpandedDrive] = useState(null);
  const [satisfyingDrive, setSatisfyingDrive] = useState(null);

  const {
    drives,
    triggeredDrives,
    loading: drivesLoading,
    error: drivesError,
    refetch: refetchDrives,
    satisfyDrive,
    lastUpdated,
  } = useDrives();

  const {
    dreams,
    highlights,
    totalDreams,
    loading: dreamsLoading,
  } = useDreams({ enabled: !isAwake });

  const handleToggle = () => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setIsAwake((prev) => !prev);
      setTimeout(() => setIsTransitioning(false), 600);
    }, 50);
  };

  const handleSatisfy = async (driveName) => {
    setSatisfyingDrive(driveName);
    try {
      await satisfyDrive(driveName);
    } finally {
      setSatisfyingDrive(null);
    }
  };

  const highestDrive = useMemo(() => {
    return drives.length > 0 ? drives[0] : null;
  }, [drives]);

  // Loading
  if (drivesLoading && !drives.length) {
    return (
      <div className="p-4 space-y-3">
        {[1,2,3,4,5].map(i => (
          <div key={i} className="animate-pulse">
            <div className="h-3 bg-background/50 rounded w-3/4 mb-1.5"></div>
            <div className="h-2 bg-background/50 rounded-full"></div>
          </div>
        ))}
      </div>
    );
  }

  // Error
  if (drivesError && !drives.length) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-danger mb-2">Cannot load drives</p>
        <button onClick={refetchDrives} className="text-xs text-accent hover:underline">Retry</button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Mode Toggle + Status */}
      <div className="p-3 border-b border-surface">
        <div className="flex justify-center mb-2">
          <ModeToggle isAwake={isAwake} onToggle={handleToggle} disabled={isTransitioning} />
        </div>
        <div className="text-center">
          <h2 className={`text-sm font-bold ${isAwake ? 'text-accent' : 'text-indigo-400'}`}>
            {isAwake ? `${agentName} is Awake` : `${agentName} is Dreaming`}
          </h2>
          <p className="text-[10px] text-textMuted mt-0.5">
            {isAwake 
              ? `${triggeredDrives.length > 0 ? `${triggeredDrives.length} triggered` : `${drives.length} drives active`}`
              : 'Processing memories'
            }
            {lastUpdated && (
              <span className="ml-1 opacity-70">
                • {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className={`
        flex-1 overflow-y-auto min-h-0 p-2
        transition-all duration-600
        ${isTransitioning ? 'opacity-0' : 'opacity-100'}
      `}>
        {isAwake ? (
          <div className="space-y-1">
            {drives.map((drive) => (
              <div key={drive.name}>
                <HorizontalBar
                  drive={drive}
                  isHighest={drive.name === highestDrive?.name}
                  isExpanded={expandedDrive === drive.name}
                  onClick={() => setExpandedDrive(
                    expandedDrive === drive.name ? null : drive.name
                  )}
                />
                {/* Expanded detail card */}
                {expandedDrive === drive.name && (
                  <div className="mt-1 mb-2 px-1">
                    <DriveCard
                      drive={drive}
                      isHighest={drive.name === highestDrive?.name}
                      onSatisfy={handleSatisfy}
                      satisfying={satisfyingDrive === drive.name}
                      defaultExpanded={true}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <DreamView
            dreams={dreams}
            highlights={highlights}
            totalDreams={totalDreams}
            loading={dreamsLoading}
          />
        )}
      </div>
    </div>
  );
}
