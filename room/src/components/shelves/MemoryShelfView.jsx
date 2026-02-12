import { useState, useCallback, useEffect } from 'react';
import { renderMarkdown } from '../../utils/markdown';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Format date for display
 */
function formatDisplayDate(dateStr) {
  try {
    // Compare date strings directly to avoid timezone issues
    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);
    const yesterdayDate = new Date(now);
    yesterdayDate.setDate(yesterdayDate.getDate() - 1);
    const yesterdayStr = yesterdayDate.toISOString().slice(0, 10);

    const date = new Date(dateStr + 'T12:00:00');
    const weekday = date.toLocaleDateString('en-GB', { weekday: 'short' });
    const day = date.getDate();
    const month = date.toLocaleDateString('en-GB', { month: 'short' });

    if (dateStr === todayStr) return `Today — ${weekday} ${day} ${month}`;
    if (dateStr === yesterdayStr) return `Yesterday — ${weekday} ${day} ${month}`;
    
    const diffDays = Math.round((now - date) / 86400000);
    if (diffDays < 7) return `${weekday} ${day} ${month}`;
    return `${day} ${month} ${date.getFullYear()}`;
  } catch {
    return dateStr;
  }
}

/**
 * Memory shelf view — Daily memory browser with modal reader
 */
export default function MemoryShelfView({ data }) {
  const [modalDate, setModalDate] = useState(null);
  const [modalBody, setModalBody] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);

  if (!data) return null;

  const dailyList = data?.dailyList || [];
  const hasDaily = dailyList.length > 0;

  const openDay = useCallback(async (date) => {
    setModalDate(date);
    setModalBody(null);
    setModalLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/memory/daily/${date}`);
      if (res.ok) {
        const json = await res.json();
        setModalBody(json.body || 'No content');
      } else {
        setModalBody('Failed to load');
      }
    } catch {
      setModalBody('Failed to load');
    } finally {
      setModalLoading(false);
    }
  }, []);

  const daysSinceFirst = data?.daily?.daysActive || 0;
  const firstDate = data?.daily?.firstDate;
  const sinceText = firstDate
    ? (() => {
        const date = new Date(firstDate + 'T12:00:00');
        const month = date.toLocaleDateString('en-GB', { month: 'short' });
        const day = date.getDate();
        return `Since ${month} ${day}`;
      })()
    : 'Memory space ready';

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="grid grid-cols-5 gap-2">
        <div className="bg-background/50 rounded-lg p-2 text-center">
          <div className="text-sm font-semibold text-text">{data?.daily?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Days</div>
        </div>
        <div className="bg-background/50 rounded-lg p-2 text-center">
          <div className="text-sm font-semibold text-text">{data?.sessions?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Sessions</div>
        </div>
        <div className="bg-background/50 rounded-lg p-2 text-center">
          <div className="text-sm font-semibold text-text">{data?.dreams?.count || 0}</div>
          <div className="text-[10px] text-textMuted">Dreams</div>
        </div>
        <div className="bg-background/50 rounded-lg p-2 text-center">
          <div className="text-sm font-semibold text-text">{data?.total?.size || '0 B'}</div>
          <div className="text-[10px] text-textMuted">Total</div>
        </div>
        {data?.embeddings && (
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{data.embeddings.chunks?.toLocaleString()}</div>
            <div className="text-[10px] text-textMuted">Embeddings</div>
          </div>
        )}
      </div>

      {/* Timeline info */}
      <div className="flex items-center justify-between text-xs text-textMuted px-1">
        <span>{sinceText}</span>
        {daysSinceFirst > 0 && <span>{daysSinceFirst} days of memory</span>}
      </div>

      {/* Embedding breakdown */}
      {data?.embeddings?.breakdown?.length > 0 && (
        <div className="bg-background/40 rounded-lg p-3">
          <div className="text-xs text-textMuted mb-2 font-medium">Memory Index</div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1">
            {data.embeddings.breakdown.map((b) => (
              <div key={b.category} className="flex items-center justify-between text-xs">
                <span className="text-textMuted capitalize">{b.category}</span>
                <span className="text-textMuted/60 font-mono">
                  {b.files}f / {b.chunks}c
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily files list */}
      {hasDaily ? (
        <div className="space-y-1.5">
          {dailyList.map((day) => (
            <button
              key={day.date}
              onClick={() => openDay(day.date)}
              className="w-full text-left bg-background/40 hover:bg-background/70 rounded-lg p-3 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-text">
                  {formatDisplayDate(day.date)}
                </span>
                <div className="flex items-center gap-3 text-xs text-textMuted/60">
                  {day.chunks > 0 && <span title="Embeddings">{day.chunks} chunks</span>}
                  <span>{day.size}</span>
                </div>
              </div>
              {day.preview && (
                <p className="text-xs text-textMuted line-clamp-2">{day.preview}</p>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <span className="text-3xl opacity-50">📝</span>
          <p className="text-textMuted text-sm mt-2">No daily memories yet</p>
          <p className="text-textMuted/60 text-xs mt-1">Memories accumulate over time</p>
        </div>
      )}

      {/* Daily file modal */}
      {modalDate && (
        <DailyModal
          date={modalDate}
          body={modalBody}
          loading={modalLoading}
          onClose={() => setModalDate(null)}
        />
      )}
    </div>
  );
}

/**
 * Modal for viewing a full daily memory file
 */
function DailyModal({ date, body, loading, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-2xl border border-textMuted/20 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-textMuted/10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">📅</span>
            <h3 className="text-base font-semibold text-text">
              {formatDisplayDate(date)}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-textMuted hover:text-text text-2xl leading-none p-1"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="p-4 overflow-y-auto flex-1 min-h-0">
          {loading ? (
            <div className="py-8 text-center text-textMuted/50 animate-pulse">Loading...</div>
          ) : body ? (
            <div
              className="prose prose-invert prose-sm max-w-none text-textMuted leading-relaxed
                [&_h1]:text-base [&_h1]:text-text [&_h1]:mt-4 [&_h1]:mb-2
                [&_h2]:text-sm [&_h2]:text-text [&_h2]:mt-3 [&_h2]:mb-1
                [&_h3]:text-sm [&_h3]:text-text/80 [&_h3]:mt-2 [&_h3]:mb-1
                [&_p]:mb-2 [&_p]:text-sm
                [&_ul]:mb-2 [&_li]:text-sm
                [&_blockquote]:border-l-2 [&_blockquote]:border-primary/30 [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-textMuted/70
                [&_code]:text-xs [&_code]:bg-background/50 [&_code]:px-1 [&_code]:rounded
                [&_hr]:border-textMuted/10 [&_hr]:my-3"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
