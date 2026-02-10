import { useMemo } from 'react';
import { useApi } from './useApi';

/**
 * Hook to fetch data for a specific shelf
 */
export function useShelfData(shelfId, shelves) {
  const shelf = useMemo(() => {
    return shelves.find((s) => s.id === shelfId) || null;
  }, [shelfId, shelves]);

  const {
    data: rawData,
    loading,
    error,
    refetch,
    lastUpdated,
  } = useApi(shelf?.endpoint || null, {
    refreshInterval: shelf?.refreshIntervalMs || 30000,
    enabled: !!shelf?.endpoint,
  });

  // Extract .data from the envelope (GET /api/shelves/:id returns { status, data, ... })
  const data = rawData?.data ?? rawData;

  return {
    data,
    loading,
    error,
    refetch,
    lastUpdated,
    shelf,
  };
}

export default useShelfData;
