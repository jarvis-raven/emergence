import useConfig from '../hooks/useConfig';
import { useApi } from '../hooks/useApi';
import MemoryShelfView from './shelves/MemoryShelfView';

/**
 * Bookshelf Panel — Memory stats view
 * Shows memory statistics from the Memory shelf
 */
export default function BookshelfPanel() {
  const { agentName } = useConfig();

  const {
    data: memoryRaw,
    loading: memoryLoading,
    error: memoryError,
  } = useApi('/api/shelves/memory', { refreshInterval: 30000 });

  const memoryData = memoryRaw?.data ?? memoryRaw;

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">📚</span>
        <span className="text-xs font-medium text-textMuted uppercase tracking-wider">
          Memory
        </span>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0">
        {/* Loading */}
        {memoryLoading && (
          <div className="animate-pulse space-y-2">
            <div className="grid grid-cols-4 gap-2">
              <div className="h-16 bg-background/50 rounded-lg"></div>
              <div className="h-16 bg-background/50 rounded-lg"></div>
              <div className="h-16 bg-background/50 rounded-lg"></div>
              <div className="h-16 bg-background/50 rounded-lg"></div>
            </div>
          </div>
        )}

        {/* Error */}
        {memoryError && !memoryLoading && (
          <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">
            {memoryError}
          </div>
        )}

        {/* Memory Data */}
        {!memoryLoading && !memoryError && memoryData && (
          <MemoryShelfView data={memoryData} />
        )}

        {/* Empty State */}
        {!memoryLoading && !memoryError && !memoryData && (
          <div className="text-center p-6">
            <div className="text-textMuted/60 text-sm">No memory data available</div>
          </div>
        )}
      </div>
    </div>
  );
}
