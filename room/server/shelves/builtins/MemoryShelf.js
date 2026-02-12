/**
 * MemoryShelf — Built-in shelf for memory statistics
 * 
 * Displays memory stats using the same logic as /api/memory/stats
 */

import { join } from 'path';
import { readFileSync } from 'fs';
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
    
    // Full daily list (newest first) with preview
    const dailyList = [...sortedDaily].reverse().map(f => {
      const filePath = join(dailyBasePath, f);
      const stats = getFileStats(filePath);
      let preview = '';
      try {
        const content = readFileSync(filePath, 'utf-8');
        // Get first non-heading, non-empty line as preview
        const lines = content.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
            preview = trimmed.slice(0, 120);
            break;
          }
        }
      } catch {}
      return {
        date: f.replace('.md', ''),
        filename: f,
        size: formatBytes(stats?.size || 0),
        sizeBytes: stats?.size || 0,
        modified: stats?.mtime?.toISOString() || null,
        preview,
      };
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
      dailyList,
      _dailyBasePath: dailyBasePath,
    };
  },
};
