import { useCallback, useEffect, useRef, useState } from 'react';
import useApi, { postApi } from './useApi.js';

const WS_URL = import.meta.env.VITE_WS_URL || '';

/**
 * Hook to manage WebSocket connection with auto-reconnect
 * @param {string} url - WebSocket URL
 * @param {object} options - Hook options
 * @param {function} options.onMessage - Callback for incoming messages
 * @param {boolean} options.enabled - Whether to connect
 * @returns {object} { connected, connectionStatus }
 */
function useWebSocket(url, options = {}) {
  const { onMessage, enabled = true } = options;
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);

  // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
  const getReconnectDelay = () => {
    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
    return delay;
  };

  const connect = useCallback(() => {
    if (!enabled || !url) return;
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    setConnectionStatus('connecting');
    
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close();
          return;
        }
        console.log('[WebSocket] Connected');
        setConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;

        // Attempt reconnect with backoff
        if (enabled) {
          reconnectAttemptsRef.current++;
          const delay = getReconnectDelay();
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          setConnectionStatus('reconnecting');
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connect();
            }
          }, delay);
        }
      };

      ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err);
        setConnectionStatus('error');
      };
    } catch (err) {
      console.error('[WebSocket] Failed to create connection:', err);
      setConnectionStatus('error');
    }
  }, [url, enabled, onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    reconnectAttemptsRef.current = 0;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return { connected, connectionStatus };
}

/**
 * Transform raw drives data into the format expected by the UI
 * @param {object} rawData - Raw drives data from API or WebSocket
 * @returns {object} Transformed data
 */
function transformDrivesData(rawData) {
  // Transform drives object to array with computed properties
  const drivesArray = Object.entries(rawData.drives || {}).map(([name, drive]) => ({
    name,
    ...drive,
    percentage: Math.round((drive.pressure / drive.threshold) * 100),
    isTriggered: (drive.pressure / drive.threshold) >= 1,
    isHigh: (drive.pressure / drive.threshold) >= 0.7,
  }));

  // Sort by percentage descending
  drivesArray.sort((a, b) => b.percentage - a.percentage);

  // Get triggered drives from the API response
  const triggered = rawData.triggered_drives || [];

  return {
    drives: drivesArray,
    triggeredDrives: triggered,
    raw: rawData,
  };
}

/**
 * Hook to fetch and manage drive data
 * Uses WebSocket for live updates with polling as fallback
 * 
 * @param {object} options - Hook options
 * @param {boolean} options.enabled - Whether to fetch
 * @returns {object} { drives, triggeredDrives, loading, error, refetch, satisfyDrive, lastUpdated, wsConnected, wsStatus }
 */
export function useDrives(options = {}) {
  const { enabled = true } = options;
  const [wsData, setWsData] = useState(null);

  // Use API polling as fallback (60s interval since WebSocket is primary)
  const { 
    data: apiData, 
    loading, 
    error, 
    refetch, 
    lastUpdated, 
    isStale 
  } = useApi('/api/drives', {
    refreshInterval: 60000, // 60 seconds (fallback only)
    enabled,
    transform: transformDrivesData,
  });

  // Determine WebSocket URL
  const wsUrl = useCallback(() => {
    if (WS_URL) return WS_URL;
    
    // Derive from current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}`;
  }, []);

  // Handle WebSocket messages
  const handleWsMessage = useCallback((message) => {
    if (message.type === 'drives_update' && message.data) {
      console.log('[useDrives] Received WebSocket update');
      setWsData(transformDrivesData(message.data));
    }
  }, []);

  // WebSocket connection
  const { connected: wsConnected, connectionStatus: wsStatus } = useWebSocket(
    wsUrl(),
    {
      onMessage: handleWsMessage,
      enabled,
    }
  );

  // Use WebSocket data if available, otherwise fall back to API data
  const data = wsData || apiData;

  // Satisfy a drive by name
  const satisfyDrive = useCallback(async (driveName) => {
    await postApi(`/api/drives/${encodeURIComponent(driveName)}/satisfy`);
    // Refetch to get updated state (will also trigger WebSocket update)
    await refetch();
  }, [refetch]);

  // Clear WebSocket data when disabled
  useEffect(() => {
    if (!enabled) {
      setWsData(null);
    }
  }, [enabled]);

  return {
    drives: data?.drives || [],
    triggeredDrives: data?.triggeredDrives || [],
    rawData: data?.raw,
    loading,
    error,
    refetch,
    satisfyDrive,
    lastUpdated,
    isStale,
    wsConnected,
    wsStatus,
  };
}

export default useDrives;
