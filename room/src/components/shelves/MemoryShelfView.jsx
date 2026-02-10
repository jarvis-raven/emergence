/**
 * Memory shelf view - extracted from original BookshelfPanel
 * Data shape matches /api/memory/stats
 */
export default function MemoryShelfView({ data }) {
  if (!data) return null;

  const daysSinceFirst = data?.daily?.daysActive || 0;
  const firstDate = data?.daily?.firstDate;

  const sinceText = firstDate
    ? (() => {
        const date = new Date(firstDate);
        const month = date.toLocaleDateString('en-GB', { month: 'short' });
        const day = date.getDate();
        return `Since ${month} ${day}`;
      })()
    : 'Memory space ready';

  return (
    <div className="space-y-2">
      {/* Main stats */}
      <div className="grid grid-cols-4 gap-1.5">
        <div className="bg-background/50 rounded-lg p-1.5 text-center">
          <div className="text-sm font-semibold text-text">{data?.daily?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Memories</div>
        </div>
        <div className="bg-background/50 rounded-lg p-1.5 text-center">
          <div className="text-sm font-semibold text-text">{data?.total?.size || '0 B'}</div>
          <div className="text-[10px] text-textMuted">Size</div>
        </div>
        <div className="bg-background/50 rounded-lg p-1.5 text-center">
          <div className="text-sm font-semibold text-text">{data?.sessions?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Sessions</div>
        </div>
        <div className="bg-background/50 rounded-lg p-1.5 text-center">
          <div className="text-sm font-semibold text-text">{data?.dreams?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Dreams</div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-background/50 rounded-lg p-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-textMuted">{sinceText}</span>
          {daysSinceFirst > 0 && (
            <span className="text-xs text-textMuted/60">{daysSinceFirst} days of logging</span>
          )}
        </div>
      </div>

      {/* Recent activity chart */}
      {data?.recent && data.recent.length > 0 && (
        <div className="bg-background/50 rounded-lg p-2">
          <div className="text-xs text-textMuted mb-2">Recent activity</div>
          <div className="flex items-end gap-px h-8">
            {data.recent.map((day, i) => {
              const maxSize = Math.max(...data.recent.map(d => {
                const num = parseFloat(d.size);
                return isNaN(num) ? 0 : num;
              }));
              const dayNum = parseFloat(day.size) || 0;
              const height = maxSize > 0 ? (dayNum / maxSize) * 100 : 0;
              
              return (
                <div
                  key={i}
                  className="flex-1 bg-primary/30 hover:bg-primary/50 rounded-t transition-colors relative group"
                  style={{ height: `${Math.max(height, 10)}%` }}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-textMuted whitespace-nowrap bg-surface px-2 py-1 rounded">
                    {day.date}: {day.size}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-xs text-textMuted/40">{data.recent[0]?.date?.slice(5)}</span>
            <span className="text-xs text-textMuted/40">{data.recent[data.recent.length - 1]?.date?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* Empty state */}
      {data?.total?.files === 0 && (
        <div className="text-center p-4">
          <span className="text-2xl opacity-50">📝</span>
          <p className="text-textMuted text-sm mt-2">Memory space ready</p>
          <p className="text-textMuted/60 text-xs mt-1">Memories will accumulate here</p>
        </div>
      )}
    </div>
  );
}
