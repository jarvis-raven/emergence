import useApi from './useApi.js';

/**
 * Hook to fetch dream data
 * Auto-refreshes every 60 seconds (dreams change less frequently)
 *
 * @param {object} options - Hook options
 * @param {boolean} options.enabled - Whether to fetch
 * @returns {object} { dreams, highlights, totalDreams, loading, error, refetch, lastUpdated }
 */
export function useDreams(options = {}) {
  const { enabled = true } = options;

  const { data, loading, error, refetch, lastUpdated, isStale } = useApi('/api/dreams', {
    refreshInterval: 60000, // 60 seconds (dreams change less frequently)
    enabled,
    transform: (rawData) => {
      // Ensure consistent data structure
      return {
        dreams: rawData.dreams || [],
        highlights: rawData.highlights || [],
        totalDreams: rawData.totalDreams || 0,
        raw: rawData,
      };
    },
  });

  return {
    dreams: data?.dreams || [],
    highlights: data?.highlights || [],
    totalDreams: data?.totalDreams || 0,
    rawData: data?.raw,
    loading,
    error,
    refetch,
    lastUpdated,
    isStale,
  };
}

export default useDreams;
