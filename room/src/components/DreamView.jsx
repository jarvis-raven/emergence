import { useState } from 'react';

/**
 * Get insight score color
 *
 * @param {number} score - Insight score (0-10 or 0-100)
 * @returns {string} Tailwind color class
 */
function getInsightColor(score) {
  // Normalize to 0-10 scale
  const normalized = score > 10 ? score / 10 : score;

  if (normalized >= 8) return 'text-purple-400';
  if (normalized >= 6) return 'text-cyan-400';
  return 'text-textMuted';
}

/**
 * Format dream date
 *
 * @param {string|number} dateValue - Date value
 * @returns {string} Formatted date string
 */
function formatDreamDate(dateValue) {
  if (!dateValue) return 'Unknown time';

  try {
    const date = new Date(dateValue);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) return 'Last night';
    if (diffDays === 1) return 'Night before last';
    if (diffDays < 7) return `${diffDays} nights ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return String(dateValue);
  }
}

/**
 * Individual dream card
 *
 * @param {object} props
 * @param {object} props.dream - Dream data
 * @param {boolean} props.expanded - Whether card is expanded
 * @param {function} props.onToggle - Toggle expansion callback
 */
function DreamCard({ dream, expanded, onToggle }) {
  const content = dream.dream || dream.fragment || dream.text || 'No content';
  const score = dream.insight_score || dream.insight || dream.score || 0;
  const date = dream.date || dream.timestamp;

  return (
    <div
      className={`
        bg-surface/50 rounded-lg p-4 cursor-pointer
        border border-transparent
        transition-all duration-300
        hover:bg-surface/80 hover:border-primary/20
        ${expanded ? 'bg-surface border-primary/30' : ''}
      `}
      onClick={onToggle}
    >
      <div className="flex items-start gap-3">
        {/* Dream icon */}
        <span className="text-purple-400/60 text-lg shrink-0" aria-hidden="true">
          💭
        </span>

        <div className="flex-1 min-w-0">
          {/* Dream content */}
          <p
            className={`
            text-text text-sm leading-relaxed
            ${expanded ? '' : 'line-clamp-2'}
          `}
          >
            {content}
          </p>

          {/* Metadata */}
          <div className="flex items-center gap-4 mt-3">
            {/* Insight score - subtle */}
            <span
              className={`
                text-xs font-mono ${getInsightColor(score)}
              `}
              title="Insight score"
            >
              insight {score}/10
            </span>

            {/* Date */}
            {date && <span className="text-xs text-textMuted">{formatDreamDate(date)}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Dream View component for asleep mode
 * Displays dreams from the Dream Engine
 *
 * @param {object} props
 * @param {Array} props.dreams - Array of dream objects
 * @param {Array} props.highlights - Array of highlight objects
 * @param {number} props.totalDreams - Total dream count
 * @param {boolean} props.loading - Whether data is loading
 */
export function DreamView({ dreams, highlights, totalDreams, loading }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  const handleToggle = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-6 bg-surface rounded w-24 animate-pulse" />
          <div className="h-4 bg-surface rounded w-16 animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-surface/50 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (!dreams || dreams.length === 0) {
    return (
      <div className="text-center py-12">
        {/* Moon/stars visual */}
        <div className="text-4xl mb-4 opacity-60" aria-hidden="true">
          🌙✨
        </div>

        <h3 className="text-lg text-text font-medium mb-2">No dreams yet</h3>
        <p className="text-sm text-textMuted max-w-xs mx-auto">
          Dreams come from the Dream Engine. They appear after rest periods when the agent processes
          memories.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text flex items-center gap-2">
          <span aria-hidden="true">🌙</span>
          Dreams
        </h2>
        <span className="text-xs text-textMuted font-mono">
          {totalDreams || dreams.length} fragments
        </span>
      </div>

      {/* Dream list */}
      <div className="space-y-3">
        {dreams.map((dream, index) => (
          <DreamCard
            key={index}
            dream={dream}
            expanded={expandedIndex === index}
            onToggle={() => handleToggle(index)}
          />
        ))}
      </div>

      {/* Highlights section */}
      {highlights && highlights.length > 0 && (
        <div className="pt-4 border-t border-surface mt-4">
          <h3 className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-3">
            ✨ Highlights
          </h3>
          <div className="space-y-2">
            {highlights.slice(0, 2).map((highlight, index) => (
              <p key={index} className="text-xs text-textMuted">
                {highlight.title || highlight}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default DreamView;
