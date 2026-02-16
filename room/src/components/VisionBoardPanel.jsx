import { useState, useEffect } from 'react';
import useConfig from '../hooks/useConfig';
import { formatRelativeTime } from '../utils/timeFormat';

const API_URL = import.meta.env.VITE_API_URL || '';

const CATEGORY_STYLES = {
  philosophical: 'bg-purple-500/20 text-purple-400',
  creative: 'bg-pink-500/20 text-pink-400',
  growth: 'bg-green-500/20 text-green-400',
  social: 'bg-blue-500/20 text-blue-400',
  community: 'bg-orange-500/20 text-orange-400',
  practical: 'bg-gray-500/20 text-gray-400',
};

const STATUS_STYLES = {
  active: 'bg-green-500/20 text-green-400',
  idea: 'bg-blue-500/20 text-blue-400',
  paused: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-textMuted/20 text-textMuted',
};

const STATUS_ICONS = {
  active: '🟢',
  idea: '💡',
  paused: '⏸️',
  completed: '✅',
};

/**
 * Aspirations Panel
 * Shows aspirations as cards with linked projects
 */
export default function VisionBoardPanel() {
  const { agentName } = useConfig();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const fetchAspirations = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/shelves/aspirations`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const shelfData = await response.json();
      setData(shelfData.data || { aspirations: [], projects: [], meta: {} });
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAspirations();
    const interval = setInterval(fetchAspirations, 120000);
    return () => clearInterval(interval);
  }, []);

  // Get projects for an aspiration
  const getProjectsForAspiration = (aspirationId) => {
    if (!data?.projects) return [];
    return data.projects.filter((p) => p.aspirationId === aspirationId);
  };

  // Count projects for an aspiration
  const getProjectCount = (aspirationId) => {
    return getProjectsForAspiration(aspirationId).length;
  };

  const aspirations = data?.aspirations || [];
  const hasContent = aspirations.length > 0;

  if (!loading && !error && !hasContent) {
    return (
      <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
        {/* Empty state — no redundant header needed, tab shows name */}
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <span className="text-4xl mb-3 opacity-50">🌟</span>
          <p className="text-textMuted text-sm">Aspirations will appear here</p>
          <p className="text-textMuted/60 text-xs mt-2">Use aspire CLI to add dreams</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
      {/* Subheader */}
      {data?.meta?.updatedAt && (
        <div className="flex items-center justify-end mb-3">
          <span className="text-xs text-textMuted/60">
            {formatRelativeTime(data.meta.updatedAt)}
          </span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0 space-y-3">
        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-20 bg-background/50 rounded-lg"></div>
            <div className="h-20 bg-background/50 rounded-lg"></div>
          </div>
        )}

        {error && <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">{error}</div>}

        {!loading && !error && (
          <>
            {aspirations.map((aspiration) => {
              const projectCount = getProjectCount(aspiration.id);
              const projects = getProjectsForAspiration(aspiration.id);
              const isExpanded = expandedId === aspiration.id;
              const hasProjects = projectCount > 0;

              return (
                <div
                  key={aspiration.id}
                  className={`rounded-lg transition-all duration-200 ${
                    isExpanded ? 'bg-background/70' : 'bg-background/40 hover:bg-background/60'
                  }`}
                >
                  {/* Aspiration Card */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : aspiration.id)}
                    className="w-full text-left p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-yellow-400/80">✦</span>
                          <span className="font-medium text-text text-sm truncate">
                            {aspiration.title}
                          </span>
                        </div>
                        <p className="text-textMuted text-xs line-clamp-2">
                          {aspiration.description}
                        </p>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded-full ${CATEGORY_STYLES[aspiration.category] || CATEGORY_STYLES.philosophical}`}
                          >
                            {aspiration.category}
                          </span>
                          {aspiration.throughline && (
                            <span className="text-[10px] text-textMuted/60">
                              ~ {aspiration.throughline}
                            </span>
                          )}
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded-full ${hasProjects ? 'bg-surface text-textMuted' : 'bg-amber-500/10 text-amber-400/70'}`}
                          >
                            {hasProjects
                              ? `${projectCount} project${projectCount === 1 ? '' : 's'}`
                              : 'no projects yet'}
                          </span>
                        </div>
                      </div>
                      <span
                        className={`text-textMuted/40 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                      >
                        ›
                      </span>
                    </div>
                  </button>

                  {/* Expanded Projects */}
                  {isExpanded && (
                    <div className="px-3 pb-3 pt-0">
                      <div className="border-t border-textMuted/10 pt-2 mt-1">
                        {hasProjects ? (
                          <div className="space-y-1.5">
                            {projects.map((project) => (
                              <div
                                key={project.id}
                                className="flex items-center gap-2 p-2 rounded bg-surface/50"
                              >
                                <span className="text-xs">
                                  {STATUS_ICONS[project.status] || '•'}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <span className="text-sm text-text truncate block">
                                    {project.name}
                                  </span>
                                  <span className="text-xs text-textMuted truncate block">
                                    {project.description}
                                  </span>
                                </div>
                                <span
                                  className={`text-[10px] px-1.5 py-0.5 rounded-full ${STATUS_STYLES[project.status] || STATUS_STYLES.idea}`}
                                >
                                  {project.status}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-textMuted/60 italic py-2">
                            No projects linked yet. Use aspire CLI to add one.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}
