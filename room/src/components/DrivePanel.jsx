import { useState, useMemo } from 'react';
import { useDrives } from '../hooks/useDrives.js';
import { useDreams } from '../hooks/useDreams.js';
import { getDriveColor } from '../context/ThemeContext.jsx';
import { 
  enrichDriveWithThresholds, 
  groupDrivesByBand, 
  getBandColors,
  getBandLabel 
} from '../utils/thresholds.js';
import ModeToggle from './ModeToggle.jsx';
import DriveCard from './DriveCard.jsx';
import DreamView from './DreamView.jsx';

/**
 * Skeleton loading state for drive panel
 */
function DrivePanelSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex justify-center py-4">
        <div className="w-14 h-14 bg-surface rounded-full animate-pulse" />
      </div>
      <div className="flex flex-wrap justify-center gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="flex flex-col items-center">
            <div className="w-12 h-28 bg-surface rounded-lg animate-pulse" />
            <div className="w-16 h-3 bg-surface rounded mt-2" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Empty state when no drives are configured
 */
function EmptyDrivesState({ agentName }) {
  return (
    <div className="text-center py-12">
      <div className="text-4xl mb-4 opacity-60" aria-hidden="true">🍃</div>
      <h3 className="text-lg text-text font-medium mb-2">
        No drives configured yet
      </h3>
      <p className="text-sm text-textMuted max-w-xs mx-auto">
        {agentName} is still awakening. Drives will appear once the First Light protocol completes.
      </p>
    </div>
  );
}

/**
 * Error state for drive panel
 */
function ErrorState({ error, onRetry }) {
  return (
    <div className="text-center py-12">
      <div className="text-4xl mb-4 text-danger" aria-hidden="true">⚠️</div>
      <h3 className="text-lg text-text font-medium mb-2">
        Cannot reach the agent&apos;s system
      </h3>
      <p className="text-sm text-textMuted mb-4">{error}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors min-h-[44px]"
      >
        Retry
      </button>
    </div>
  );
}

/**
 * Drive Panel - Centerpiece of The Room
 * Shows drive pressures (awake) or dreams (asleep)
 * 
 * @param {object} props
 * @param {string} props.agentName - Name of the agent
 */
