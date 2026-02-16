import { useState } from 'react';
import useConfig from '../hooks/useConfig';
import useIdentity from '../hooks/useIdentity';
import { renderMarkdown } from '../utils/markdown';
import { formatRelativeTime } from '../utils/timeFormat';

/**
 * Mirror Panel — F021
 * Displays SOUL.md and SELF.md content
 * Tab toggle between them, markdown rendered to clean HTML
 */
export default function MirrorPanel() {
  const { agentName } = useConfig();
  const [activeTab, setActiveTab] = useState('self'); // 'self' or 'soul'
  const { data, loading, error, refetch, content, exists, modified } = useIdentity(activeTab);

  const handleRefresh = () => {
    refetch();
  };

  // Empty state when file doesn't exist
  if (!loading && !error && !exists) {
    return (
      <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
        {/* Empty state - no header needed */}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-background/50 rounded-lg p-1">
          {['self', 'soul'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === tab ? 'bg-surface text-text' : 'text-textMuted hover:text-text'
              }`}
            >
              {tab === 'self' ? 'Self' : 'Soul'}
            </button>
          ))}
        </div>

        {/* Empty state */}
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <span className="text-4xl mb-3 opacity-50">🌱</span>
          <p className="text-textMuted text-sm">
            {agentName} is still finding {activeTab === 'self' ? 'their voice' : 'their core'}...
          </p>
          <p className="text-textMuted/60 text-xs mt-2">
            {activeTab === 'self'
              ? 'First Light will create this as they awaken.'
              : 'Define the behavioral core to begin.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
      {/* Subheader */}
      {!loading && modified && (
        <div className="flex items-center justify-end mb-3">
          <span className="text-xs text-textMuted/60">{formatRelativeTime(modified)}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-background/50 rounded-lg p-1">
        {['self', 'soul'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === tab ? 'bg-surface text-text' : 'text-textMuted hover:text-text'
            }`}
          >
            {tab === 'self' ? 'Self' : 'Soul'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0">
        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-background/50 rounded w-3/4"></div>
            <div className="h-3 bg-background/50 rounded w-full"></div>
            <div className="h-3 bg-background/50 rounded w-5/6"></div>
            <div className="h-3 bg-background/50 rounded w-4/5"></div>
          </div>
        )}

        {error && <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">{error}</div>}

        {!loading && !error && content && (
          <div
            className="prose prose-invert prose-xs max-w-none text-sm leading-snug"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        )}
      </div>
    </div>
  );
}
