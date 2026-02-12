import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import useConfig from '../hooks/useConfig';
import useSessions from '../hooks/useSessions';
import { formatRelativeTime, formatFullDate } from '../utils/timeFormat';
import { renderMarkdown } from '../utils/markdown';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Drive emoji mapping
 */
const DRIVE_EMOJI = {
  CARE: '💚', CURIOSITY: '🔍', CREATIVE: '🎨', SOCIAL: '💬',
  MAINTENANCE: '🔧', REST: '😴', LEARNING: '📚', PLAY: '🎮',
  EMBODIMENT: '👁️', READING: '📖', ANXIETY: '😰',
};

const DRIVE_COLORS = {
  CARE: 'bg-green-500/20 text-green-400',
  CURIOSITY: 'bg-yellow-500/20 text-yellow-400',
  CREATIVE: 'bg-pink-500/20 text-pink-400',
  SOCIAL: 'bg-blue-500/20 text-blue-400',
  MAINTENANCE: 'bg-gray-500/20 text-gray-400',
  REST: 'bg-indigo-500/20 text-indigo-400',
  LEARNING: 'bg-purple-500/20 text-purple-400',
  PLAY: 'bg-orange-500/20 text-orange-400',
  EMBODIMENT: 'bg-amber-500/20 text-amber-400',
  READING: 'bg-cyan-500/20 text-cyan-400',
  ANXIETY: 'bg-red-500/20 text-red-400',
};

function getDriveEmoji(drive) {
  return DRIVE_EMOJI[drive?.toUpperCase()] || '⚡';
}

function getDriveColor(drive) {
  return DRIVE_COLORS[drive?.toUpperCase()] || 'bg-background/50 text-textMuted';
}

/**
 * Journal Panel — Session browser with search and drive filter
 */
