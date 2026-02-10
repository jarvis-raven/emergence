/**
 * AspirationsShelf — Built-in shelf for aspirations & projects
 * 
 * Data source: ~/.emergence/state/aspirations.json
 * 
 * Structure:
 * {
 *   "aspirations": [
 *     {
 *       "id": "understand-self",
 *       "title": "Understand myself",
 *       "description": "Deep introspection...",
 *       "category": "philosophical",
 *       "createdAt": "2026-01-30",
 *       "throughline": "depth"
 *     }
 *   ],
 *   "projects": [
 *     {
 *       "id": "emergence",
 *       "name": "Emergence Framework",
 *       "aspirationId": "understand-self",
 *       "status": "active",
 *       "category": "framework",
 *       "description": "...",
 *       "startDate": "2026-02-06",
 *       "updatedAt": "2026-02-09"
 *     }
 *   ],
 *   "meta": {
 *     "version": 1,
 *     "updatedAt": "2026-02-09T17:38:00Z"
 *   }
 * }
 */

import { readFileSync, existsSync, writeFileSync } from 'fs';
import { dirname } from 'path';
import { mkdirSync } from 'fs';

const manifest = {
  id: 'aspirations',
  name: 'Aspirations & Projects',
  version: '1.0.0',
  description: 'Vision board: aspirations (the why) and projects (the what)',
  icon: '✨',
  dataSource: {
    type: 'custom',
    refreshInterval: 30000,
  },
};

/**
 * Resolve aspirations data from ~/.emergence/state/aspirations.json
 */
async function resolveData(config) {
  const stateDir = config?.paths?.state || `${process.env.HOME}/.emergence/state`;
  const filePath = `${stateDir}/aspirations.json`;
  
  // Create empty file if missing
  if (!existsSync(filePath)) {
    const emptyData = {
      aspirations: [],
      projects: [],
      meta: {
        version: 1,
        updatedAt: new Date().toISOString(),
      },
    };
    
    try {
      mkdirSync(dirname(filePath), { recursive: true });
      writeFileSync(filePath, JSON.stringify(emptyData, null, 2), 'utf-8');
    } catch (err) {
      console.error(`Failed to create ${filePath}:`, err);
      return emptyData;
    }
  }
  
  try {
    const raw = readFileSync(filePath, 'utf-8');
    const data = JSON.parse(raw);
    
    // Validate structure
    if (!data.aspirations) data.aspirations = [];
    if (!data.projects) data.projects = [];
    if (!data.meta) data.meta = { version: 1, updatedAt: new Date().toISOString() };
    
    return data;
  } catch (err) {
    console.error(`Failed to read ${filePath}:`, err);
    return {
      aspirations: [],
      projects: [],
      meta: { version: 1, updatedAt: new Date().toISOString() },
    };
  }
}

export default {
  manifest,
  resolveData,
};
