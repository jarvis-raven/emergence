import { createContext, useContext } from 'react';

// Drive color gradients — every known drive gets a color
// Unknown/discovered drives get auto-assigned from the fallback palette
export const driveColors = {
  // Core drives
  CARE: { from: '#22d3ee', to: '#2dd4bf' },
  MAINTENANCE: { from: '#94a3b8', to: '#64748b' },
  REST: { from: '#818cf8', to: '#c084fc' },
  // Common discovered drives
  CURIOSITY: { from: '#fbbf24', to: '#f97316' },
  SOCIAL: { from: '#f472b6', to: '#ef4444' },
  CREATIVE: { from: '#a78bfa', to: '#8b5cf6' },
  PLAY: { from: '#34d399', to: '#10b981' },
  LEARNING: { from: '#60a5fa', to: '#3b82f6' },
  READING: { from: '#a78bfa', to: '#6366f1' },
  EMBODIMENT: { from: '#fb923c', to: '#ea580c' },
  ANXIETY: { from: '#f87171', to: '#dc2626' },
};

// Fallback palette for agent-discovered drives not in the map
const fallbackPalette = [
  { from: '#f9a8d4', to: '#ec4899' },
  { from: '#86efac', to: '#22c55e' },
  { from: '#fde68a', to: '#eab308' },
  { from: '#7dd3fc', to: '#0ea5e9' },
  { from: '#c4b5fd', to: '#7c3aed' },
  { from: '#fca5a1', to: '#e11d48' },
];

/**
 * Get color for a drive name. Known drives get their assigned color,
 * unknown drives get a consistent color from the fallback palette.
 */
export function getDriveColor(name) {
  if (driveColors[name]) return driveColors[name];
  // Hash the name to pick a consistent fallback color
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
  return fallbackPalette[Math.abs(hash) % fallbackPalette.length];
}

// Default dark theme colors from UX flows
export const defaultTheme = {
  colors: {
    background: '#0f172a',
    surface: '#1e293b',
    text: '#f8fafc',
    textMuted: '#94a3b8',
    primary: '#3b82f6',
    secondary: '#64748b',
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
  },
  driveColors,
};

// Create the theme context
export const ThemeContext = createContext({
  theme: defaultTheme,
  agentName: 'My Agent',
  loading: true,
  error: null,
});

// Hook to use theme context
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}

export default ThemeContext;
