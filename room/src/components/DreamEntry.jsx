/**
 * DreamEntry component - Beautiful, readable dream formatting
 *
 * Displays dream fragments with:
 * - Prominent dream text (italic)
 * - Visual insight score badge
 * - Concept tags/pills
 * - Compact source list
 * - Date grouping support
 */

/**
 * Get insight score color and label
 *
 * @param {number} score - Insight score (0-100)
 * @returns {object} { colorClass, label, bgClass }
 */
function getInsightColorScheme(score) {
  if (score >= 90) {
    return {
      colorClass: 'text-purple-400',
      bgClass: 'bg-purple-500/20',
      label: 'profound',
    };
  }
  if (score >= 70) {
    return {
      colorClass: 'text-cyan-400',
      bgClass: 'bg-cyan-500/20',
      label: 'insightful',
    };
  }
  if (score >= 50) {
    return {
      colorClass: 'text-blue-400',
      bgClass: 'bg-blue-500/20',
      label: 'notable',
    };
  }
  return {
    colorClass: 'text-textMuted',
    bgClass: 'bg-surface/30',
    label: 'subtle',
  };
}

/**
 * Individual dream entry
 *
 * @param {object} props
 * @param {object} props.dream - Dream object with fragment, insight_score, concepts, sources
 * @param {boolean} props.compact - Compact mode (smaller, less spacing)
 */
export function DreamEntry({ dream, compact = false }) {
  const { fragment, insight_score = 0, concepts = [], sources = [] } = dream;

  const { colorClass, bgClass, label } = getInsightColorScheme(insight_score);

  return (
    <div
      className={`
      ${compact ? 'p-3' : 'p-4'}
      bg-surface/30 rounded-lg
      border border-indigo-500/10
      hover:border-indigo-500/20
      hover:bg-surface/40
      transition-all duration-200
    `}
    >
      {/* Dream icon + insight badge */}
      <div className="flex items-start gap-3 mb-3">
        <span className="text-lg shrink-0" aria-hidden="true">
          💭
        </span>

        <div className="flex-1 min-w-0">
          {/* Insight score badge */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`
              inline-flex items-center gap-1.5
              px-2 py-0.5 rounded-full
              ${bgClass}
              text-xs font-medium ${colorClass}
            `}
            >
              <span className="font-mono">{insight_score}</span>
              <span className="text-[10px] opacity-70">{label}</span>
            </span>
          </div>

          {/* Dream fragment - prominent, italic */}
          <p
            className={`
            ${compact ? 'text-sm' : 'text-base'}
            text-text/90 italic leading-relaxed mb-3
          `}
          >
            {fragment}
          </p>

          {/* Concepts as pills */}
          {concepts && concepts.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {concepts.map((concept, i) => (
                <span
                  key={i}
                  className="
                    inline-block px-2 py-0.5 rounded-full
                    bg-indigo-500/10 text-indigo-300/80
                    text-xs font-medium
                  "
                >
                  {concept}
                </span>
              ))}
            </div>
          )}

          {/* Sources - small, unobtrusive */}
          {sources && sources.length > 0 && (
            <div className="text-xs text-textMuted/60">
              <span className="opacity-50">Sources:</span> {sources.join(', ')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Group of dreams by date
 *
 * @param {object} props
 * @param {string} props.date - Date string (YYYY-MM-DD)
 * @param {Array} props.dreams - Array of dream objects
 * @param {boolean} props.compact - Compact mode
 */
export function DreamGroup({ date, dreams, compact = false }) {
  if (!dreams || dreams.length === 0) return null;

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr + 'T12:00:00');
      const month = d.toLocaleDateString('en-US', { month: 'short' });
      const day = d.getDate();
      const year = d.getFullYear();
      return `${month} ${day}, ${year}`;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-3">
      {/* Date header */}
      {date && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold text-indigo-400/70 uppercase tracking-wide">
            {formatDate(date)}
          </span>
          <div className="flex-1 h-px bg-indigo-500/10" />
        </div>
      )}

      {/* Dreams */}
      <div className="space-y-2">
        {dreams.map((dream, i) => (
          <DreamEntry key={i} dream={dream} compact={compact} />
        ))}
      </div>
    </div>
  );
}

/**
 * Dream list with optional grouping
 *
 * @param {object} props
 * @param {Array} props.dreams - Array of dream objects
 * @param {boolean} props.groupByDate - Whether to group by date
 * @param {boolean} props.compact - Compact mode
 */
export function DreamList({ dreams, groupByDate = false, compact = false }) {
  if (!dreams || dreams.length === 0) {
    return (
      <div className="text-center py-8">
        <span className="text-3xl opacity-50">💭</span>
        <p className="text-textMuted text-sm mt-2">No dreams recorded</p>
      </div>
    );
  }

  if (!groupByDate) {
    return (
      <div className="space-y-2">
        {dreams.map((dream, i) => (
          <DreamEntry key={i} dream={dream} compact={compact} />
        ))}
      </div>
    );
  }

  // Group by date
  const grouped = dreams.reduce((acc, dream) => {
    const date = dream.date || dream.generated_at?.split('T')[0] || 'unknown';
    if (!acc[date]) acc[date] = [];
    acc[date].push(dream);
    return acc;
  }, {});

  const sortedDates = Object.keys(grouped).sort().reverse();

  return (
    <div className="space-y-6">
      {sortedDates.map((date) => (
        <DreamGroup key={date} date={date} dreams={grouped[date]} compact={compact} />
      ))}
    </div>
  );
}

/**
 * Parse dream JSON file content
 * Handles different dream file formats
 *
 * @param {string} jsonString - JSON string content
 * @returns {Array|null} Array of dreams or null if invalid
 */
export function parseDreamFile(jsonString) {
  try {
    const data = JSON.parse(jsonString);

    // Handle different formats
    if (Array.isArray(data)) {
      return data;
    }

    if (data.dreams && Array.isArray(data.dreams)) {
      return data.dreams;
    }

    if (data.fragments && Array.isArray(data.fragments)) {
      return data.fragments;
    }

    // Single dream object
    if (data.fragment || data.dream) {
      return [data];
    }

    return null;
  } catch (e) {
    console.error('Failed to parse dream JSON:', e);
    return null;
  }
}

export default DreamEntry;
