/**
 * Dreams Routes — GET /api/dreams
 * 
 * Returns recent dreams from memory/dreams/*.json
 * Query params: limit (default 7)
 */

import { Router } from 'express';
import { join } from 'path';
import { existsSync, readFileSync } from 'fs';
import { loadConfig, getMemoryPath } from '../utils/configLoader.js';
import { listFiles, readJsonFile } from '../utils/fileReader.js';

const router = Router();

/**
 * GET /api/dreams
 * Returns recent dreams
 * Query: ?limit=7
 */
router.get('/', (req, res) => {
  try {
    const limit = parseInt(req.query.limit, 10) || 7;
    
    const config = loadConfig();
    const dreamsDir = getMemoryPath(config, 'dreams');
    
    // List dream files (sorted by date desc)
    const files = listFiles(dreamsDir, /^\d{4}-\d{2}-\d{2}\.json$/)
      .sort()
      .reverse();
    
    if (files.length === 0) {
      return res.json({
        dreams: [],
        count: 0,
        days_with_dreams: 0,
        message: "No dreams yet. Dreams generate automatically during rest periods.",
      });
    }
    
    // Read recent dream files and collect fragments
    let allDreams = [];
    
    for (const file of files.slice(0, 14)) { // Read up to 14 days
      const data = readJsonFile(join(dreamsDir, file));
      
      if (!data) continue;
      
      const date = file.replace('.json', '');
      
      // Handle different dream file formats
      const fragments = data.fragments || data.dreams || (Array.isArray(data) ? data : []);
      
      if (Array.isArray(fragments)) {
        for (const dream of fragments) {
          allDreams.push({
            ...dream,
            date,
            source_file: file,
          });
        }
      }
    }
    
    // Sort by insight score desc, then by date desc
    allDreams.sort((a, b) => {
      const insightDiff = (b.insight || 0) - (a.insight || 0);
      if (insightDiff !== 0) return insightDiff;
      return new Date(b.date) - new Date(a.date);
    });
    
    // Take top dreams by limit
    const dreams = allDreams.slice(0, limit);
    
    // Check for highlights file
    let highlights = [];
    const highlightsPath = join(dreamsDir, 'highlights.md');
    
    if (existsSync(highlightsPath)) {
      try {
        const content = readFileSync(highlightsPath, 'utf-8');
        // Extract recent highlights (split by ##)
        const entries = content.split(/^## /m).filter(Boolean).slice(0, 5);
        highlights = entries.map(e => {
          const lines = e.trim().split('\n');
          return {
            title: lines[0].trim(),
            content: lines.slice(1).join('\n').trim().slice(0, 200),
          };
        });
      } catch (e) {
        // Ignore highlights read errors
      }
    }
    
    res.json({
      dreams,
      count: dreams.length,
      total_dreams: allDreams.length,
      days_with_dreams: files.length,
      highlights,
    });
  } catch (err) {
    console.error('Dreams route error:', err);
    res.status(500).json({ error: 'Failed to load dreams' });
  }
});

export default router;
