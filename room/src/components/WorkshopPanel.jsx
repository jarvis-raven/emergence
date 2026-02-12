import { useState, useCallback } from 'react';
import useConfig from '../hooks/useConfig';
import useSessions from '../hooks/useSessions';
import { formatRelativeTime, formatFullDate } from '../utils/timeFormat';
import { renderMarkdown } from '../utils/markdown';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Drive emoji mapping
 */
const DRIVE_EMOJI = {
  CARE: '💚',
  CURIOSITY: '🔍',
  CREATIVE: '🎨',
  SOCIAL: '💬',
  MAINTENANCE: '🔧',
  REST: '😴',
  LEARNING: '📚',
  PLAY: '🎮',
  EMBODIMENT: '👁️',
  READING: '📖',
  ANXIETY: '😰',
};

/**
 * Get emoji for a drive
 */
function getDriveEmoji(drive) {
  return DRIVE_EMOJI[drive?.toUpperCase()] || '⚡';
}

/**
 * Workshop Panel — F022
 * Displays recent autonomous session experiences
 * Expandable list with full content view
 */
export default function WorkshopPanel() {
  const { agentName } = useConfig();
  const [modalSession, setModalSession] = useState(null);
  const [modalBody, setModalBody] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [selectedDrive, setSelectedDrive] = useState(null);
  
  const { sessions, loading, error, refetch, count } = useSessions({
    limit: 20,
    drive: selectedDrive,
  });

  const handleRefresh = () => {
    refetch();
  };

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

  // Extract unique drives for filter
  const availableDrives = [...new Set(sessions.map(s => s.drive))].filter(Boolean);

  return (
    <div className="bg-surface rounded-xl p-4 h-full flex flex-col">
      {/* Subheader */}
      {!loading && (
        <div className="flex items-center justify-end mb-3">
          <span className="text-xs text-textMuted/60">{count} sessions</span>
        </div>
      )}

      {/* Drive filter */}
      {availableDrives.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          <button
            onClick={() => setSelectedDrive(null)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              selectedDrive === null
                ? 'bg-primary/20 text-primary'
                : 'bg-background/50 text-textMuted hover:text-text'
            }`}
          >
            All
          </button>
          {availableDrives.map((drive) => (
            <button
              key={drive}
              onClick={() => setSelectedDrive(drive === selectedDrive ? null : drive)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                selectedDrive === drive
                  ? 'bg-primary/20 text-primary'
                  : 'bg-background/50 text-textMuted hover:text-text'
              }`}
            >
              {getDriveEmoji(drive)} {drive}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
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
          <div className="text-danger/80 text-sm p-3 bg-danger/10 rounded-lg">
            {error}
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center p-6 h-40">
            <span className="text-3xl mb-3 opacity-50">🔧</span>
            <p className="text-textMuted text-sm">
              {agentName} hasn't explored autonomously yet
            </p>
            <p className="text-textMuted/60 text-xs mt-2">
              Sessions happen during scheduled exploration time
            </p>
          </div>
        )}

        {!loading && !error && sessions.length > 0 && (
          <div className="space-y-2">
            {sessions.map((session, index) => (
              <div
                key={session.filename || index}
                onClick={() => openSession(session)}
                className="bg-background/50 rounded-lg p-3 cursor-pointer hover:bg-background/70 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <span className="text-base flex-shrink-0">{getDriveEmoji(session.drive)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-medium text-primary">
                        {session.drive || 'Unknown'}
                      </span>
                      <span className="text-xs text-textMuted/60">
                        {formatRelativeTime(session.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm text-textMuted line-clamp-2">
                      {session.summary || 'No summary available'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

      {/* Session Detail Modal */}
      {modalSession && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setModalSession(null)}
        >
          <div
            className="bg-surface rounded-2xl border border-textMuted/20 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center gap-3 p-4 border-b border-textMuted/10">
              <span className="text-lg">{getDriveEmoji(modalSession.drive)}</span>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-text">
                  {modalSession.drive} Session
                </h3>
                <p className="text-xs text-textMuted/60">
                  {formatFullDate(modalSession.timestamp)}
                  {modalSession.pressure && ` · ⚡ ${modalSession.pressure}`}
                </p>
              </div>
              <button
                onClick={() => setModalSession(null)}
                className="text-textMuted hover:text-text text-2xl leading-none p-1"
              >
                ×
              </button>
            </div>

            {/* Body */}
            <div className="p-4 overflow-y-auto flex-1 min-h-0">
              {modalLoading ? (
                <div className="py-8 text-center text-textMuted/50 animate-pulse">Loading...</div>
              ) : modalBody ? (
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
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(modalBody) }}
                />
              ) : null}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
