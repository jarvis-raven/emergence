import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * DaemonHealthDrawer - Shows daemon status, tick countdown, and spawn errors
 * 
 * Desktop: Slides from right
 * Mobile: Full-screen overlay
 */
export default function DaemonHealthDrawer({ isOpen, onClose }) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tickInterval, setTickInterval] = useState(900); // Default 15min

  // Fetch health data
  useEffect(() => {
    if (!isOpen) return;

    const fetchHealth = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch drives-state.json
        const response = await fetch(`${API_URL}/api/drives/state`);
        if (!response.ok) throw new Error('Failed to fetch daemon state');
        
        const data = await response.json();
        
        // Fetch config to get tick_interval
        try {
          const configResponse = await fetch(`${API_URL}/api/config`);
          if (configResponse.ok) {
            const config = await configResponse.json();
            setTickInterval(config?.drives?.tick_interval || 900);
          }
        } catch {
          // Config fetch optional, use default
        }

        setHealth(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    
    // Poll every 5 seconds while open
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  // Calculate daemon status
  const getDaemonStatus = () => {
    if (!health || !health.last_updated) return { status: 'unknown', color: 'text-textMuted' };
    
    const lastUpdate = new Date(health.last_updated);
    const now = new Date();
    const secondsSinceUpdate = (now - lastUpdate) / 1000;
    const offlineThreshold = tickInterval * 3; // 3x tick interval
    
    if (secondsSinceUpdate > offlineThreshold) {
      return { status: 'offline', color: 'text-red-400' };
    } else if (secondsSinceUpdate > tickInterval * 1.5) {
      return { status: 'stale', color: 'text-yellow-400' };
    } else {
      return { status: 'online', color: 'text-emerald-400' };
    }
  };

  // Calculate time until next tick
  const getNextTickInfo = () => {
    if (!health || !health.last_updated) return null;
    
    const lastUpdate = new Date(health.last_updated);
    const now = new Date();
    const secondsSinceUpdate = (now - lastUpdate) / 1000;
    const secondsUntilNext = Math.max(0, tickInterval - secondsSinceUpdate);
    
    const minutes = Math.floor(secondsUntilNext / 60);
    const seconds = Math.floor(secondsUntilNext % 60);
    
    const progress = ((tickInterval - secondsUntilNext) / tickInterval) * 100;
    
    return {
      minutesUntilNext: minutes,
      secondsUntilNext: seconds,
      progress: Math.max(0, Math.min(100, progress)),
      overdue: secondsSinceUpdate > tickInterval
    };
  };

  const daemonStatus = getDaemonStatus();
  const tickInfo = getNextTickInfo();

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-[60] lg:hidden"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div 
        className={`
          fixed top-0 right-0 h-full w-full lg:w-96 bg-background border-l border-surface
          shadow-2xl z-[70] overflow-y-auto
          transform transition-transform duration-300
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background border-b border-surface px-4 py-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Daemon Health</h2>
          <button
            onClick={onClose}
            className="p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {loading && (
            <div className="text-center text-textMuted py-8">
              Loading daemon status...
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400 text-sm">
              <strong>Error:</strong> {error}
            </div>
          )}

          {health && !loading && (
            <>
              {/* Status Badge */}
              <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textMuted">Status</span>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      daemonStatus.status === 'online' ? 'bg-emerald-400' :
                      daemonStatus.status === 'stale' ? 'bg-yellow-400' : 'bg-red-400'
                    }`} />
                    <span className={`text-sm font-medium ${daemonStatus.color}`}>
                      {daemonStatus.status === 'online' ? 'Online' :
                       daemonStatus.status === 'stale' ? 'Stale' : 'Offline'}
                    </span>
                  </div>
                </div>
                
                {health.last_updated && (
                  <div className="text-xs text-textMuted">
                    Last tick: {new Date(health.last_updated).toLocaleString()}
                  </div>
                )}
              </div>

              {/* Tick Countdown */}
              {tickInfo && daemonStatus.status !== 'offline' && (
                <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-textMuted">Next Tick</span>
                    <span className="text-sm font-medium text-text">
                      {tickInfo.overdue ? 'Overdue' : `${tickInfo.minutesUntilNext}m ${tickInfo.secondsUntilNext}s`}
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-surface rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ${
                        tickInfo.overdue ? 'bg-yellow-400' : 'bg-accent'
                      }`}
                      style={{ width: `${tickInfo.progress}%` }}
                    />
                  </div>
                  
                  <div className="mt-2 text-xs text-textMuted">
                    Tick interval: {Math.floor(tickInterval / 60)} minutes
                  </div>
                </div>
              )}

              {/* Triggered Drives */}
              {health.triggered && health.triggered.length > 0 && (
                <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                  <div className="text-sm text-textMuted mb-2">Triggered Drives</div>
                  <div className="flex flex-wrap gap-2">
                    {health.triggered.map((drive) => (
                      <span 
                        key={drive}
                        className="px-2 py-1 bg-accent/20 text-accent text-xs rounded-md font-medium"
                      >
                        {drive}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Spawn Errors (placeholder - would need API support) */}
              {/* Future: Show recent spawn failures from trigger_log */}
              
              {/* Daemon Logs Link */}
              <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                <div className="text-sm text-textMuted mb-2">Logs</div>
                <div className="text-xs text-textMuted space-y-1">
                  <div><span className="font-mono">.emergence/logs/daemon.log</span></div>
                  <div className="text-xs opacity-75">Check terminal for spawn errors</div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="pt-2 space-y-2">
                <div className="text-xs text-textMuted">
                  <strong>Quick Commands:</strong>
                </div>
                <div className="font-mono text-xs bg-surface rounded p-2 space-y-1">
                  <div>$ emergence drives daemon status</div>
                  <div>$ emergence drives daemon stop</div>
                  <div>$ emergence drives daemon start</div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
