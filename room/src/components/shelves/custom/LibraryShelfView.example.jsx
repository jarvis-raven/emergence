/**
 * LibraryShelfView — Display reading progress and book collection
 */

import React from 'react';

export function LibraryShelfView({ data }) {
  if (!data) {
    return (
      <div className="text-center py-8 text-textMuted">
        <p className="text-sm">No library data available</p>
      </div>
    );
  }

  const { currentlyReading = [], toRead = [] } = data;

  return (
    <div className="space-y-6">
      {/* Currently Reading */}
      {currentlyReading.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <span>📖</span>
            <span>Currently Reading</span>
          </h3>
          <div className="space-y-3">
            {currentlyReading.map((book, idx) => (
              <BookCard key={idx} book={book} showProgress />
            ))}
          </div>
        </div>
      )}

      {/* To Read */}
      {toRead.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <span>📚</span>
            <span>Up Next ({toRead.length})</span>
          </h3>
          <div className="space-y-2">
            {toRead.slice(0, 5).map((book, idx) => (
              <BookCard key={idx} book={book} compact />
            ))}
            {toRead.length > 5 && (
              <p className="text-xs text-textMuted pl-3">+{toRead.length - 5} more in queue</p>
            )}
          </div>
        </div>
      )}

      {currentlyReading.length === 0 && toRead.length === 0 && (
        <div className="text-center py-8 text-textMuted">
          <p className="text-sm">No books in library yet</p>
        </div>
      )}
    </div>
  );
}

function BookCard({ book, showProgress = false, compact = false }) {
  const {
    title,
    author,
    progress = 0,
    wordsRead = 0,
    totalWords = 0,
    sessionsCompleted = 0,
    lastReadAt,
    interest = 3,
  } = book;

  if (compact) {
    return (
      <div className="flex items-center gap-3 text-sm">
        <div className="flex-shrink-0">
          <InterestIndicator level={interest} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-text truncate font-medium">{title}</p>
          {author && author !== 'Unknown' && (
            <p className="text-textMuted text-xs truncate">{author}</p>
          )}
        </div>
        <div className="text-xs text-textMuted">{formatWords(totalWords)}</div>
      </div>
    );
  }

  return (
    <div className="bg-backgroundAlt rounded-lg p-3 border border-surface">
      <div className="flex items-start gap-3 mb-2">
        <InterestIndicator level={interest} />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-text leading-tight mb-1">{title}</h4>
          {author && author !== 'Unknown' && <p className="text-xs text-textMuted">{author}</p>}
        </div>
      </div>

      {showProgress && (
        <div className="space-y-2">
          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-xs text-textMuted mb-1">
              <span>{Math.round(progress * 100)}% complete</span>
              <span>
                {formatWords(wordsRead)} / {formatWords(totalWords)}
              </span>
            </div>
            <div className="h-1.5 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-textMuted">
            {sessionsCompleted > 0 && <span>{sessionsCompleted} sessions</span>}
            {lastReadAt && <span>Last read: {formatDate(lastReadAt)}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function InterestIndicator({ level }) {
  const colors = {
    1: 'bg-gray-400',
    2: 'bg-gray-300',
    3: 'bg-blue-400',
    4: 'bg-purple-400',
    5: 'bg-primary',
  };

  return (
    <div
      className={`w-2 h-2 rounded-full ${colors[level] || 'bg-gray-400'}`}
      title={`Interest level: ${level}/5`}
    />
  );
}

function formatWords(words) {
  if (!words) return '0 words';
  if (words < 1000) return `${words} words`;
  return `${Math.round(words / 1000)}k words`;
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
