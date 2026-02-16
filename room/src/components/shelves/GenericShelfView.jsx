/**
 * Generic shelf view — fallback renderer for unknown shelf types
 * Renders key-value pairs, arrays, or primitives as cards
 */

const MAX_DEPTH = 2;

function renderValue(value, depth = 0) {
  if (value === null || value === undefined) {
    return <span className="text-textMuted/50 italic">null</span>;
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className="text-text">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-textMuted/50 italic">empty array</span>;
    if (depth >= MAX_DEPTH)
      return <span className="text-textMuted/50 italic">[{value.length} items]</span>;
    return (
      <ul className="space-y-1">
        {value.map((item, index) => (
          <li key={index} className="text-sm">
            <span className="text-textMuted/60 mr-2">[{index}]</span>
            {renderValue(item, depth + 1)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (entries.length === 0) return <span className="text-textMuted/50 italic">empty object</span>;
    if (depth >= MAX_DEPTH) return <span className="text-textMuted/50 italic">{'{...}'}</span>;
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {entries.map(([key, val]) => (
          <div key={key} className="bg-background/50 rounded-lg p-3">
            <div className="text-xs text-textMuted uppercase tracking-wider mb-1">{key}</div>
            <div className="text-sm">{renderValue(val, depth + 1)}</div>
          </div>
        ))}
      </div>
    );
  }

  return <span className="text-textMuted/50">unknown</span>;
}

export default function GenericShelfView({ data }) {
  if (data === null || data === undefined) {
    return (
      <div className="text-center p-4 bg-background/50 rounded-lg">
        <span className="text-textMuted/50 italic">No data available</span>
      </div>
    );
  }

  if (typeof data !== 'object') {
    return (
      <div className="bg-background/50 rounded-lg p-3">
        <div className="text-text">{String(data)}</div>
      </div>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <div className="text-center p-4 bg-background/50 rounded-lg">
          <span className="text-textMuted/50 italic">Empty array</span>
        </div>
      );
    }
    return (
      <div className="space-y-2">
        {data.map((item, index) => (
          <div key={index} className="bg-background/50 rounded-lg p-3">
            <div className="text-xs text-textMuted/60 mb-1">Item {index + 1}</div>
            {renderValue(item, 1)}
          </div>
        ))}
      </div>
    );
  }

  const entries = Object.entries(data);
  if (entries.length === 0) {
    return (
      <div className="text-center p-4 bg-background/50 rounded-lg">
        <span className="text-textMuted/50 italic">Empty object</span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="bg-background/50 rounded-lg p-3">
          <div className="text-xs text-textMuted uppercase tracking-wider mb-1">{key}</div>
          <div className="text-sm">{renderValue(value, 1)}</div>
        </div>
      ))}
    </div>
  );
}
