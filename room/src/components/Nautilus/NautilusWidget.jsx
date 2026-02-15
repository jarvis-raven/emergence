import { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

/**
 * Chamber Distribution Visualization
 * Shows Atrium/Corridor/Unknown distribution
 */
function ChamberDistribution({ chambers }) {
  const { atrium, corridor, unknown, total, coverage_pct } = chambers;
  
  const items = [
    { label: 'Atrium', value: atrium, color: 'bg-blue-500', desc: 'Recent context' },
    { label: 'Corridor', value: corridor, color: 'bg-purple-500', desc: 'Transitional' },
    { label: 'Unknown', value: unknown, color: 'bg-gray-500', desc: 'Uncategorized' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-text">Chamber Distribution</h3>
        <span className="text-xs text-textMuted">
          {Math.round(coverage_pct)}% categorized
        </span>
      </div>
      
      <div className="space-y-2">
        {items.map((item) => {
          const percentage = total > 0 ? (item.value / total) * 100 : 0;
          
          return (
            <div key={item.label} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-textMuted">{item.label}</span>
                <span className="text-text font-medium">{item.value}</span>
              </div>
              <div className="h-2 bg-background rounded-full overflow-hidden">
                <div 
                  className={`h-full ${item.color} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <p className="text-xs text-textMuted/70">{item.desc}</p>
            </div>
          );
        })}
      </div>
      
      <div className="pt-2 border-t border-background/50">
        <div className="text-xs text-textMuted">
          Total chunks: <span className="text-text font-medium">{total}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Coverage Stats Card
 * Shows a single coverage metric
 */
function CoverageCard({ icon, label, value, total, color = 'text-blue-500' }) {
  const percentage = total > 0 ? (value / total) * 100 : 0;
  
  return (
    <div className="bg-background rounded-lg p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <h4 className="text-sm font-medium text-text">{label}</h4>
      </div>
      
      <div className="space-y-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-2xl font-bold ${color}`}>
            {Math.round(percentage)}%
          </span>
          <span className="text-xs text-textMuted">
            {value}/{total}
          </span>
        </div>
        
        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
          <div 
            className={`h-full ${color.replace('text-', 'bg-')} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Gravity Stats
 * Shows total chunks and access patterns
 */
function GravityStats({ gravity }) {
  const { total_chunks, total_accesses, superseded, db_size } = gravity;
  
  // Format DB size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };
  
  return (
    <div className="bg-background rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🌍</span>
        <h4 className="text-sm font-medium text-text">Gravity</h4>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-textMuted">Total Chunks</div>
          <div className="text-lg font-bold text-text">{total_chunks}</div>
        </div>
        <div>
          <div className="text-xs text-textMuted">Accesses</div>
          <div className="text-lg font-bold text-text">{total_accesses}</div>
        </div>
        <div>
          <div className="text-xs text-textMuted">Superseded</div>
          <div className="text-lg font-bold text-text">{superseded}</div>
        </div>
        <div>
          <div className="text-xs text-textMuted">DB Size</div>
          <div className="text-lg font-bold text-text">{formatSize(db_size)}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Mirror Coverage
 * Shows event reflection stats
 */
function MirrorCoverage({ mirrors }) {
  const { total_events, fully_mirrored, coverage } = mirrors;
  
  const layers = [
    { label: 'Raw', value: coverage.raw, color: 'bg-green-500' },
    { label: 'Summary', value: coverage.summary, color: 'bg-yellow-500' },
    { label: 'Lesson', value: coverage.lesson, color: 'bg-orange-500' },
  ];
  
  return (
    <div className="bg-background rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🪞</span>
        <h4 className="text-sm font-medium text-text">Mirror Coverage</h4>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-textMuted">Total Events</span>
          <span className="text-text font-medium">{total_events}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-textMuted">Fully Mirrored</span>
          <span className="text-text font-medium">{fully_mirrored}</span>
        </div>
      </div>
      
      <div className="space-y-2 pt-2 border-t border-surface">
        {layers.map((layer) => (
          <div key={layer.label} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-textMuted">{layer.label}</span>
              <span className="text-text font-medium">{layer.value}</span>
            </div>
            <div className="h-1.5 bg-surface rounded-full overflow-hidden">
              <div 
                className={`h-full ${layer.color} transition-all duration-500`}
                style={{ width: total_events > 0 ? `${(layer.value / total_events) * 100}%` : '0%' }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Loading skeleton for Nautilus widget
 */
function NautilusSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 bg-background/50 rounded w-1/3"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-background/50 rounded-lg"></div>
        ))}
      </div>
    </div>
  );
}

/**
 * Error state for Nautilus widget
 */
function NautilusError({ error, onRetry }) {
  return (
    <div className="text-center py-12">
      <div className="text-4xl mb-4 opacity-60">🐚</div>
      <h3 className="text-lg text-text font-medium mb-2">
        Cannot load Nautilus status
      </h3>
      <p className="text-sm text-textMuted mb-4">{error}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

/**
 * NautilusWidget — Memory system visualization
 * 
 * Displays:
 * - Chamber distribution (Atrium/Corridor/Unknown)
 * - Door coverage (file tagging)
 * - Mirror coverage (event reflection)
 * - Gravity stats (total chunks, accesses, DB size)
 */
export default function NautilusWidget() {
  const { data, loading, error, refetch } = useApi('/api/nautilus/status', {
    refreshInterval: 30000, // Refresh every 30 seconds
  });

  if (loading && !data) {
    return <NautilusSkeleton />;
  }

  if (error && !data) {
    return <NautilusError error={error} onRetry={refetch} />;
  }

  const { gravity, chambers, doors, mirrors, summary_files } = data || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">🐚</span>
          <h2 className="text-xl font-semibold text-text">Nautilus</h2>
        </div>
        <p className="text-sm text-textMuted">
          Memory system status and coverage metrics
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column */}
        <div className="space-y-4">
          <div className="bg-surface rounded-xl p-4 border border-background">
            <ChamberDistribution chambers={chambers || {}} />
          </div>
          
          <GravityStats gravity={gravity || {}} />
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          <CoverageCard
            icon="🚪"
            label="Door Coverage"
            value={doors?.tagged_files || 0}
            total={doors?.total_files || 0}
            color="text-green-500"
          />
          
          <MirrorCoverage mirrors={mirrors || {}} />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="bg-surface rounded-xl p-4 border border-background">
        <h3 className="text-sm font-medium text-text mb-3">Summary Files</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-textMuted">Corridors</div>
            <div className="text-lg font-bold text-text">{summary_files?.corridors || 0}</div>
          </div>
          <div>
            <div className="text-xs text-textMuted">Vaults</div>
            <div className="text-lg font-bold text-text">{summary_files?.vaults || 0}</div>
          </div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="text-xs text-textMuted text-center">
        Last updated: {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : 'Never'}
      </div>
    </div>
  );
}
