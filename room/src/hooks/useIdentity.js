import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Hook to fetch identity files (soul, self, aspirations, interests)
 * Returns content, loading state, and error for a specific file
 * 
 * @param {string} file - Identity file name (e.g., 'SOUL.md', 'SELF.md')
 * @returns {object} { data, content, loading, error, exists, modified, refetch }
 */
export function useIdentity(file) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!file) {
      setLoading(false);
      return;
    }

    const fetchIdentity = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/api/identity/${file}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        console.error(`Failed to load identity file ${file}:`, err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIdentity();
  }, [file]);

  const refetch = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/identity/${file}`);
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
    content: data?.content || '',
    exists: data?.exists || false,
    modified: data?.stats?.modified || null,
  };
}

export default useIdentity;
