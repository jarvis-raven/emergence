/**
 * MemoryShelf — Built-in shelf for memory statistics
 * 
 * Displays memory stats using the same logic as /api/memory/stats
 */

import { join } from 'path';
import { readFileSync, existsSync } from 'fs';
import { execSync } from 'child_process';
import { getMemoryPath, getWorkspacePath } from '../../utils/configLoader.js';
import { listFiles, getFileStats } from '../../utils/fileReader.js';

/**
 * Format bytes to human readable
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Query embedding stats from OpenClaw memory sqlite
 */
function getEmbeddingStats() {
  const home = process.env.HOME || process.env.USERPROFILE || '.';
  const dbPath = join(home, '.openclaw', 'memory', 'main.sqlite');
  if (!existsSync(dbPath)) return null;
  try {
    const result = execSync(
      `sqlite3 "${dbPath}" "SELECT (SELECT COUNT(*) FROM chunks) as chunks, (SELECT COUNT(*) FROM files) as files;"`,
      { timeout: 3000, encoding: 'utf-8' }
    ).trim();
    const [chunks, files] = result.split('|').map(Number);

    // Breakdown by category
    const breakdown = [];
    try {
      const rows = execSync(
        `sqlite3 "${dbPath}" "SELECT CASE WHEN path LIKE 'memory/daily/%' THEN 'daily' WHEN path LIKE 'memory/sessions/%' THEN 'sessions' WHEN path LIKE 'memory/changelog/%' THEN 'changelog' WHEN path LIKE 'memory/correspondence/%' THEN 'correspondence' WHEN path LIKE 'memory/creative/%' THEN 'creative' WHEN path LIKE 'memory/dreams/%' THEN 'dreams' WHEN path LIKE 'memory/archive/%' THEN 'archive' ELSE 'other' END as cat, COUNT(DISTINCT path) as files, COUNT(*) as chunks FROM chunks GROUP BY cat ORDER BY chunks DESC;"`,
        { timeout: 3000, encoding: 'utf-8' }
      ).trim();
      for (const row of rows.split('\n').filter(Boolean)) {
        const [category, fileCount, chunkCount] = row.split('|');
        breakdown.push({ category, files: parseInt(fileCount), chunks: parseInt(chunkCount) });
      }
    } catch {}

    return { chunks, files, breakdown };
  } catch {
    return null;
  }
}

