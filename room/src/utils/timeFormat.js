/**
 * Format a timestamp to relative time
 * Returns: "just now", "2m ago", "3h ago", "yesterday", "3 days ago"
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return 'unknown';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffSecs < 30) return 'just now';
  if (diffMins < 2) return '1m ago';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 2) return '1h ago';
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  // For older dates, show actual date
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

/**
 * Format a full date with time
 */
export function formatFullDate(timestamp) {
  if (!timestamp) return 'unknown';

  const date = new Date(timestamp);
  return date.toLocaleString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date range (e.g., "Since Feb 1")
 */
export function formatDateRange(startDate) {
  if (!startDate) return 'No date';

  const date = new Date(startDate);
  const month = date.toLocaleDateString('en-GB', { month: 'short' });
  const day = date.getDate();
  return `Since ${month} ${day}`;
}

export default formatRelativeTime;
