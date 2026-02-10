/**
 * Identity Routes — GET /api/identity/:file
 * 
 * Returns identity file content (soul, self, aspirations, interests, etc.)
 * Source files: SOUL.md, SELF.md, ASPIRATIONS.md, INTERESTS.md
 */

import { Router } from 'express';
import { loadConfig, getIdentityPath } from '../utils/configLoader.js';
import { readTextFile, getFileStats } from '../utils/fileReader.js';

const router = Router();

// Map of route params to filenames
const IDENTITY_FILES = {
  soul: 'SOUL.md',
  self: 'SELF.md',
  aspirations: 'ASPIRATIONS.md',
  interests: 'INTERESTS.md',
  user: 'USER.md',
  agents: 'AGENTS.md',
  thread: 'THREAD.md',
};

/**
 * GET /api/identity/:file
 * Returns identity file content as markdown string
 * :file can be: soul, self, aspirations, interests, user, agents, thread
 */
router.get('/:file', (req, res) => {
  try {
    const { file } = req.params;
    const normalizedFile = file.toLowerCase();
    
    // Check if this is a known identity file
    const filename = IDENTITY_FILES[normalizedFile];
    
    if (!filename) {
      return res.status(400).json({
        error: `Unknown identity file: ${file}`,
        available: Object.keys(IDENTITY_FILES),
      });
    }
    
    const config = loadConfig();
    const path = getIdentityPath(config, filename);
    
    const content = readTextFile(path);
    const stats = getFileStats(path);
    
    if (!content) {
      return res.json({
        file: normalizedFile,
        filename,
        content: '',
        exists: false,
        placeholder: `${filename} has not been created yet.`,
      });
    }
    
    // Strip H1 title if present (redundant in dashboard)
    const cleanContent = content.replace(/^# .+\n+/, '');
    
    res.json({
      file: normalizedFile,
      filename,
      content: cleanContent.trim(),
      exists: true,
      stats: {
        size: stats?.size || 0,
        modified: stats?.mtime?.toISOString() || null,
      },
    });
  } catch (err) {
    console.error('Identity route error:', err);
    res.status(500).json({ error: 'Failed to load identity file' });
  }
});

/**
 * GET /api/identity
 * Returns list of available identity files with metadata
 */
router.get('/', (req, res) => {
  try {
    const config = loadConfig();
    const files = [];
    
    for (const [key, filename] of Object.entries(IDENTITY_FILES)) {
      const path = getIdentityPath(config, filename);
      const stats = getFileStats(path);
      
      files.push({
        key,
        filename,
        exists: !!stats,
        size: stats?.size || 0,
        modified: stats?.mtime?.toISOString() || null,
      });
    }
    
    res.json({ files });
  } catch (err) {
    console.error('Identity list route error:', err);
    res.status(500).json({ error: 'Failed to list identity files' });
  }
});

export default router;
