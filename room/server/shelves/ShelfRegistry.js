/**
 * ShelfRegistry — discovers and manages shelf manifests
 * 
 * Built-in shelves registered in code.
 * Custom shelves discovered from ${statePath}/shelves/ directory.
 * Each subdirectory with a valid shelf.json becomes a shelf.
 */

import { readdirSync, existsSync } from 'fs';
import { join, resolve } from 'path';
import { readJsonFile } from '../utils/fileReader.js';

export class ShelfRegistry {
  constructor(statePath) {
    this.statePath = statePath;
    this.shelvesPath = join(statePath, 'shelves');
    this.builtins = new Map();
    this.custom = new Map();
  }

  /**
   * Register a built-in shelf
   * @param {object} shelfDef - Shelf definition with manifest and resolveData function
   */
  registerBuiltin(shelfDef) {
    if (!shelfDef?.manifest?.id) {
      console.error('Invalid built-in shelf: missing manifest.id');
      return;
    }
    this.builtins.set(shelfDef.manifest.id, {
      ...shelfDef,
      isBuiltin: true,
      status: 'active',
      discoveredAt: Date.now(),
    });
  }

  /**
   * Discover custom shelves from the shelves directory
   */
  async discover() {
    this.custom.clear();
    
    if (!existsSync(this.shelvesPath)) {
      return;
    }

    try {
      const entries = readdirSync(this.shelvesPath, { withFileTypes: true });
      
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        
        const shelfDir = join(this.shelvesPath, entry.name);
        const manifestPath = join(shelfDir, 'shelf.json');
        
        if (!existsSync(manifestPath)) continue;
        
        const raw = readJsonFile(manifestPath);
        if (!raw) {
          console.error(`Failed to read shelf.json from ${entry.name}`);
          continue;
        }
        
        const manifest = this.validateManifest(raw, entry.name);
        if (!manifest) {
          console.error(`Invalid shelf.json in ${entry.name}`);
          continue;
        }
        
        this.custom.set(manifest.id, {
          manifest,
          isBuiltin: false,
          status: 'active',
          shelfDir,
          discoveredAt: Date.now(),
        });
      }
    } catch (err) {
      console.error('Error discovering shelves:', err.message);
    }
  }

  /**
   * Validate and clean a manifest object
   * @param {object} raw - Raw manifest data
   * @param {string} dirName - Directory name for auto-deriving id
   * @returns {object|null} Cleaned manifest or null if invalid
   */
  validateManifest(raw, dirName) {
    if (!raw.name || typeof raw.name !== 'string') {
      console.error('Manifest missing required field: name');
      return null;
    }
    if (!raw.endpoint || typeof raw.endpoint !== 'string') {
      console.error('Manifest missing required field: endpoint');
      return null;
    }

    const id = raw.id || dirName;
    
    const manifest = {
      id,
      name: raw.name,
      icon: raw.icon || '📦',
      description: raw.description || '',
      endpoint: raw.endpoint,
      version: raw.version || '1.0',
      priority: typeof raw.priority === 'number' ? raw.priority : 50,
      refreshIntervalMs: typeof raw.refreshIntervalMs === 'number' ? raw.refreshIntervalMs : 30000,
      dataSource: {
        type: raw.dataSource?.type || 'inline',
        path: raw.dataSource?.path || null,
      },
      renderer: raw.renderer || 'auto',
    };

    const validTypes = ['custom', 'file', 'inline'];
    if (!validTypes.includes(manifest.dataSource.type)) {
      console.error(`Invalid dataSource.type: ${manifest.dataSource.type}`);
      return null;
    }

    return manifest;
  }

  /**
   * Get all shelves (built-in and custom) sorted by priority desc
   * @returns {Array} Array of { manifest, status, isBuiltin }
   */
  getAll() {
    const all = [];
    
    for (const [id, shelf] of this.builtins) {
      all.push({
        manifest: shelf.manifest,
        status: shelf.status,
        isBuiltin: shelf.isBuiltin,
      });
    }
    
    for (const [id, shelf] of this.custom) {
      all.push({
        manifest: shelf.manifest,
        status: shelf.status,
        isBuiltin: shelf.isBuiltin,
      });
    }
    
    return all.sort((a, b) => b.manifest.priority - a.manifest.priority);
  }

  /**
   * Get a single shelf by id
   * @param {string} id - Shelf id
   * @returns {object|null} Shelf object or null
   */
  get(id) {
    if (this.builtins.has(id)) {
      const shelf = this.builtins.get(id);
      return {
        manifest: shelf.manifest,
        status: shelf.status,
        isBuiltin: shelf.isBuiltin,
      };
    }
    
    if (this.custom.has(id)) {
      const shelf = this.custom.get(id);
      return {
        manifest: shelf.manifest,
        status: shelf.status,
        isBuiltin: shelf.isBuiltin,
      };
    }
    
    return null;
  }

  /**
   * Resolve data for a shelf based on its dataSource configuration
   * @param {string} id - Shelf id
   * @param {object} config - App config for custom resolvers
   * @returns {Promise<object|null>} Resolved data
   */
  async resolveData(id, config) {
    // Check built-ins first
    if (this.builtins.has(id)) {
      const shelf = this.builtins.get(id);
      const { manifest, resolveData } = shelf;
      
      if (manifest.dataSource.type === 'custom' && typeof resolveData === 'function') {
        try {
          return await resolveData(config);
        } catch (err) {
          console.error(`Error resolving custom data for ${id}:`, err.message);
          return null;
        }
      }
      
      if (manifest.dataSource.type === 'inline') {
        return { ...manifest };
      }
      
      return null;
    }
    
    // Check custom shelves
    if (this.custom.has(id)) {
      const shelf = this.custom.get(id);
      const { manifest, shelfDir } = shelf;
      
      if (manifest.dataSource.type === 'file' && manifest.dataSource.path) {
        const filePath = resolve(shelfDir, manifest.dataSource.path);
        const data = readJsonFile(filePath);
        return data !== null ? data : null;
      }
      
      if (manifest.dataSource.type === 'inline') {
        return { ...manifest };
      }
      
      return null;
    }
    
    return null;
  }
}