export default function WorkshopPanel() {
  const { agentName } = useConfig();
  const [modalSession, setModalSession] = useState(null);
  const [modalBody, setModalBody] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDrive, setSelectedDrive] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef(null);

  // Load all sessions (no drive filter at API level — we filter client-side for search)
  const { sessions, loading, error, refetch, count } = useSessions({ limit: 100 });

  // Close dropdown on outside click
  useEffect(() => {
    if (!filterOpen) return;
    const handler = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) setFilterOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [filterOpen]);

  // Drive categories with counts
  const driveCategories = useMemo(() => {
    const counts = {};
    for (const s of sessions) {
      const d = s.drive || 'Unknown';
      counts[d] = (counts[d] || 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([drive, count]) => ({ drive, count }));
  }, [sessions]);

  // Filtered sessions
  const filteredSessions = useMemo(() => {
    let list = selectedDrive ? sessions.filter(s => s.drive === selectedDrive) : sessions;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(s =>
        (s.summary || '').toLowerCase().includes(q) ||
        (s.drive || '').toLowerCase().includes(q) ||
        (s.filename || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [sessions, selectedDrive, searchQuery]);

  const openSession = useCallback(async (session) => {
    setModalSession(session);
    setModalBody(null);
    setModalLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/sessions/${session.filename}`);
      if (res.ok) {
        const data = await res.json();
        setModalBody(data.body || 'No content');
      } else {
        setModalBody('Failed to load content');
      }
    } catch {
      setModalBody('Failed to load content');
    } finally {
      setModalLoading(false);
    }
  }, []);

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
      {/* Sticky header */}
      <div className="shrink-0 space-y-3 pb-3">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{count}</div>
            <div className="text-[10px] text-textMuted">Sessions</div>
          </div>
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{driveCategories.length}</div>
            <div className="text-[10px] text-textMuted">Drives</div>
          </div>
          <div className="bg-background/50 rounded-lg p-2 text-center">
            <div className="text-sm font-semibold text-text">{filteredSessions.length}</div>
            <div className="text-[10px] text-textMuted">Showing</div>
          </div>
        </div>

        {/* Search + filter row */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              className="w-full bg-background/50 border border-surface rounded-lg px-3 py-1.5 text-sm text-text placeholder:text-textMuted/40 focus:outline-none focus:border-primary/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-textMuted hover:text-text text-xs"
              >✕</button>
            )}
          </div>

          {/* Drive dropdown */}
          <div ref={filterRef} className="relative shrink-0">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                selectedDrive
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-surface bg-background/50 text-textMuted hover:text-text'
              }`}
            >
              {selectedDrive ? (
                <><span>{getDriveEmoji(selectedDrive)}</span><span>{selectedDrive}</span></>
              ) : (
                <span>All drives</span>
              )}
              <span className="text-[10px]">▼</span>
            </button>

            {filterOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-surface border border-surface rounded-xl shadow-2xl py-1 z-50 max-h-64 overflow-y-auto">
                <button
                  onClick={() => { setSelectedDrive(null); setFilterOpen(false); }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                    !selectedDrive ? 'bg-accent/15 text-accent' : 'text-textMuted hover:text-text hover:bg-background/50'
                  }`}
                >
                  <span>All drives</span>
                  <span className="text-textMuted/50">{sessions.length}</span>
                </button>
                {driveCategories.map(({ drive, count }) => (
                  <button
                    key={drive}
                    onClick={() => { setSelectedDrive(drive); setFilterOpen(false); }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                      selectedDrive === drive ? 'bg-accent/15 text-accent' : 'text-textMuted hover:text-text hover:bg-background/50'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <span>{getDriveEmoji(drive)}</span>
                      <span>{drive}</span>
                    </span>
                    <span className="text-textMuted/50">{count}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Scrollable session list */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0">
        {loading && (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-background/50 rounded-lg p-3">
                <div className="h-3 bg-surface/50 rounded w-1/4 mb-2"></div>
                <div className="h-3 bg-surface/50 rounded w-3/4"></div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">{error}</div>
        )}

        {!loading && !error && filteredSessions.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center p-6 h-40">
            <span className="text-3xl mb-3 opacity-50">📓</span>
            <p className="text-textMuted text-sm">
              {searchQuery || selectedDrive ? 'No matching sessions' : `${agentName} hasn't explored yet`}
            </p>
          </div>
        )}

        {!loading && !error && filteredSessions.length > 0 && (
          <div className="space-y-1.5">
            {filteredSessions.map((session, index) => (
              <button
                key={session.filename || index}
                onClick={() => openSession(session)}
                className="w-full text-left bg-background/40 hover:bg-background/70 rounded-lg p-3 transition-colors"
              >
                <div className="flex items-center justify-between mb-1 gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm">{getDriveEmoji(session.drive)}</span>
                    <span className="text-sm font-medium text-text">
                      {formatRelativeTime(session.timestamp)}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${getDriveColor(session.drive)}`}>
                      {session.drive || 'Unknown'}
                    </span>
                  </div>
                  {session.pressure && (
                    <span className="text-xs text-textMuted/60 shrink-0">⚡ {session.pressure}</span>
                  )}
                </div>
                {session.summary && (
                  <p className="text-xs text-textMuted line-clamp-1 pl-7">{session.summary}</p>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Session Detail Modal */}
        {modalSession && (
          <SessionModal
            session={modalSession}
            body={modalBody}
            loading={modalLoading}
            onClose={() => setModalSession(null)}
          />
        )}
      </div>
    </div>
  );
}

/**
 * Modal for viewing a full session
 */
function SessionModal({ session, body, loading, onClose }) {
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
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">{getDriveEmoji(session.drive)}</span>
            <h3 className="text-base font-semibold text-text">{session.drive} Session</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${getDriveColor(session.drive)}`}>
              {session.drive}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-textMuted hover:text-text text-2xl leading-none p-1 ml-2"
          >×</button>
        </div>

        {/* Meta */}
        <div className="px-4 py-2 text-xs text-textMuted/60 border-b border-textMuted/5">
          {formatFullDate(session.timestamp)}
          {session.pressure && ` · ⚡ ${session.pressure}`}
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
