import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { renderMarkdown } from '../../utils/markdown';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Category tag colors
 */
const TAG_COLORS = {
  daily: 'bg-blue-500/20 text-blue-400',
  session: 'bg-purple-500/20 text-purple-400',
  changelog: 'bg-green-500/20 text-green-400',
  correspondence: 'bg-amber-500/20 text-amber-400',
  creative: 'bg-pink-500/20 text-pink-400',
  dream: 'bg-indigo-500/20 text-indigo-400',
  'self-history': 'bg-cyan-500/20 text-cyan-400',
  'soul-history': 'bg-cyan-500/20 text-cyan-400',
  todo: 'bg-orange-500/20 text-orange-400',
  bug: 'bg-red-500/20 text-red-400',
  archive: 'bg-gray-500/20 text-gray-400',
  memory: 'bg-teal-500/20 text-teal-400',
};

/**
 * Format date for display
 */
function formatDisplayDate(dateStr) {
  if (!dateStr) return '';
  try {
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
 * Memory shelf view — Full memory browser with category filters and modal reader
 */
export default function MemoryShelfView({ data }) {
  const [modalFile, setModalFile] = useState(null);
  const [modalBody, setModalBody] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef(null);

  if (!data) return null;

  const allFiles = data?.allFiles || [];

  // Extract unique categories for filter tabs
  const categories = useMemo(() => {
    const counts = {};
    for (const f of allFiles) {
      counts[f.category] = (counts[f.category] || 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([cat, count]) => ({ category: cat, count }));
  }, [allFiles]);

  // Close dropdown on outside click
  useEffect(() => {
    if (!filterOpen) return;
    const handler = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) setFilterOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [filterOpen]);

  // Filtered file list
  const filteredFiles = useMemo(() => {
    let files = activeFilter ? allFiles.filter(f => f.category === activeFilter) : allFiles;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      files = files.filter(f =>
        (f.filename || '').toLowerCase().includes(q) ||
        (f.preview || '').toLowerCase().includes(q) ||
        (f.date || '').includes(q) ||
        (f.category || '').toLowerCase().includes(q)
      );
    }
    return files;
  }, [allFiles, activeFilter, searchQuery]);

  const openFile = useCallback(async (file) => {
    setModalFile(file);
    setModalBody(null);
    setModalLoading(true);
    try {
      // Use path-based endpoint for non-daily, date-based for daily
      const url = file.category === 'daily' && file.date
        ? `${API_URL}/api/memory/daily/${file.date}`
        : `${API_URL}/api/memory/file?path=${encodeURIComponent(file.path)}`;
      const res = await fetch(url);
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
    <div className="flex flex-col h-full">
      {/* Sticky stats header */}
      <div className="shrink-0 space-y-3 pb-3">
        {/* Stats row */}
        <div className="grid grid-cols-5 gap-2">
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{allFiles.length}</div>
            <div className="text-[10px] text-textMuted">Files</div>
          </div>
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{data?.daily?.count || 0}</div>
            <div className="text-[10px] text-textMuted">Days</div>
          </div>
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{data?.sessions?.count || 0}</div>
            <div className="text-[10px] text-textMuted">Sessions</div>
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

        {/* Timeline + Embedding breakdown */}
        <div className="flex items-center justify-between text-xs text-textMuted px-1">
          <span>{sinceText}</span>
          {daysSinceFirst > 0 && <span>{daysSinceFirst} days of memory</span>}
        </div>

        {/* Search + filter row */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories..."
              className="w-full bg-background/50 border border-surface rounded-lg px-3 py-1.5 text-sm text-text placeholder:text-textMuted/40 focus:outline-none focus:border-primary/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-textMuted hover:text-text text-xs"
              >✕</button>
            )}
          </div>

          {/* Category dropdown */}
          <div ref={filterRef} className="relative shrink-0">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                activeFilter
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-surface bg-background/50 text-textMuted hover:text-text'
              }`}
            >
              <span>{activeFilter || 'All'}</span>
              <span className="text-[10px]">▼</span>
            </button>

            {filterOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-surface border border-surface rounded-xl shadow-2xl py-1 z-50 max-h-64 overflow-y-auto">
                <button
                  onClick={() => { setActiveFilter(null); setFilterOpen(false); }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                    !activeFilter ? 'bg-accent/15 text-accent' : 'text-textMuted hover:text-text hover:bg-background/50'
                  }`}
                >
                  <span>All</span>
                  <span className="text-textMuted/50">{allFiles.length}</span>
                </button>
                {categories.map(({ category, count }) => (
                  <button
                    key={category}
                    onClick={() => { setActiveFilter(category); setFilterOpen(false); }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                      activeFilter === category ? 'bg-accent/15 text-accent' : 'text-textMuted hover:text-text hover:bg-background/50'
                    }`}
                  >
                    <span className="capitalize">{category}</span>
                    <span className="text-textMuted/50">{count}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Scrollable file list */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-1.5 pr-1">
        {filteredFiles.length > 0 ? (
          filteredFiles.map((file, i) => (
            <button
              key={file.path || i}
              onClick={() => openFile(file)}
              className="w-full text-left bg-background/40 hover:bg-background/70 rounded-lg p-3 transition-colors"
            >
              <div className="flex items-center justify-between mb-1 gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="text-sm">{file.icon}</span>
                  <span className="text-sm font-medium text-text truncate">
                    {file.date ? formatDisplayDate(file.date) : file.filename}
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${TAG_COLORS[file.category] || 'bg-background/50 text-textMuted'}`}>
                    {file.category}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-textMuted/60 shrink-0">
                  {file.chunks > 0 && <span>{file.chunks}c</span>}
                  <span>{file.size}</span>
                </div>
              </div>
              {file.preview && (
                <p className="text-xs text-textMuted line-clamp-1 pl-7">{file.preview}</p>
              )}
            </button>
          ))
        ) : (
          <div className="text-center py-8">
            <span className="text-3xl opacity-50">📝</span>
            <p className="text-textMuted text-sm mt-2">No memory files yet</p>
          </div>
        )}
      </div>

      {/* File modal */}
      {modalFile && (
        <FileModal
          file={modalFile}
          body={modalBody}
          loading={modalLoading}
          onClose={() => setModalFile(null)}
        />
      )}
    </div>
  );
}

/**
 * Modal for viewing a full memory file
 */
function FileModal({ file, body, loading, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const title = file.date ? formatDisplayDate(file.date) : file.filename;

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
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">{file.icon}</span>
            <h3 className="text-base font-semibold text-text truncate">{title}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${TAG_COLORS[file.category] || 'bg-background/50 text-textMuted'}`}>
              {file.category}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-textMuted hover:text-text text-2xl leading-none p-1 ml-2"
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
