import { useState, useEffect, useCallback, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Generic API fetching hook
 * Used by all panels for consistent data fetching with auto-refresh
 *
 * @param {string} endpoint - API endpoint path (e.g., '/api/drives')
 * @param {object} options - Hook options
 * @param {number} options.refreshInterval - Auto-refresh interval in ms (default: 30000)
 * @param {boolean} options.enabled - Whether to fetch (default: true)
 * @param {function} options.transform - Transform function for response data
 * @returns {object} { data, loading, error, refetch, lastUpdated }
 */
export function useApi(endpoint, options = {}) {
  const { refreshInterval = 30000, enabled = true, transform = (data) => data } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Use ref to track if component is mounted
  const mountedRef = useRef(true);

  // Store transform in ref to avoid re-render loops
  const transformRef = useRef(transform);
  transformRef.current = transform;

  const fetchData = useCallback(
    async (showLoading = true) => {
      if (!endpoint) return;

      if (showLoading) setLoading(true);
      setError(null);

      try {
        const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const rawData = await response.json();

        if (mountedRef.current) {
          setData(transformRef.current(rawData));
          setLastUpdated(new Date());
        }
      } catch (err) {
        if (mountedRef.current) {
          console.error(`API error for ${endpoint}:`, err);
          setError(err.message);
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [endpoint],
  );

  const refetch = useCallback(async () => {
    await fetchData(true);
  }, [fetchData]);

  // Initial fetch and auto-refresh
  useEffect(() => {
    mountedRef.current = true;

    if (enabled) {
      fetchData();

      // Set up auto-refresh interval
      if (refreshInterval > 0) {
        const intervalId = setInterval(() => {
          fetchData(false); // Don't show loading state on refresh
        }, refreshInterval);

        return () => {
          clearInterval(intervalId);
          mountedRef.current = false;
        };
      }
    }

    return () => {
      mountedRef.current = false;
    };
  }, [fetchData, refreshInterval, enabled]);

  return {
    data,
    loading,
    error,
    refetch,
    lastUpdated,
    isStale: lastUpdated ? Date.now() - lastUpdated.getTime() > refreshInterval * 2 : false,
  };
}

/**
 * POST request helper
 *
 * @param {string} endpoint - API endpoint path
 * @param {object} body - Request body
 * @returns {Promise<object>} Response data
 */
export async function postApi(endpoint, body = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export default useApi;
