import { useState, useEffect, useRef } from 'react';
import { ThemeContext, defaultTheme } from './context/ThemeContext.jsx';
import useConfig from './hooks/useConfig.js';
import DriveSidebar from './components/DriveSidebar.jsx';
import ShelfPanel from './components/ShelfPanel.jsx';
import DaemonHealthDrawer from './components/DaemonHealthDrawer.jsx';

// Panel imports
import MirrorPanel from './components/MirrorPanel.jsx';
import WorkshopPanel from './components/WorkshopPanel.jsx';
import DrivePanel from './components/DrivePanel.jsx';
import VisionBoardPanel from './components/VisionBoardPanel.jsx';
import ProjectsPanel from './components/ProjectsPanel.jsx';

/**
 * Navigation items for the menu
 */
/**
 * Core nav items. Custom shelves (library etc.) append dynamically.
 */
const NAV_ITEMS = [
  { id: 'home',        icon: '🏠', label: 'Home' },
  { id: 'mirror',      icon: '🪞', label: 'Mirror' },
  { id: 'memory',      icon: '🧠', label: 'Memory' },
  { id: 'journal',     icon: '📓', label: 'Journal' },
  { id: 'aspirations', icon: '✨', label: 'Aspirations' },
  { id: 'projects',    icon: '🚀', label: 'Projects' },
];

/**
 * Header component with agent name and hamburger menu
 */
function Header({ agentName, loading, error, onRetry, activePanel, onPanelChange, onHealthClick, showMenu = true }) {
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  return (
    <header 
      className={`
        border-b border-surface px-4 py-2 lg:px-6 lg:py-3
        transition-all duration-700 relative z-50
        ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}
      `}
    >
      <div className="max-w-[1600px] mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text">
            {agentName}&apos;s Room
          </h1>
          <span className="text-xs text-textMuted hidden sm:inline">
            {error 
              ? 'Connection interrupted' 
              : loading 
                ? 'Entering...' 
                : 'A space for reflection, creation, and rest'
            }
          </span>
        </div>

        <div className="flex items-center gap-2">
          {error && (
            <button
              onClick={onRetry}
              className="px-3 py-2 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              Reconnect
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={() => window.location.reload()}
            className="p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
            title="Refresh"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

          {/* Daemon Health — Desktop only */}
          <button
            onClick={onHealthClick}
            className="hidden lg:flex p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
            title="Daemon Health"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          {/* Hamburger menu — mobile only */}
          {showMenu && <div ref={menuRef} className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 text-textMuted hover:text-text transition-colors rounded-lg hover:bg-surface/50"
              title="Menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>

            {/* Dropdown */}
            {menuOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-surface border border-surface rounded-xl shadow-2xl py-1 z-50">
                {NAV_ITEMS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { onPanelChange(item.id); setMenuOpen(false); }}
                    className={`
                      w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors
                      ${activePanel === item.id
                        ? 'bg-accent/15 text-accent font-medium'
                        : 'text-textMuted hover:text-text hover:bg-background/50'
                      }
                    `}
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
                
                {/* Daemon Health (mobile only) */}
                <div className="border-t border-surface/50 my-1 lg:hidden" />
                <button
                  onClick={() => { onHealthClick(); setMenuOpen(false); }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-textMuted hover:text-text hover:bg-background/50 transition-colors lg:hidden"
                >
                  <span>🏥</span>
                  <span>Daemon Health</span>
                </button>
              </div>
            )}
          </div>}
        </div>
      </div>
    </header>
  );
}

/**
 * Main App — Room v2 Layout
 * 
 * Desktop: Two-column layout
 *   [Drives Sidebar (narrow)] [Tabbed Shelf Panel (wide)]
 * 
 * Mobile: Single panel with bottom tab navigation
 */
/**
 * Panel component mapping
 */
const PANEL_MAP = {
  mirror: MirrorPanel,
  journal: WorkshopPanel,
  aspirations: VisionBoardPanel,
  projects: ProjectsPanel,
};

function App() {
  const { 
    config, 
    loading: configLoading, 
    error: configError, 
    refetch: refetchConfig,
    agentName,
  } = useConfig();

  const [activePanel, setActivePanel] = useState('home');
  const [healthDrawerOpen, setHealthDrawerOpen] = useState(false);

  useEffect(() => {
    if (agentName) {
      document.title = `${agentName}'s Room`;
    }
  }, [agentName]);

  // Loading state
  if (configLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-4xl animate-pulse" aria-hidden="true">🌙</div>
          <div className="text-textMuted animate-pulse">Entering The Room...</div>
        </div>
      </div>
    );
  }

  // Error state
  if (configError && !config) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4" aria-hidden="true">🚪</div>
          <h2 className="text-xl text-text font-semibold mb-2">
            Cannot reach the agent&apos;s system
          </h2>
          <p className="text-textMuted mb-6">{configError}</p>
          <button 
            onClick={refetchConfig}
            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors min-h-[44px]"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const themeContextValue = {
    theme: defaultTheme,
    agentName,
    loading: configLoading,
    error: configError,
  };

  // Mobile: resolve active panel
  const isShelfPanel = ['memory', 'library'].includes(activePanel);
  const BuiltinPanel = PANEL_MAP[activePanel];

  return (
    <ThemeContext.Provider value={themeContextValue}>
      {/* ═══════════════════════════════════════════
          DESKTOP: Original two-column layout
          Left: Drives sidebar (fixed width)
          Right: Tabbed shelf panel (fills remaining)
          No hamburger menu — tabs in ShelfPanel
          ═══════════════════════════════════════════ */}
      <div className="hidden lg:flex lg:flex-col h-screen bg-background text-text overflow-hidden">
        <Header 
          agentName={agentName} 
          loading={configLoading}
          error={configError}
          onRetry={refetchConfig}
          activePanel={activePanel}
          onPanelChange={setActivePanel}
          onHealthClick={() => setHealthDrawerOpen(true)}
          showMenu={false}
        />

        <main className="flex-1 flex gap-4 p-4 min-h-0 max-w-[1600px] mx-auto w-full">
          <div className="w-72 shrink-0 bg-surface rounded-2xl border border-surface overflow-hidden">
            <DriveSidebar agentName={agentName} />
          </div>
          <div className="flex-1 min-w-0">
            <ShelfPanel agentName={agentName} />
          </div>
        </main>
      </div>

      {/* ═══════════════════════════════════════════
          MOBILE: Hamburger menu navigation
          ═══════════════════════════════════════════ */}
      <div className="lg:hidden flex flex-col h-screen bg-background text-text overflow-hidden">
        <Header 
          agentName={agentName} 
          loading={configLoading}
          error={configError}
          onRetry={refetchConfig}
          activePanel={activePanel}
          onPanelChange={setActivePanel}
          onHealthClick={() => setHealthDrawerOpen(true)}
          showMenu={true}
        />

        <main className="flex-1 overflow-y-auto p-2">
          {activePanel === 'home' && <DrivePanel agentName={agentName} />}
          {isShelfPanel && <ShelfPanel agentName={agentName} forceTab={activePanel} />}
          {BuiltinPanel && <BuiltinPanel agentName={agentName} />}
        </main>
      </div>

      {/* Daemon Health Drawer */}
      <DaemonHealthDrawer 
        isOpen={healthDrawerOpen}
        onClose={() => setHealthDrawerOpen(false)}
      />
    </ThemeContext.Provider>
  );
}

export default App;
