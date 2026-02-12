import { useState, useEffect } from 'react';

/**
 * DaemonHealthDrawer — Shows drives daemon health status
 * 
 * Features:
 * - Status badge (online/stale/offline)
 * - WebSocket connection indicator
 * - Tick countdown with progress bar
 * - List of currently triggered drives
 * - Force Refresh button
 * 
 * Slides in from right on desktop, appears in mobile menu
 */
function DaemonHealthDrawer({ isOpen, onClose }) {
  const [daemonState, setDaemonState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [restarting, setRestarting] = useState(false);
  const [liveCountdown, setLiveCountdown] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  const fetchDaemonState = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/drives/state');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch daemon state (${response.status})`);
      }
      
      const data = await response.json();
      setDaemonState(data);
    } catch (err) {
      console.error('Daemon state fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const forceRefresh = async () => {
    setRestarting(true);
    await fetchDaemonState();
    setRestarting(false);
  };

  // WebSocket connection monitoring
  useEffect(() => {
    if (!isOpen) return;

    // Use wss:// for HTTPS pages, ws:// for HTTP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}`);
    
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    return () => ws.close();
  }, [isOpen]);

  // Live countdown timer (updates every second)
  useEffect(() => {
    if (!isOpen || !daemonState?.last_tick) return;

    const interval = setInterval(() => {
      const lastUpdate = new Date(daemonState.last_tick);
      const tickInterval = daemonState.tick_interval_seconds || 300;
      const nextTick = new Date(lastUpdate.getTime() + tickInterval * 1000);
      const now = new Date();
      const remaining = Math.max(0, nextTick - now);
      const remainingSeconds = Math.floor(remaining / 1000);

      setLiveCountdown(remainingSeconds);
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, daemonState]);

  useEffect(() => {
    if (isOpen) {
      fetchDaemonState();
      // Refresh every 10 seconds while drawer is open
      const interval = setInterval(fetchDaemonState, 10000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Calculate daemon status
  const getDaemonStatus = () => {
    if (!daemonState || !daemonState.last_tick) {
      return { status: 'offline', label: 'Offline', color: 'text-red-400' };
    }

    const lastUpdate = new Date(daemonState.last_tick);
    const now = new Date();
    const ageMs = now - lastUpdate;
    const tickInterval = daemonState.tick_interval_seconds || 300; // default 5 min
    const staleThreshold = tickInterval * 3 * 1000; // 3x tick interval

    if (ageMs > staleThreshold) {
      return { status: 'offline', label: 'Offline', color: 'text-red-400' };
    } else if (ageMs > tickInterval * 1000) {
      return { status: 'stale', label: 'Stale', color: 'text-yellow-400' };
    } else {
      return { status: 'online', label: 'Online', color: 'text-green-400' };
    }
  };

  // Calculate progress bar (no need for full tick info anymore)
  const getProgress = () => {
    if (!daemonState || !daemonState.last_tick || liveCountdown === null) return 0;

    const tickInterval = daemonState.tick_interval_seconds || 300;
    const elapsed = tickInterval - liveCountdown;
    const progress = (elapsed / tickInterval) * 100;

    return Math.min(100, Math.max(0, progress));
  };

  // Get triggered drives
  const getTriggeredDrives = () => {
    if (!daemonState || !daemonState.drives) return [];
    
    return Object.entries(daemonState.drives)
      .filter(([_, drive]) => drive.status === 'triggered')
      .map(([name, drive]) => ({
        name,
        pressure: drive.pressure,
        threshold: drive.threshold,
        percentage: Math.round((drive.pressure / drive.threshold) * 100),
      }));
  };

  const status = getDaemonStatus();
  const progress = getProgress();
  const triggeredDrives = getTriggeredDrives();

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-96 bg-background border-l border-surface z-50 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-background border-b border-surface px-4 py-3 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold text-text">Daemon Health</h2>
          <button
            onClick={onClose}
            className="p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
            title="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {loading && !daemonState && (
            <div className="text-center py-8 text-textMuted">Loading daemon state...</div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="text-red-400 text-xl">⚠️</span>
                <div className="flex-1">
                  <div className="font-semibold text-red-400 mb-1">Error:</div>
                  <div className="text-sm text-red-300">{error}</div>
                  <button
                    onClick={fetchDaemonState}
                    className="mt-3 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg transition-colors text-sm"
                  >
                    Retry
                  </button>
                </div>
              </div>
            </div>
          )}

          {daemonState && !error && (
            <>
              {/* Status Badge */}
              <div className="bg-surface rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-textMuted">Daemon Status</span>
                  <span className={`font-semibold ${status.color}`}>
                    {status.label}
                  </span>
                </div>
                {daemonState.last_tick && (
                  <div className="text-xs text-textMuted mb-3">
                    Last update: {new Date(daemonState.last_tick).toLocaleTimeString()}
                  </div>
                )}
                
                {/* WebSocket Status */}
                <div className="flex items-center justify-between pt-2 border-t border-surface/50">
                  <span className="text-sm text-textMuted">WebSocket</span>
                  <span className={`text-sm font-semibold ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>

              {/* Next Tick Countdown */}
              {liveCountdown !== null && status.status === 'online' && (
                <div className="bg-surface rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-textMuted">Next tick in</span>
                    <span className="font-mono text-sm text-text">
                      {Math.floor(liveCountdown / 60)}:{String(liveCountdown % 60).padStart(2, '0')}
                    </span>
                  </div>
                  <div className="w-full bg-background rounded-full h-2 overflow-hidden">
                    <div 
                      className="h-full bg-primary transition-all duration-1000"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Force Refresh Button */}
              <div className="bg-surface rounded-lg p-4">
                <button
                  onClick={forceRefresh}
                  disabled={restarting}
                  className="w-full px-4 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg transition-colors text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {restarting ? 'Refreshing...' : 'Force Refresh'}
                </button>
                <div className="text-xs text-textMuted mt-2 text-center">
                  Immediately fetch latest daemon state
                </div>
              </div>

              {/* Triggered Drives */}
              {triggeredDrives.length > 0 && (
                <div className="bg-surface rounded-lg p-4">
                  <div className="text-sm font-semibold text-text mb-3">
                    Triggered Drives ({triggeredDrives.length})
                  </div>
                  <div className="space-y-2">
                    {triggeredDrives.map((drive) => (
                      <div key={drive.name} className="flex items-center justify-between py-2 border-b border-surface/50 last:border-0">
                        <span className="text-sm text-text font-medium">{drive.name}</span>
                        <span className="text-xs text-primary font-semibold">{drive.percentage}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Spawn Errors (placeholder for future) */}
              {daemonState.spawn_errors && daemonState.spawn_errors.length > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                  <div className="text-sm font-semibold text-yellow-400 mb-2">
                    Recent Spawn Errors
                  </div>
                  <div className="space-y-2 text-xs text-yellow-300">
                    {daemonState.spawn_errors.map((err, idx) => (
                      <div key={idx} className="font-mono">{err}</div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default DaemonHealthDrawer;
