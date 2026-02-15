import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import ShelfRenderer from './shelves/ShelfRenderer';
import MirrorPanel from './MirrorPanel';
import WorkshopPanel from './WorkshopPanel';
import VisionBoardPanel from './VisionBoardPanel';
import ProjectsPanel from './ProjectsPanel';

/**
 * Built-in panel components mapped by tab ID.
 * These are legacy panels that predate the shelf system.
 * Over time, these should migrate to proper shelf renderers.
 */
const BUILTIN_PANELS = {
  mirror: MirrorPanel,
  journal: WorkshopPanel,     // renamed from 'workshop'
  aspirations: VisionBoardPanel,
  projects: ProjectsPanel,
};

/**
 * Tab definitions — order matters.
 * 'shelf:xxx' tabs load dynamically from the shelf registry.
 * Others use BUILTIN_PANELS.
 */
/**
 * Core tabs in display order.
 * Custom shelves (e.g. library) are discovered and appended after these.
 */
const DEFAULT_TABS = [
  { id: 'mirror',        icon: '🪞', label: 'Mirror' },
  { id: 'shelf:memory',  icon: '🧠', label: 'Memory' },
  { id: 'shelf:nautilus', icon: '🐚', label: 'Nautilus' },
  { id: 'journal',       icon: '📓', label: 'Journal' },
  { id: 'aspirations',   icon: '✨', label: 'Aspirations' },
  { id: 'projects',      icon: '🚀', label: 'Projects' },
];

/**
 * Dynamic shelf content loader
 * Fetches shelf data from API and renders via ShelfRenderer
 */
function ShelfContent({ shelfId, shelfMeta }) {
  const endpoint = shelfMeta?.endpoint || `/api/shelves/${shelfId}`;
  
  const { data: raw, loading, error } = useApi(endpoint, { refreshInterval: 30000 });
  const data = raw?.data ?? raw;

  if (loading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-6 bg-background/50 rounded w-1/3"></div>
        <div className="h-4 bg-background/50 rounded w-2/3"></div>
        <div className="h-32 bg-background/50 rounded"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-danger/80">
        <p className="text-sm">Error loading {shelfId}: {error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 text-center text-textMuted">
        <p className="text-sm">No data available</p>
      </div>
    );
  }

  return <ShelfRenderer shelf={shelfMeta || { id: shelfId, renderer: shelfId }} data={data} />;
}

/**
 * ShelfPanel — Main content area with dynamic tabs
 * 
 * Combines built-in panels (Mirror, Journal, Aspirations, Projects)
 * with dynamic shelf-based content (Memory, Library, custom shelves).
 * Tabs are rendered in a horizontal bar; content fills the remaining space.
 */
export default function ShelfPanel({ agentName, forceTab }) {
  const [activeTab, setActiveTab] = useState(forceTab ? `shelf:${forceTab}` : 'mirror');
  const [tabs, setTabs] = useState(DEFAULT_TABS);

  // Sync with forceTab from parent
  useEffect(() => {
    if (forceTab) setActiveTab(`shelf:${forceTab}`);
  }, [forceTab]);

  // Fetch shelf registry to discover custom shelves
  const { data: shelvesRaw } = useApi('/api/shelves', { refreshInterval: 60000 });
  const allShelves = shelvesRaw?.shelves ?? [];

  // Build shelf metadata lookup
  const shelfMeta = {};
  allShelves.forEach(s => { shelfMeta[s.id] = s; });

  // Merge discovered shelves into tabs (add any custom ones not in DEFAULT_TABS)
  useEffect(() => {
    if (allShelves.length === 0) return;

    // Collect all shelf IDs already represented in default tabs (both shelf: and builtin)
    const knownShelfIds = DEFAULT_TABS
      .filter(t => t.id.startsWith('shelf:'))
      .map(t => t.id.replace('shelf:', ''));
    const knownBuiltinIds = DEFAULT_TABS
      .filter(t => !t.id.startsWith('shelf:'))
      .map(t => t.id);

    const customShelves = allShelves.filter(s => 
      !knownShelfIds.includes(s.id) && 
      !knownBuiltinIds.includes(s.id) &&
      !['drives', 'budget-transparency', 'pending-reviews', 'latent-drives'].includes(s.id) &&
      s.status === 'active'
    );

    if (customShelves.length > 0) {
      const customTabs = customShelves.map(s => ({
        id: `shelf:${s.id}`,
        icon: s.icon || '📋',
        label: s.name || s.id,
      }));

      // Append custom tabs after core panels
      const merged = [...DEFAULT_TABS, ...customTabs];
      setTabs(merged);
    }
  }, [allShelves.length]);

  // Resolve active content
  const isShelfTab = activeTab.startsWith('shelf:');
  const shelfId = isShelfTab ? activeTab.replace('shelf:', '') : null;
  const BuiltinComponent = !isShelfTab ? BUILTIN_PANELS[activeTab] : null;

  return (
    <div className="h-full flex flex-col bg-surface rounded-2xl border border-surface overflow-hidden">
      {/* Tab Bar — only show when not forced to a specific tab */}
      {!forceTab && (
        <div className="flex items-center gap-0.5 px-3 pt-3 pb-2 overflow-x-auto border-b border-background/50 shrink-0">
          {tabs.map((tab) => {
            const isActive = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium 
                  whitespace-nowrap transition-all duration-200
                  ${isActive
                    ? 'bg-accent/20 text-accent shadow-sm'
                    : 'text-textMuted hover:text-text hover:bg-background/50'
                  }
                `}
              >
                {tab.icon && <span className="text-sm">{tab.icon}</span>}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4">
        {isShelfTab ? (
          <ShelfContent 
            shelfId={shelfId} 
            shelfMeta={shelfMeta[shelfId]} 
          />
        ) : BuiltinComponent ? (
          <BuiltinComponent agentName={agentName} />
        ) : (
          <div className="text-center py-12 text-textMuted">
            <p>Unknown tab: {activeTab}</p>
          </div>
        )}
      </div>
    </div>
  );
}
