import { useState, useEffect, useCallback, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

// Constants (extracted from magic numbers)
const POLL_INTERVAL_MS = 5000;  // Poll data every 5 seconds
const UI_UPDATE_INTERVAL_MS = 1000;  // Update countdown every second
const STALE_THRESHOLD_MULTIPLIER = 1.5;  // 1.5x tick_interval = stale
const OFFLINE_THRESHOLD_MULTIPLIER = 3;  // 3x tick_interval = offline
const DEFAULT_TICK_INTERVAL = 900;  // 15 minutes

/**
 * DaemonHealthDrawer - Shows daemon status, tick countdown, and spawn errors
 * 
 * Desktop: Slides from right, backdrop clickable to close
 * Mobile: Full-screen overlay, backdrop clickable to close
 * 
 * Accessibility: ARIA labels, keyboard navigation, focus management
 */
export default function DaemonHealthDrawer({ isOpen, onClose }) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tickInterval, setTickInterval] = useState(DEFAULT_TICK_INTERVAL);
  const [now, setNow] = useState(Date.now());  // For real-time countdown
  const abortControllerRef = useRef(null);
  const drawerRef = useRef(null);

  // Fetch health data
  const fetchHealth = useCallback(async () => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      setLoading(health === null);  // Only show loading on first fetch
      setError(null);

      // Fetch drives-state.json
      const response = await fetch(`${API_URL}/api/drives/state`, {
        signal: controller.signal
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch daemon state (${response.status})`);
      }
      
      const data = await response.json();
      setHealth(data);

    } catch (err) {
      if (err.name === 'AbortError') {
        // Request was cancelled, ignore
        return;
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [health]);

  // Fetch config once to get tick_interval
  useEffect(() => {
    if (!isOpen) return;

    const fetchConfig = async () => {
      try {
        const response = await fetch(`${API_URL}/api/config`);
        if (response.ok) {
          const config = await response.json();
          setTickInterval(config?.drives?.tick_interval || DEFAULT_TICK_INTERVAL);
        }
      } catch {
        // Config fetch optional, use default
      }
    };

    fetchConfig();
  }, [isOpen]); // Only fetch config once when drawer opens

  // Poll health data
  useEffect(() => {
    if (!isOpen) return;

    fetchHealth();
    const interval = setInterval(fetchHealth, POLL_INTERVAL_MS);
    
    return () => {
      clearInterval(interval);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [isOpen, fetchHealth]);

  // Real-time countdown timer (updates UI every second)
  useEffect(() => {
    if (!isOpen) return;

    const timer = setInterval(() => {
      setNow(Date.now());
    }, UI_UPDATE_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [isOpen]);

  // Focus management
  useEffect(() => {
    if (isOpen && drawerRef.current) {
      drawerRef.current.focus();
    }
  }, [isOpen]);

  // Keyboard handling
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Calculate daemon status (memoized)
  const getDaemonStatus = useCallback(() => {
    if (!health || !health.last_updated) {
      return { status: 'unknown', color: 'text-textMuted' };
    }
    
    const lastUpdate = new Date(health.last_updated);
    
    // Validate date
    if (isNaN(lastUpdate.getTime())) {
      return { status: 'unknown', color: 'text-textMuted' };
    }
    
    const secondsSinceUpdate = (now - lastUpdate.getTime()) / 1000;
    const offlineThreshold = tickInterval * OFFLINE_THRESHOLD_MULTIPLIER;
    const staleThreshold = tickInterval * STALE_THRESHOLD_MULTIPLIER;
    
    if (secondsSinceUpdate > offlineThreshold) {
      return { status: 'offline', color: 'text-red-400' };
    } else if (secondsSinceUpdate > staleThreshold) {
      return { status: 'stale', color: 'text-yellow-400' };
    } else {
      return { status: 'online', color: 'text-emerald-400' };
    }
  }, [health, now, tickInterval]);

  // Calculate time until next tick (memoized)
  const getNextTickInfo = useCallback(() => {
    if (!health || !health.last_updated) return null;
    
    const lastUpdate = new Date(health.last_updated);
    
    // Validate date
    if (isNaN(lastUpdate.getTime())) return null;
    
    const secondsSinceUpdate = (now - lastUpdate.getTime()) / 1000;
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
  }, [health, now, tickInterval]);

  if (!isOpen) return null;

  const daemonStatus = getDaemonStatus();
  const tickInfo = getNextTickInfo();

  return (
    <>
      {/* Backdrop - clickable on both desktop and mobile */}
      <div 
        className="fixed inset-0 bg-black/50 z-[60]"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Drawer */}
      <div 
        ref={drawerRef}
        role="dialog"
        aria-labelledby="daemon-health-title"
        aria-modal="true"
        tabIndex={-1}
        className={`
          fixed top-0 right-0 h-full w-full lg:w-96 bg-background border-l border-surface
          shadow-2xl z-[70] overflow-y-auto
          transform transition-transform duration-300
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          focus:outline-none
        `}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background border-b border-surface px-4 py-3 flex items-center justify-between">
          <h2 id="daemon-health-title" className="text-lg font-semibold text-text">
            Daemon Health
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
            aria-label="Close daemon health drawer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Loading Skeleton */}
          {loading && !health && (
            <div className="space-y-4 animate-pulse">
              <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                <div className="h-4 bg-surface rounded w-1/3 mb-2"></div>
                <div className="h-6 bg-surface rounded w-2/3"></div>
              </div>
              <div className="bg-surface/50 rounded-lg p-4 border border-surface">
                <div className="h-4 bg-surface rounded w-1/2 mb-2"></div>
                <div className="h-2 bg-surface rounded w-full"></div>
              </div>
            </div>
          )}

          {/* Error State with Retry */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400 text-sm">
              <div className="flex items-start justify-between mb-2">
                <strong>Error:</strong>
                <button
                  onClick={fetchHealth}
                  className="text-xs px-2 py-1 bg-red-500/20 hover:bg-red-500/30 rounded transition-colors"
                  aria-label="Retry fetching daemon health"
                >
                  Retry
                </button>
              </div>
              <p>{error}</p>
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
                    }`} aria-hidden="true" />
                    <span className={`text-sm font-medium ${daemonStatus.color}`}>
                      {daemonStatus.status === 'online' ? 'Online' :
                       daemonStatus.status === 'stale' ? 'Stale' : 
                       daemonStatus.status === 'unknown' ? 'Unknown' : 'Offline'}
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
                    <span className="text-sm font-medium text-text" aria-live="polite">
                      {tickInfo.overdue ? 'Overdue' : `${tickInfo.minutesUntilNext}m ${tickInfo.secondsUntilNext}s`}
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-surface rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${
                        tickInfo.overdue ? 'bg-yellow-400' : 'bg-accent'
                      }`}
                      style={{ width: `${tickInfo.progress}%` }}
                      role="progressbar"
                      aria-valuenow={Math.round(tickInfo.progress)}
                      aria-valuemin="0"
                      aria-valuemax="100"
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
