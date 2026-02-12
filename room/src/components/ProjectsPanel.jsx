import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

const STATUS_ORDER = ['active', 'idea', 'paused', 'completed'];
const STATUS_LABELS = { active: 'Active', idea: 'Ideas', paused: 'Paused', completed: 'Completed' };
const STATUS_STYLES = {
  active: 'bg-green-500/20 text-green-400',
  idea: 'bg-blue-500/20 text-blue-400',
  paused: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-textMuted/20 text-textMuted',
};

const CATEGORY_STYLES = {
  framework: 'bg-purple-500/20 text-purple-400',
  tool: 'bg-cyan-500/20 text-cyan-400',
  creative: 'bg-pink-500/20 text-pink-400',
  community: 'bg-orange-500/20 text-orange-400',
  personal: 'bg-textMuted/15 text-textMuted',
};

/**
 * Project detail modal
 */
function ProjectModal({ project, aspiration, onClose }) {
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  if (!project) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-surface rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-textMuted/10"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-textMuted hover:text-text transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Header */}
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-text mb-2">{project.name}</h2>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[project.status] || STATUS_STYLES.idea}`}>
              {STATUS_LABELS[project.status] || project.status}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_STYLES[project.category] || CATEGORY_STYLES.personal}`}>
              {project.category}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-text mb-3">{project.description}</p>

        {/* Details */}
        {project.details && (
          <div className="text-sm text-textMuted mb-4 p-3 bg-background/50 rounded-lg">
            {project.details}
          </div>
        )}

        {/* Aspiration */}
        {aspiration && (
          <div className="mb-4 p-3 bg-background/50 rounded-lg">
            <p className="text-xs text-textMuted/60 mb-1">Serves aspiration:</p>
            <div className="flex items-center gap-2">
              <span className="text-yellow-400/70">✦</span>
              <span className="text-sm text-text">{aspiration.title}</span>
            </div>
          </div>
        )}

        {/* Links */}
        {project.links && Object.keys(project.links).length > 0 && (
          <div className="space-y-1 mb-4">
            {project.links.repo && (
              <a href={project.links.repo} target="_blank" rel="noopener noreferrer"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1">
                🔗 Repository
              </a>
            )}
            {project.links.local && (
              <p className="text-sm text-textMuted">📁 {project.links.local}</p>
            )}
            {project.links.url && (
              <a href={project.links.url} target="_blank" rel="noopener noreferrer"
                className="text-sm text-primary hover:text-primary/80 flex items-center gap-1">
                🌐 Link
              </a>
            )}
          </div>
        )}

        {/* Dates */}
        <div className="flex items-center gap-4 text-xs text-textMuted/60">
          {project.startDate && (
            <span>Started: {project.startDate}</span>
          )}
          {project.updatedAt && (
            <span>Updated: {project.updatedAt}</span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Projects Panel — reads from aspirations shelf, groups by status
 */
export default function ProjectsPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/shelves/aspirations`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const shelfData = await res.json();
      setData(shelfData.data || { aspirations: [], projects: [] });
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Get aspiration for a project
  const getAspiration = (aspirationId) => {
    if (!data?.aspirations) return null;
    return data.aspirations.find(a => a.id === aspirationId) || null;
  };

  // Get selected project details
  const selectedProject = selected ? (data?.projects || []).find(p => p.id === selected) : null;
  const selectedAspiration = selectedProject ? getAspiration(selectedProject.aspirationId) : null;

  // Group by status
  const projects = data?.projects || [];
  const grouped = {};
  for (const s of STATUS_ORDER) grouped[s] = [];
  for (const p of projects) {
    const key = STATUS_ORDER.includes(p.status) ? p.status : 'idea';
    grouped[key].push(p);
  }

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
      {/* Subheader */}
      {!loading && !error && (
        <div className="flex items-center justify-end mb-3">
          <span className="text-xs text-textMuted/60">{projects.length} total</span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0 space-y-4">
        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-14 bg-background/50 rounded-lg"></div>
            <div className="h-14 bg-background/50 rounded-lg"></div>
            <div className="h-14 bg-background/50 rounded-lg"></div>
          </div>
        )}

        {error && (
          <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">{error}</div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
            <span className="text-4xl mb-3 opacity-50">🚀</span>
            <p className="text-textMuted text-sm">No projects yet</p>
            <p className="text-textMuted/60 text-xs mt-2">Use aspire CLI to add projects</p>
          </div>
        )}

        {!loading && !error && STATUS_ORDER.map(status => {
          const items = grouped[status];
          if (!items || items.length === 0) return null;
          return (
            <section key={status}>
              <h3 className="text-xs font-medium text-textMuted/70 uppercase tracking-wider mb-2">
                {STATUS_LABELS[status]} ({items.length})
              </h3>
              <div className="space-y-1.5">
                {items.map((project) => {
                  const aspiration = getAspiration(project.aspirationId);
                  return (
                    <button
                      key={project.id}
                      onClick={() => setSelected(project.id)}
                      className="w-full text-left p-3 bg-background/50 rounded-lg hover:bg-background/80 transition-colors group"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-text truncate">{project.name}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${CATEGORY_STYLES[project.category] || CATEGORY_STYLES.personal}`}>
                              {project.category}
                            </span>
                          </div>
                          {project.description && (
                            <p className="text-xs text-textMuted mt-0.5 truncate">{project.description}</p>
                          )}
                          {aspiration && (
                            <p className="text-[10px] text-textMuted/60 mt-1">
                              ✦ {aspiration.title}
                            </p>
                          )}
                        </div>
                        <span className="text-textMuted/40 group-hover:text-textMuted transition-colors flex-shrink-0">
                          ›
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      {/* Modal */}
      {selected && (
        <ProjectModal
          project={selectedProject}
          aspiration={selectedAspiration}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
