import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Hook to fetch and provide agent configuration
 * Returns config, loading state, and error
 */
export function useConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch(`${API_URL}/api/config`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        setConfig(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load config:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  // Retry function for manual refresh
  const refetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/config`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setConfig(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    config,
    loading,
    error,
    refetch,
    // Convenience accessors
    agentName: config?.agent?.name || 'My Agent',
    theme: config?.room?.theme,
    drivesConfig: config?.drives,
    paths: config?.paths,
  };
}

export default useConfig;
