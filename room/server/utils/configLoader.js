/**
 * Config Loader — Load emergence.json with comment stripping
 * 
 * Reads emergence.json from workspace root, strips // and # comments,
 * and exposes config values for the dashboard.
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, join } from 'path';

// Default configuration values
const DEFAULT_CONFIG = {
  agent: {
    name: 'My Agent',
    model: 'anthropic/claude-sonnet-4-20250514',
  },
  drives: {
    tick_interval: 900,
    quiet_hours: [23, 7],
    daemon_mode: true,
    cooldown_minutes: 30,
  },
  room: {
    port: 8765,
    theme: 'default',
    https: true,
  },
  paths: {
    workspace: '.',
    state: '.emergence/state',
    identity: '.',
    memory: 'memory',
  },
};

/**
 * Strip comments from JSON content
 * Supports both // and # style comments at start of lines
 * 
 * @param {string} content - Raw file content
 * @returns {string} Content with comment lines removed
 */
export function stripComments(content) {
  const lines = [];
  for (const line of content.split('\n')) {
    const stripped = line.trim();
    // Skip full-line comments
    if (stripped.startsWith('//') || stripped.startsWith('#')) {
      continue;
    }
    // Strip inline // comments — find the first // that's outside quotes
    let cleanLine = line;
    let inString = false;
    let escape = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (escape) { escape = false; continue; }
      if (ch === '\\') { escape = true; continue; }
      if (ch === '"') { inString = !inString; continue; }
      if (!inString && ch === '/' && i + 1 < line.length && line[i + 1] === '/') {
        cleanLine = line.substring(0, i).trimEnd();
        break;
      }
    }
    lines.push(cleanLine);
  }
  return lines.join('\n');
}

/**
 * Find emergence.json config file
 * 
 * Priority order:
 * 1. ~/.openclaw/workspace/emergence.json (canonical OpenClaw location)
 * 2. Search upward from startPath (for non-OpenClaw installs)
 * 3. ~/.emergence/emergence.json (legacy location)
 * 
 * @param {string} startPath - Where to start searching (for upward walk fallback)
 * @returns {string|null} Path to config file or null
 */
export function findConfig(startPath = process.cwd()) {
  const configName = 'emergence.json';
  const home = process.env.HOME || process.env.USERPROFILE || '.';
  
  // Priority 1: Check OpenClaw workspace FIRST (canonical location)
  const openclawWorkspace = join(home, '.openclaw', 'workspace', configName);
  if (existsSync(openclawWorkspace)) {
    return openclawWorkspace;
  }
  
  // Priority 2: Search upward from startPath (fallback for non-OpenClaw installs)
  let current = resolve(startPath);
  for (let i = 0; i < 100; i++) {
    const configPath = join(current, configName);
    if (existsSync(configPath)) {
      return configPath;
    }
    
    const parent = resolve(current, '..');
    if (parent === current) {
      break;
    }
    current = parent;
  }
  
  // Priority 3: Fall back to ~/.emergence/ (legacy location)
  const homeConfig = join(home, '.emergence', configName);
  if (existsSync(homeConfig)) {
    return homeConfig;
  }
  
  return null;
}

/**
 * Load and parse emergence.json with defaults
 * 
 * @param {string} configPath - Explicit path or null to search
 * @returns {object} Merged configuration with defaults
 */
export function loadConfig(configPath = null) {
  if (!configPath) {
    configPath = findConfig();
  }
  
  if (!configPath || !existsSync(configPath)) {
    return { ...DEFAULT_CONFIG };
  }
  
  try {
    const rawContent = readFileSync(configPath, 'utf-8');
    const cleanContent = stripComments(rawContent);
    const loaded = JSON.parse(cleanContent);
    
    // Deep merge with defaults
    const merged = deepMerge({ ...DEFAULT_CONFIG }, loaded);
    
    // Store the config path for resolving relative paths
    merged._configPath = configPath;
    merged._configDir = resolve(configPath, '..');
    
    return merged;
  } catch (err) {
    console.error('Config error:', err.message);
    return { ...DEFAULT_CONFIG };
  }
}

/**
 * Deep merge two objects
 * 
 * @param {object} target - Base object
 * @param {object} source - Object to merge in
 * @returns {object} Merged object
 */
function deepMerge(target, source) {
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      target[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

/**
 * Get workspace root path from config
 * 
 * @param {object} config - Loaded config
 * @returns {string} Resolved workspace path
 */
export function getWorkspacePath(config) {
  const workspace = config.paths?.workspace || '.';
  if (workspace.startsWith('/')) {
    return workspace;
  }
  return resolve(config._configDir || '.', workspace);
}

/**
 * Get state file path
 * 
 * @param {object} config - Loaded config
 * @param {string} filename - State file name
 * @returns {string} Resolved path
 */
export function getStatePath(config, filename) {
  const workspace = getWorkspacePath(config);
  const stateDir = config.paths?.state || '.emergence/state';
  return resolve(workspace, stateDir, filename);
}

/**
 * Get memory directory path
 * 
 * @param {object} config - Loaded config
 * @param {string} subdir - Optional subdirectory
 * @returns {string} Resolved path
 */
export function getMemoryPath(config, subdir = '') {
  const workspace = getWorkspacePath(config);
  const memoryDir = config.paths?.memory || 'memory';
  return resolve(workspace, memoryDir, subdir);
}

/**
 * Get identity file path
 * 
 * @param {object} config - Loaded config
 * @param {string} filename - Identity file name
 * @returns {string} Resolved path
 */
export function getIdentityPath(config, filename) {
  const workspace = getWorkspacePath(config);
  const identityDir = config.paths?.identity || '.';
  return resolve(workspace, identityDir, filename);
}

// Export defaults for reference
export { DEFAULT_CONFIG };