export const MemoryShelf = {
  manifest: {
    id: 'memory',
    name: 'Memory',
    icon: '🧠',
    description: 'Memory files, sessions, dreams, and self-history statistics',
    endpoint: '/api/shelves/memory',
    version: '1.0',
    priority: 100,
    refreshIntervalMs: 30000,
    dataSource: { type: 'custom' },
    renderer: 'memory',
  },

  async resolveData(config) {
    const memoryDir = getMemoryPath(config);
    const dailyDir = getMemoryPath(config, 'daily');
    const sessionsDir = getMemoryPath(config, 'sessions');
    const dreamsDir = getMemoryPath(config, 'dreams');
    const selfHistoryDir = getMemoryPath(config, 'self-history');
    
    // Daily memory files — check both memory/ and memory/daily/
    let dailyFiles = listFiles(dailyDir, /^\d{4}-\d{2}-\d{2}\.md$/);
    let dailyBasePath = dailyDir;
    if (dailyFiles.length === 0) {
      dailyFiles = listFiles(memoryDir, /^\d{4}-\d{2}-\d{2}\.md$/);
      dailyBasePath = memoryDir;
    }
    const dailySize = dailyFiles.reduce((sum, f) => {
      const stats = getFileStats(join(dailyBasePath, f));
      return sum + (stats?.size || 0);
    }, 0);
    
    // Session files
    const sessionFiles = listFiles(sessionsDir, /^\d{4}-\d{2}-\d{2}-\d{4}-.+\.md$/);
    const sessionSize = sessionFiles.reduce((sum, f) => {
      const stats = getFileStats(join(sessionsDir, f));
      return sum + (stats?.size || 0);
    }, 0);
    
    // Dream files
    const dreamFiles = listFiles(dreamsDir, /^\d{4}-\d{2}-\d{2}\.json$/);
    const dreamSize = dreamFiles.reduce((sum, f) => {
      const stats = getFileStats(join(dreamsDir, f));
      return sum + (stats?.size || 0);
    }, 0);
    
    // Self history files
    const selfHistoryFiles = listFiles(selfHistoryDir, /^SELF-\d{4}-\d{2}-\d{2}\.md$/);
    
    // Calculate date range
    const sortedDaily = dailyFiles.sort();
    const firstDate = sortedDaily.length > 0 ? sortedDaily[0].replace('.md', '') : null;
    const lastDate = sortedDaily.length > 0 ? sortedDaily[sortedDaily.length - 1].replace('.md', '') : null;
    
    let daysActive = 0;
    if (firstDate) {
      const first = new Date(firstDate);
      const now = new Date();
      daysActive = Math.floor((now - first) / (1000 * 60 * 60 * 24)) + 1;
    }
    
    // Recent files (last 7 days) for activity chart
    const recentFiles = sortedDaily.slice(-7).map(f => ({
      date: f.replace('.md', ''),
      size: formatBytes(getFileStats(join(dailyBasePath, f))?.size || 0),
    }));
    
    // Per-file embedding chunk counts (by full path)
    const chunkCountsByPath = {};
    const home = process.env.HOME || process.env.USERPROFILE || '.';
    const dbPath = join(home, '.openclaw', 'memory', 'main.sqlite');
    if (existsSync(dbPath)) {
      try {
        const rows = execSync(
          `sqlite3 "${dbPath}" "SELECT path, COUNT(*) FROM chunks GROUP BY path;"`,
          { timeout: 5000, encoding: 'utf-8' }
        ).trim();
        for (const row of rows.split('\n').filter(Boolean)) {
          const [path, count] = row.split('|');
          chunkCountsByPath[path] = parseInt(count, 10);
        }
      } catch {}
    }

    // Build complete file list from ALL memory subdirectories
    const allFiles = [];
    const CATEGORY_MAP = {
      daily: { icon: '📅', label: 'daily' },
      // sessions excluded — shown in Journal panel
      changelog: { icon: '📋', label: 'changelog' },
      correspondence: { icon: '✉️', label: 'correspondence' },
      creative: { icon: '🎨', label: 'creative' },
      dreams: { icon: '🌙', label: 'dream' },
      'self-history': { icon: '🪞', label: 'self-history' },
      'soul-history': { icon: '🪞', label: 'soul-history' },
      todo: { icon: '✅', label: 'todo' },
      bugs: { icon: '🐛', label: 'bug' },
      archive: { icon: '📦', label: 'archive' },
    };

    // Helper to extract date from filename or mtime
    function extractDate(filename, mtime) {
      const dateMatch = filename.match(/(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) return dateMatch[1];
      if (mtime) return new Date(mtime).toISOString().slice(0, 10);
      return null;
    }

    // Helper to get preview line
    function getPreview(filePath) {
      try {
        const content = readFileSync(filePath, 'utf-8');
        for (const line of content.split('\n')) {
          const trimmed = line.trim();
          if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
            return trimmed.slice(0, 120);
          }
        }
      } catch {}
      return '';
    }

    // Scan each known subdirectory
    for (const [subdir, meta] of Object.entries(CATEGORY_MAP)) {
      const dirPath = getMemoryPath(config, subdir);
      const files = listFiles(dirPath, /\.(md|json)$/);
      for (const f of files) {
        const filePath = join(dirPath, f);
        const stats = getFileStats(filePath);
        const date = extractDate(f, stats?.mtime);
        allFiles.push({
          date,
          filename: f,
          path: `memory/${subdir}/${f}`,
          category: meta.label,
          icon: meta.icon,
          size: formatBytes(stats?.size || 0),
          sizeBytes: stats?.size || 0,
          modified: stats?.mtime?.toISOString() || null,
          preview: getPreview(filePath),
          chunks: chunkCountsByPath[`memory/${subdir}/${f}`] || 0,
        });
      }
    }

    // Also include root-level memory files (MEMORY.md etc.)
    const rootFiles = listFiles(memoryDir, /\.md$/);
    for (const f of rootFiles) {
      if (/^\d{4}-\d{2}-\d{2}\.md$/.test(f)) continue; // Skip if daily pattern in root
      const filePath = join(memoryDir, f);
      const stats = getFileStats(filePath);
      allFiles.push({
        date: extractDate(f, stats?.mtime),
        filename: f,
        path: `memory/${f}`,
        category: 'memory',
        icon: '🧠',
        size: formatBytes(stats?.size || 0),
        sizeBytes: stats?.size || 0,
        modified: stats?.mtime?.toISOString() || null,
        preview: getPreview(filePath),
        chunks: chunkCountsByPath[`memory/${f}`] || 0,
      });
    }

    // Sort: newest first by date, then by modified
    allFiles.sort((a, b) => {
      if (a.date && b.date) return b.date.localeCompare(a.date);
      if (a.date) return -1;
      if (b.date) return 1;
      return (b.modified || '').localeCompare(a.modified || '');
    });
    
    const totalSize = dailySize + sessionSize + dreamSize;
    
    return {
      daily: {
        count: dailyFiles.length,
        size: formatBytes(dailySize),
        firstDate,
        lastDate,
        daysActive,
      },
      sessions: {
        count: sessionFiles.length,
        size: formatBytes(sessionSize),
      },
      dreams: {
        count: dreamFiles.length,
        size: formatBytes(dreamSize),
      },
      selfHistory: {
        count: selfHistoryFiles.length,
      },
      total: {
        files: dailyFiles.length + sessionFiles.length + dreamFiles.length + selfHistoryFiles.length,
        size: formatBytes(totalSize),
      },
      recent: recentFiles,
      allFiles,
      embeddings: await getEmbeddingStats(),
    };
  },
};