export function DrivePanel({ agentName = 'My Agent' }) {
  const [isAwake, setIsAwake] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [satisfyingDrive, setSatisfyingDrive] = useState(null);
  const [expandedDrive, setExpandedDrive] = useState(null);

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
    refetch: refetchDreams,
  } = useDreams({ enabled: !isAwake });

  // Handle mode toggle with 600ms crossfade
  const handleToggle = () => {
    if (isTransitioning) return;

    setIsTransitioning(true);
    setTimeout(() => {
      setIsAwake((prev) => !prev);
      // Small delay before removing transitioning state
      setTimeout(() => setIsTransitioning(false), 600);
    }, 50);
  };

  // Handle drive satisfaction
  const handleSatisfy = async (driveName) => {
    setSatisfyingDrive(driveName);
    try {
      await satisfyDrive(driveName);
    } finally {
      setSatisfyingDrive(null);
    }
  };

  // Find highest drive
  const highestDrive = useMemo(() => {
    return drives.length > 0 ? drives[0] : null;
  }, [drives]);

  // Group drives by threshold band
  const drivesByBand = useMemo(() => {
    return groupDrivesByBand(drives);
  }, [drives]);
  
  // Get counts for each band
  const bandCounts = useMemo(() => ({
    emergency: drivesByBand.emergency.length,
    crisis: drivesByBand.crisis.length,
    triggered: drivesByBand.triggered.length,
    elevated: drivesByBand.elevated.length,
    available: drivesByBand.available.length,
    neutral: drivesByBand.neutral.length,
  }), [drivesByBand]);
  
  // Count urgent drives (triggered or higher)
  const urgentCount = bandCounts.emergency + bandCounts.crisis + bandCounts.triggered;

  // Loading state
  if (drivesLoading && !drives.length) {
    return (
      <div className="bg-surface rounded-2xl border border-surface p-3 lg:p-6">
        <DrivePanelSkeleton />
      </div>
    );
  }

  // Error state
  if (drivesError && !drives.length) {
    return (
      <div className="bg-surface rounded-2xl border border-danger/30 p-3 lg:p-6">
        <ErrorState error={drivesError} onRetry={refetchDrives} />
      </div>
    );
  }

  // Empty state
  if (!drivesLoading && drives.length === 0) {
    return (
      <div className="bg-surface rounded-2xl border border-surface p-3 lg:p-6">
        <div className="flex justify-center mb-6">
          <ModeToggle isAwake={isAwake} onToggle={handleToggle} />
        </div>
        <EmptyDrivesState agentName={agentName} />
      </div>
    );
  }

  return (
    <div 
      className={`
        relative bg-surface rounded-2xl border-2 p-3 lg:p-6 h-full flex flex-col
        transition-all duration-500
        ${isAwake 
          ? 'border-primary/20 shadow-lg shadow-primary/5' 
          : 'border-indigo-500/20 shadow-lg shadow-indigo-500/5'
        }
      `}
    >
      {/* Mode Toggle - Inline centered */}
      <div className="flex justify-center pt-2 lg:pt-3 mb-2">
        <ModeToggle 
          isAwake={isAwake} 
          onToggle={handleToggle}
          disabled={isTransitioning}
        />
      </div>

      {/* Status Header */}
      <div className="text-center mb-3 lg:mb-6">
        <h2 
          className={`
            text-xl font-bold mb-1 transition-colors duration-300
            ${isAwake 
              ? 'text-primary' 
              : 'text-indigo-400'
            }
          `}
        >
          {isAwake 
            ? `${agentName} is Awake` 
            : `${agentName} is Dreaming`
          }
        </h2>
        <p className="text-xs text-textMuted">
          {isAwake 
            ? (
              <>
                {urgentCount > 0 && (
                  <span className="text-warning font-medium">
                    {urgentCount} urgent
                    {bandCounts.emergency > 0 && ` (${bandCounts.emergency} emergency)`}
                    {' • '}
                  </span>
                )}
                Click to rest
              </>
            )
            : 'Processing memories • Click to wake'
          }
          {lastUpdated && (
            <span className="ml-2 opacity-70">
              • Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </p>
      </div>

      {/* Content area with crossfade */}
      <div 
        className={`
          flex-1 min-h-0 overflow-y-auto
          transition-all duration-600 ease-in-out
          ${isTransitioning ? 'opacity-0 scale-[0.98]' : 'opacity-100 scale-100'}
        `}
      >
        {isAwake ? (
          /* Awake Mode: Drive Pressures - Grouped by Threshold Band */
          <div className="space-y-4">
            {/* Render drives grouped by band (emergency → neutral) */}
            {['emergency', 'crisis', 'triggered', 'elevated', 'available', 'neutral'].map(bandKey => {
              const bandDrives = drivesByBand[bandKey];
              if (bandDrives.length === 0) return null;
              
              const bandColors = getBandColors(bandKey);
              const bandLabel = getBandLabel(bandKey);
              
              return (
                <div key={bandKey} className="space-y-1">
                  {/* Band header - only show for urgent bands or if there are multiple bands */}
                  {(bandKey === 'emergency' || bandKey === 'crisis' || bandKey === 'triggered' || Object.values(bandCounts).filter(c => c > 0).length > 1) && (
                    <div className={`text-[10px] uppercase tracking-wider font-semibold ${bandColors.text} px-2 py-1`}>
                      {bandLabel} ({bandDrives.length})
                    </div>
                  )}
                  
                  {/* Drives in this band */}
                  {bandDrives.map((enrichedDrive) => {
                    const { name, percentage, pressure, threshold, band, bandIcon } = enrichedDrive;
                    const colors = getDriveColor(name);
                    const displayWidth = Math.min(percentage, 100);
                    const isHighest = name === highestDrive?.name;
                    const isExpanded = expandedDrive === name;
                    const driveBandColors = getBandColors(band);

                    return (
                      <div key={name}>
                        <div
                          className={`
                            group cursor-pointer rounded-lg px-2 py-1.5 transition-all duration-200
                            ${isExpanded
                              ? `${driveBandColors.bg} border ${driveBandColors.border}`
                              : `border border-transparent hover:${driveBandColors.bg}`
                            }
                          `}
                          onClick={() => setExpandedDrive(isExpanded ? null : name)}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1.5">
                              {bandIcon && <span className="text-[10px]">{bandIcon}</span>}
                              <span className={`text-[11px] font-medium uppercase tracking-wider ${
                                driveBandColors.text
                              }`}>{name}</span>
                            </div>
                            <span className={`text-[11px] font-mono font-bold ${
                              driveBandColors.text
                            }`}>{percentage}%</span>
                          </div>
                          <div className="relative h-2 bg-background/60 rounded-full overflow-hidden">
                            {/* Threshold markers on bar */}
                            <div className="absolute bottom-0 h-full border-l border-dashed border-emerald-500/20" style={{ left: '30%' }} />
                            <div className="absolute bottom-0 h-full border-l border-dashed border-yellow-500/20" style={{ left: '75%' }} />
                            
                            {/* Fill bar */}
                            <div
                              className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out ${
                                (band === 'crisis' || band === 'emergency') ? 'animate-pulse' : ''
                              }`}
                              style={{
                                width: `${displayWidth}%`,
                                background: `linear-gradient(to right, ${driveBandColors.gradient.from}, ${driveBandColors.gradient.to})`,
                              }}
                            />
                          </div>
                        </div>
                        {isExpanded && (
                          <div className="mt-1 mb-2 px-1">
                            <DriveCard
                              drive={{
                                ...enrichedDrive,
                                // Keep original drive structure for DriveCard compatibility
                                isTriggered: band === 'triggered' || band === 'crisis' || band === 'emergency',
                              }}
                              isHighest={isHighest}
                              onSatisfy={handleSatisfy}
                              satisfying={satisfyingDrive === name}
                              defaultExpanded={true}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        ) : (
          /* Asleep Mode: Dreams */
          <DreamView
            dreams={dreams}
            highlights={highlights}
            totalDreams={totalDreams}
            loading={dreamsLoading}
          />
        )}
      </div>

      {/* Ambient glow effect */}
      <div 
        className={`
          absolute -inset-4 rounded-3xl blur-3xl -z-10 opacity-20
          transition-colors duration-500 pointer-events-none
          ${isAwake ? 'bg-primary' : 'bg-indigo-600'}
        `}
        aria-hidden="true"
      />
    </div>
  );
}

export default DrivePanel;
