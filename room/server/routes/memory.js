/**
 * Memory Routes — GET /api/memory/stats
 * 
 * Returns file counts, total size, date range for memory directories
 */

import { Router } from 'express';
import { join } from 'path';
import { loadConfig, getMemoryPath, getWorkspacePath } from '../utils/configLoader.js';
import { 
  listFiles, 
  countFiles, 
  getDirectorySize, 
  getFileStats,
  readTextFile 
} from '../utils/fileReader.js';

const router = Router();

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
 * GET /api/memory/stats
 * Returns file counts, total size, date range for memory directories
 */
router.get('/stats', (req, res) => {
  try {
    const config = loadConfig();
    
    // Memory directories to scan
    const memoryDir = getMemoryPath(config);
    const sessionsDir = getMemoryPath(config, 'sessions');
    const dreamsDir = getMemoryPath(config, 'dreams');
    const selfHistoryDir = getMemoryPath(config, 'self-history');
    const workspace = getWorkspacePath(config);
    
    // Daily memory files (YYYY-MM-DD.md)
    const dailyFiles = listFiles(memoryDir, /^\d{4}-\d{2}-\d{2}\.md$/);
    const dailySize = dailyFiles.reduce((sum, f) => {
      const stats = getFileStats(join(memoryDir, f));
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
    
    // Calculate date range from daily files
    const sortedDaily = dailyFiles.sort();
    const firstDate = sortedDaily.length > 0 ? sortedDaily[0].replace('.md', '') : null;
    const lastDate = sortedDaily.length > 0 ? sortedDaily[sortedDaily.length - 1].replace('.md', '') : null;
    
    // Calculate days since first memory
    let daysActive = 0;
    if (firstDate) {
      const first = new Date(firstDate);
      const now = new Date();
      daysActive = Math.floor((now - first) / (1000 * 60 * 60 * 24)) + 1;
    }
    
    // Recent files (last 7 days)
    const recentFiles = sortedDaily.slice(-7).map(f => ({
      date: f.replace('.md', ''),
      size: formatBytes(getFileStats(join(memoryDir, f))?.size || 0),
    }));
    
    // Total memory size
    const totalSize = dailySize + sessionSize + dreamSize;
    
    res.json({
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
    });
  } catch (err) {
    console.error('Memory stats route error:', err);
    res.status(500).json({ error: 'Failed to load memory stats' });
  }
});

/**
 * GET /api/memory/daily/:date
 * Returns the full markdown content of a daily memory file
 */
router.get('/daily/:date', (req, res) => {
  try {
    const { date } = req.params;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return res.status(400).json({ error: 'Invalid date format' });
    }

    const config = loadConfig();
    const memoryDir = getMemoryPath(config);
    const dailyDir = getMemoryPath(config, 'daily');
    const filename = `${date}.md`;

    let content = readTextFile(join(dailyDir, filename));
    if (!content) content = readTextFile(join(memoryDir, filename));
    if (!content) return res.status(404).json({ error: 'Daily file not found' });

    res.json({ date, body: content });
  } catch (err) {
    console.error('Memory daily route error:', err);
    res.status(500).json({ error: 'Failed to load daily file' });
  }
});

/**
 * GET /api/memory/file?path=memory/sessions/foo.md
 * Returns the full content of any memory file by relative path
 */
router.get('/file', (req, res) => {
  try {
    const relPath = req.query.path;
    // Security: prevent path traversal
    if (!relPath || relPath.includes('..') || !relPath.match(/^[a-zA-Z0-9_\-\/\.]+$/)) {
      return res.status(400).json({ error: 'Invalid path' });
    }

    const config = loadConfig();
    const workspace = getWorkspacePath(config);
    const fullPath = join(workspace, relPath);

    // Must be within workspace
    if (!fullPath.startsWith(workspace)) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const content = readTextFile(fullPath);
    if (!content) return res.status(404).json({ error: 'File not found' });

    res.json({ path: relPath, body: content });
  } catch (err) {
    console.error('Memory file route error:', err);
    res.status(500).json({ error: 'Failed to load file' });
  }
});

export default router;
