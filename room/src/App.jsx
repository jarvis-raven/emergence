import { useState, useEffect } from 'react';
import { ThemeContext, defaultTheme } from './context/ThemeContext.jsx';
import useConfig from './hooks/useConfig.js';
import DrivePanel from './components/DrivePanel.jsx';
import MirrorPanel from './components/MirrorPanel.jsx';
import WorkshopPanel from './components/WorkshopPanel.jsx';
import BookshelfPanel from './components/BookshelfPanel.jsx';
import VisionBoardPanel from './components/VisionBoardPanel.jsx';
import ProjectsPanel from './components/ProjectsPanel.jsx';
import MobileNav from './components/MobileNav.jsx';

/**
 * Placeholder panel for future implementation
 */
function PlaceholderPanel({ title, icon, description, color = 'primary' }) {
  const colorClasses = {
    primary: 'border-primary/20 hover:border-primary/40',
    secondary: 'border-secondary/20 hover:border-secondary/40',
    success: 'border-success/20 hover:border-success/40',
    warning: 'border-warning/20 hover:border-warning/40',
  };

  return (
    <div 
      className={`
        bg-surface rounded-2xl border-2 p-6 h-full
        transition-colors duration-300
        ${colorClasses[color] || colorClasses.primary}
      `}
    >
      <div className="h-full flex flex-col items-center justify-center text-center">
        <span className="text-4xl mb-3 opacity-60" aria-hidden="true">{icon}</span>
        <h3 className="text-lg font-semibold text-text mb-2">{title}</h3>
        <p className="text-sm text-textMuted max-w-xs">{description}</p>
      </div>
    </div>
  );
}

/**
 * Header component with agent name
 */
function Header({ agentName, loading, error, onRetry }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Gentle fade-in animation
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <header 
      className={`
        border-b border-surface px-4 py-2 lg:px-6 lg:py-4
        transition-all duration-700
        ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}
      `}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
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

        {error && (
          <button
            onClick={onRetry}
            className="px-3 py-2 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Reconnect
          </button>
        )}
      </div>
    </header>
  );
}

/**
 * Main App component
 */
function App() {
  const { 
    config, 
    loading: configLoading, 
    error: configError, 
    refetch: refetchConfig,
    agentName,
  } = useConfig();

  const [mobileTab, setMobileTab] = useState('drives');
  const [leftPanel, setLeftPanel] = useState('mirror'); // 'mirror' or 'bookshelf'
  const [rightPanel, setRightPanel] = useState('workshop'); // 'workshop' or 'aspirations' or 'projects'

  // Update document title when agent name is available
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
          <div className="text-textMuted animate-pulse">
            Entering The Room...
          </div>
        </div>
      </div>
    );
  }

  // Error state (but allow app to continue with defaults)
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

  // Theme context value
  const themeContextValue = {
    theme: defaultTheme,
    agentName,
    loading: configLoading,
    error: configError,
  };

  return (
    <ThemeContext.Provider value={themeContextValue}>
      {/* Desktop: viewport-locked room — no page scroll, panels scroll internally */}
      <div className="hidden lg:flex lg:flex-col h-screen bg-background text-text overflow-hidden">
        {/* Compact header */}
        <Header 
          agentName={agentName} 
          loading={configLoading}
          error={configError}
          onRetry={refetchConfig}
        />

        {/* Room grid — 3 columns, Drive is full-height center */}
        <main className="flex-1 grid grid-cols-3 gap-4 p-4 min-h-0">
          {/* Left column: Mirror / Bookshelf — full height, togglable */}
          <div className="flex flex-col min-h-0">
            <div className="flex gap-1 mb-2">
              <button
                onClick={() => setLeftPanel('mirror')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  leftPanel === 'mirror'
                    ? 'bg-primary/20 text-primary'
                    : 'text-textMuted hover:text-text hover:bg-surface'
                }`}
              >
                🪞 Mirror
              </button>
              <button
                onClick={() => setLeftPanel('bookshelf')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  leftPanel === 'bookshelf'
                    ? 'bg-primary/20 text-primary'
                    : 'text-textMuted hover:text-text hover:bg-surface'
                }`}
              >
                📚 Bookshelf
              </button>
            </div>
            <div className="flex-1 overflow-y-auto rounded-2xl bg-surface border border-surface min-h-0">
              {leftPanel === 'mirror' && <MirrorPanel agentName={agentName} />}
              {leftPanel === 'bookshelf' && <BookshelfPanel agentName={agentName} />}
            </div>
          </div>

          {/* Center column: Drive panel full height */}
          <div className="overflow-y-auto rounded-2xl min-h-0">
            <DrivePanel agentName={agentName} />
          </div>

          {/* Right column: Workshop / Vision Board — full height, togglable */}
          <div className="flex flex-col min-h-0">
            <div className="flex gap-1 mb-2">
              <button
                onClick={() => setRightPanel('workshop')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  rightPanel === 'workshop'
                    ? 'bg-primary/20 text-primary'
                    : 'text-textMuted hover:text-text hover:bg-surface'
                }`}
              >
                🔧 Workshop
              </button>
              <button
                onClick={() => setRightPanel('aspirations')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  rightPanel === 'aspirations'
                    ? 'bg-primary/20 text-primary'
                    : 'text-textMuted hover:text-text hover:bg-surface'
                }`}
              >
                ✨ Aspirations
              </button>
              <button
                onClick={() => setRightPanel('projects')}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  rightPanel === 'projects'
                    ? 'bg-primary/20 text-primary'
                    : 'text-textMuted hover:text-text hover:bg-surface'
                }`}
              >
                🚀 Projects
              </button>
            </div>
            <div className="flex-1 overflow-y-auto rounded-2xl bg-surface border border-surface min-h-0">
              {rightPanel === 'workshop' && <WorkshopPanel agentName={agentName} />}
              {rightPanel === 'aspirations' && <VisionBoardPanel agentName={agentName} />}
              {rightPanel === 'projects' && <ProjectsPanel agentName={agentName} />}
            </div>
          </div>
        </main>
      </div>

      {/* Mobile: scrollable single panel with tab navigation */}
      <div className="lg:hidden min-h-screen bg-background text-text">
        <Header 
          agentName={agentName} 
          loading={configLoading}
          error={configError}
          onRetry={refetchConfig}
        />

        <main className="p-2 mb-20">
          {mobileTab === 'drives' && <DrivePanel agentName={agentName} />}
          {mobileTab === 'mirror' && <MirrorPanel agentName={agentName} />}
          {mobileTab === 'workshop' && <WorkshopPanel agentName={agentName} />}
          {mobileTab === 'bookshelf' && <BookshelfPanel agentName={agentName} />}
          {mobileTab === 'aspirations' && <VisionBoardPanel agentName={agentName} />}
          {mobileTab === 'projects' && <ProjectsPanel agentName={agentName} />}
        </main>

        <MobileNav activeTab={mobileTab} onTabChange={setMobileTab} />
      </div>
    </ThemeContext.Provider>
  );
}

export default App;
