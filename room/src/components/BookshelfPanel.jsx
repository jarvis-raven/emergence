import { useState } from 'react';
import useConfig from '../hooks/useConfig';
import { useApi } from '../hooks/useApi';
import ShelfRenderer from './shelves/ShelfRenderer';

/**
 * Bookshelf Panel — Dynamic shelf view
 * Fetches available shelves from API, renders tabs and selected shelf content.
 * Custom shelves (like Library) appear alongside built-in ones.
 */

// Shelves to show in the Bookshelf panel (by renderer type or id)
// 'memory' is always first, then custom shelves
const BOOKSHELF_SHELF_IDS = ['memory', 'library'];

export default function BookshelfPanel() {
  const { agentName } = useConfig();
  const [activeShelf, setActiveShelf] = useState('memory');

  // Fetch shelf registry
  const { data: shelvesRaw, loading: shelvesLoading } = useApi('/api/shelves', {
    refreshInterval: 60000,
  });

  const allShelves = shelvesRaw?.shelves ?? [];

  // Filter to only bookshelf-relevant shelves
  const visibleShelves = allShelves.filter(
    (s) => BOOKSHELF_SHELF_IDS.includes(s.id) || BOOKSHELF_SHELF_IDS.includes(s.renderer),
  );

  // Fetch active shelf data
  const activeShelfMeta = visibleShelves.find(
    (s) => s.id === activeShelf || s.renderer === activeShelf,
  );
  const endpoint = activeShelfMeta?.endpoint || `/api/shelves/${activeShelf}`;

  const {
    data: shelfDataRaw,
    loading: dataLoading,
    error: dataError,
  } = useApi(endpoint, { refreshInterval: 30000 });

  const shelfData = shelfDataRaw?.data ?? shelfDataRaw;

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col overflow-hidden">
      {/* Shelf Tabs */}
      <div className="flex items-center gap-1 mb-3 overflow-x-auto">
        {visibleShelves.length > 0 ? (
          visibleShelves.map((shelf) => {
            const isActive = shelf.id === activeShelf || shelf.renderer === activeShelf;
            return (
              <button
                key={shelf.id}
                onClick={() => setActiveShelf(shelf.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-accent/20 text-accent'
                    : 'text-textMuted hover:text-text hover:bg-background/50'
                }`}
              >
                {shelf.icon && <span>{shelf.icon}</span>}
                <span>{shelf.name}</span>
              </button>
            );
          })
        ) : (
          <>
            <button
              onClick={() => setActiveShelf('memory')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                activeShelf === 'memory'
                  ? 'bg-accent/20 text-accent'
                  : 'text-textMuted hover:text-text hover:bg-background/50'
              }`}
            >
              <span>🧠</span>
              <span>Memory</span>
            </button>
          </>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0">
        {/* Loading */}
        {(shelvesLoading || dataLoading) && (
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
        {dataError && !dataLoading && (
          <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">{dataError}</div>
        )}

        {/* Shelf Content */}
        {!dataLoading && !dataError && shelfData && activeShelfMeta && (
          <ShelfRenderer shelf={activeShelfMeta} data={shelfData} />
        )}

        {/* Empty State */}
        {!dataLoading && !dataError && !shelfData && (
          <div className="text-center p-6">
            <div className="text-textMuted/60 text-sm">No data available</div>
          </div>
        )}
      </div>
    </div>
  );
}
