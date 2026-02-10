import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Hook to fetch shelf list from /api/shelves
 */
export function useShelves() {
  const [shelves, setShelves] = useState([]);
  const [activeShelfId, setActiveShelfId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchShelves = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/shelves`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const result = await response.json();
      setShelves(result.shelves || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load shelves:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShelves();
    const interval = setInterval(fetchShelves, 60000);
    return () => clearInterval(interval);
  }, [fetchShelves]);

  useEffect(() => {
    if (shelves.length > 0 && !activeShelfId) {
      setActiveShelfId(shelves[0].id);
    }
  }, [shelves, activeShelfId]);

  const setActiveShelf = useCallback((id) => {
    setActiveShelfId(id);
  }, []);

  return {
    shelves,
    activeShelfId,
    setActiveShelf,
    loading,
    error,
    refetch: fetchShelves,
  };
}

export default useShelves;
