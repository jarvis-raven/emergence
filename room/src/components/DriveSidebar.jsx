import { useState, useMemo } from 'react';
import { useDrives } from '../hooks/useDrives.js';
import { getDriveColor } from '../context/ThemeContext.jsx';
import { enrichDriveWithThresholds, getBandColors } from '../utils/thresholds.js';
import ModeToggle from './ModeToggle.jsx';
import DreamView from './DreamView.jsx';
import { useDreams } from '../hooks/useDreams.js';
import DriveCard from './DriveCard.jsx';

/**
 * Horizontal pressure bar for the sidebar layout with threshold visualization
 */
function HorizontalBar({ drive, isHighest, onClick, isExpanded }) {
  const enrichedDrive = useMemo(() => enrichDriveWithThresholds(drive), [drive]);
  const { name, percentage, band, bandIcon, bandColors } = enrichedDrive;
  const displayWidth = Math.min(percentage, 100);

  return (
    <div
      className={`
        group cursor-pointer rounded-lg px-2 py-1.5 transition-all duration-200
        ${isExpanded
          ? `${bandColors.bg} border ${bandColors.border}`
          : `border border-transparent hover:${bandColors.bg}`
        }
      `}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      aria-label={`${name}: ${percentage}% pressure (${band})`}
    >
      {/* Drive name + percentage row */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          {bandIcon && <span className="text-[10px]">{bandIcon}</span>}
          <span className={`
            text-[11px] font-medium uppercase tracking-wider
            ${bandColors.text}
          `}>
            {name}
          </span>
        </div>
        <span className={`
          text-[11px] font-mono font-bold
          ${bandColors.text}
        `}>
          {percentage}%
        </span>
      </div>

      {/* Horizontal bar with threshold markers */}
      <div className="relative h-2 bg-background/60 rounded-full overflow-hidden">
        {/* Threshold markers */}
        <div className="absolute bottom-0 h-full border-l border-dashed border-emerald-500/20" style={{ left: '30%' }} />
        <div className="absolute bottom-0 h-full border-l border-dashed border-yellow-500/20" style={{ left: '75%' }} />
        
        {/* Fill bar with band colors */}
        <div
          className={`
            absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out
            ${(band === 'crisis' || band === 'emergency') ? 'animate-pulse' : ''}
          `}
          style={{
            width: `${displayWidth}%`,
            background: `linear-gradient(to right, ${bandColors.gradient.from}, ${bandColors.gradient.to})`,
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
