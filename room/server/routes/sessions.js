/**
 * Sessions Routes — GET /api/sessions, GET /api/sessions/:filename
 * 
 * Returns recent sessions with parsed YAML frontmatter
 * Query params: limit (default 10), drive (optional filter)
 */

import { Router } from 'express';
import { join } from 'path';
import { loadConfig, getMemoryPath } from '../utils/configLoader.js';
import { listFiles, readTextFile, getFileStats } from '../utils/fileReader.js';
import { parseFrontmatter, extractSummary } from '../utils/frontmatter.js';

const router = Router();

/**
 * GET /api/sessions
 * Returns recent sessions with parsed YAML frontmatter
 * Query: ?limit=10&drive=CURIOSITY
 */
router.get('/', (req, res) => {
  try {
    const limit = parseInt(req.query.limit, 10) || 10;
    const driveFilter = req.query.drive?.toUpperCase();
    
    const config = loadConfig();
    const sessionsDir = getMemoryPath(config, config.paths?.sessions || 'sessions');
    
    // List session files
    const filePattern = /^\d{4}-\d{2}-\d{2}-\d{4}-.+\.md$/;
    const allFiles = listFiles(sessionsDir, filePattern).map(f => ({ filename: f, dir: sessionsDir }));
    
    if (allFiles.length === 0) {
      return res.json({ sessions: [], count: 0 });
    }
    
    // Sort by filename (date desc) and parse
    let sessions = allFiles
      .sort((a, b) => b.filename.localeCompare(a.filename))
      .map(({ filename, dir }) => {
        const path = join(dir, filename);
        const content = readTextFile(path);
        
        if (!content) {
          return null;
        }
        
        const { frontmatter, body } = parseFrontmatter(content);
        const stats = getFileStats(path);
        
        // Extract date from filename if not in frontmatter
        const dateMatch = filename.match(/^(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})-/);
        let timestamp = frontmatter.timestamp;
        if (!timestamp && dateMatch) {
          timestamp = `${dateMatch[1]}T${dateMatch[2]}:${dateMatch[3]}:00Z`;
        }
        
        // Extract drive from filename if not in frontmatter
        // Filename format: YYYY-MM-DD-HHMM-DRIVE.md
        let drive = frontmatter.drive;
        if (!drive) {
          const driveMatch = filename.match(/^\d{4}-\d{2}-\d{2}-\d{4}-([A-Za-z_-]+)\.md$/);
          drive = driveMatch ? driveMatch[1].toUpperCase() : 'UNKNOWN';
        }
        
        return {
          filename,
          drive,
          timestamp,
          pressure: frontmatter.pressure || null,
          trigger: frontmatter.trigger || null,
          model: frontmatter.model || null,
          duration_minutes: frontmatter.duration_minutes || null,
          satisfaction: frontmatter.satisfaction || null,
          summary: extractSummary(body),
          size: stats?.size || 0,
          modified: stats?.mtime?.toISOString() || null,
        };
      })
      .filter(Boolean);
    
    // Filter by drive if specified
    if (driveFilter) {
      sessions = sessions.filter(s => s.drive?.toUpperCase() === driveFilter);
    }
    
    // Apply limit
    sessions = sessions.slice(0, limit);
    
    res.json({ sessions, count: sessions.length });
  } catch (err) {
    console.error('Sessions route error:', err);
    res.status(500).json({ error: 'Failed to load sessions' });
  }
});

/**
 * GET /api/sessions/:filename
 * Returns single session with full content
 */
router.get('/:filename', (req, res) => {
  try {
    const { filename } = req.params;
    
    // Validate filename (prevent directory traversal)
    if (!filename.match(/^\d{4}-\d{2}-\d{2}-\d{4}-[\w-]+\.md$/)) {
      return res.status(400).json({ error: 'Invalid filename' });
    }
    
    const config = loadConfig();
    const sessionsDir = getMemoryPath(config, config.paths?.sessions || 'sessions');
    const path = join(sessionsDir, filename);
    
    const content = readTextFile(path);
    
    if (!content) {
      return res.status(404).json({ error: 'Session not found' });
    }
    
    const { frontmatter, body } = parseFrontmatter(content);
    const stats = getFileStats(path);
    
    // Extract date from filename if not in frontmatter
    const dateMatch = filename.match(/^(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})-/);
    let timestamp = frontmatter.timestamp;
    if (!timestamp && dateMatch) {
      timestamp = `${dateMatch[1]}T${dateMatch[2]}:${dateMatch[3]}:00Z`;
    }
    
    res.json({
      filename,
      frontmatter: {
        ...frontmatter,
        timestamp,
      },
      body,
      stats: {
        size: stats?.size || 0,
        created: stats?.birthtime?.toISOString() || null,
        modified: stats?.mtime?.toISOString() || null,
      },
    });
  } catch (err) {
    console.error('Session detail route error:', err);
    res.status(500).json({ error: 'Failed to load session' });
  }
});

export default router;
