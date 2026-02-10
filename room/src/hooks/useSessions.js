import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Hook to fetch sessions
 * Returns sessions list, loading state, and error
 * @param {Object} options - Query options
 * @param {number} options.limit - Max number of sessions (default 20)
 * @param {string} options.drive - Optional drive filter
 */
export function useSessions(options = {}) {
  const { limit = 50, drive = null } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        params.append('limit', limit.toString());
        if (drive) {
          params.append('drive', drive);
        }

        const response = await fetch(`${API_URL}/api/sessions?${params}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        console.error('Failed to load sessions:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, [limit, drive]);

  const refetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      if (drive) {
        params.append('drive', drive);
      }

      const response = await fetch(`${API_URL}/api/sessions?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    data,
    loading,
    error,
    refetch,
    sessions: data?.sessions || [],
    count: data?.count || 0,
  };
}

export default useSessions;
