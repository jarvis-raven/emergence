/**
 * ShelfRegistry — discovers and manages shelf manifests
 *
 * Built-in shelves registered in code.
 * Custom shelves discovered from ${statePath}/shelves/ directory.
 * Each subdirectory with a valid shelf.json becomes a shelf.
 */

import { readdirSync, existsSync } from 'fs';
import { join, resolve } from 'path';
import os from 'os';
import { readJsonFile } from '../utils/fileReader.js';

export class ShelfRegistry {
  constructor(statePath) {
    this.statePath = statePath;
    this.shelvesPath = join(statePath, 'shelves');
    this.builtins = new Map();
    this.custom = new Map();
    this.userConfig = null;
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

        // Skip custom shelves that duplicate a built-in shelf ID
        if (this.builtins.has(manifest.id)) {
          console.log(`Skipping custom shelf '${manifest.id}' — overridden by built-in`);
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
   * Load user shelf configuration from ~/.openclaw/config/shelves.json
   * @returns {object} User config or empty defaults
   */
  loadUserConfig() {
    const configPath = join(os.homedir(), '.openclaw', 'config', 'shelves.json');
    const config = readJsonFile(configPath);

    if (!config) {
      return { builtins: {}, custom: {} };
    }

    this.userConfig = config;
    return config;
  }

  /**
   * Apply user preferences to registered shelves
   * @param {object} userConfig - User configuration object
   */
  applyUserPreferences(userConfig) {
    // Apply preferences to built-ins
    for (const [id, pref] of Object.entries(userConfig.builtins || {})) {
      if (this.builtins.has(id)) {
        const shelf = this.builtins.get(id);
        if (pref.enabled === false) {
          shelf.status = 'disabled';
        }
        if (typeof pref.priority === 'number') {
          shelf.manifest.priority = pref.priority;
        }
      }
    }

    // Apply preferences to custom shelves
    for (const [id, pref] of Object.entries(userConfig.custom || {})) {
      if (this.custom.has(id)) {
        const shelf = this.custom.get(id);
        if (pref.enabled === false) {
          shelf.status = 'disabled';
        }
        if (typeof pref.priority === 'number') {
          shelf.manifest.priority = pref.priority;
        }
      }
    }
  }

  /**
   * Disable a shelf (marks as disabled, won't appear in UI)
   * @param {string} id - Shelf id
   * @returns {boolean} Success
   */
  disableShelf(id) {
    if (this.builtins.has(id)) {
      this.builtins.get(id).status = 'disabled';
      return true;
    }

    if (this.custom.has(id)) {
      this.custom.get(id).status = 'disabled';
      return true;
    }

    return false;
  }

  /**
   * Enable a shelf
   * @param {string} id - Shelf id
   * @returns {boolean} Success
   */
  enableShelf(id) {
    if (this.builtins.has(id)) {
      this.builtins.get(id).status = 'active';
      return true;
    }

    if (this.custom.has(id)) {
      this.custom.get(id).status = 'active';
      return true;
    }

    return false;
  }

  /**
   * Set shelf priority (higher numbers appear first)
   * @param {string} id - Shelf id
   * @param {number} priority - Priority value
   * @returns {boolean} Success
   */
  setShelfPriority(id, priority) {
    if (this.builtins.has(id)) {
      this.builtins.get(id).manifest.priority = priority;
      return true;
    }

    if (this.custom.has(id)) {
      this.custom.get(id).manifest.priority = priority;
      return true;
    }

    return false;
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
   * @param {boolean} includeDisabled - Include disabled shelves
   * @returns {Array} Array of { manifest, status, isBuiltin }
   */
  getAll(includeDisabled = false) {
    const all = [];

    for (const [id, shelf] of this.builtins) {
      if (includeDisabled || shelf.status !== 'disabled') {
        all.push({
          manifest: shelf.manifest,
          status: shelf.status,
          isBuiltin: shelf.isBuiltin,
        });
      }
    }

    for (const [id, shelf] of this.custom) {
      if (includeDisabled || shelf.status !== 'disabled') {
        all.push({
          manifest: shelf.manifest,
          status: shelf.status,
          isBuiltin: shelf.isBuiltin,
        });
      }
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
