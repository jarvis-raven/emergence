/**
 * File Reader — Safe file reading with error handling
 * 
 * All file reads go through here for consistent error handling.
 * Missing files return null instead of throwing.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, readdirSync } from 'fs';
import { join, dirname } from 'path';

/**
 * Safely read a text file
 * 
 * @param {string} path - File path
 * @returns {string|null} File content or null if not found/error
 */
export function readTextFile(path) {
  try {
    if (!existsSync(path)) {
      return null;
    }
    return readFileSync(path, 'utf-8');
  } catch (err) {
    console.error(`Error reading ${path}:`, err.message);
    return null;
  }
}

/**
 * Safely read and parse JSON
 * 
 * @param {string} path - File path
 * @returns {object|null} Parsed JSON or null if not found/error
 */
export function readJsonFile(path) {
  try {
    if (!existsSync(path)) {
      // Silently return null - missing files are expected during init/startup
      return null;
    }
    const content = readFileSync(path, 'utf-8');
    return JSON.parse(content);
  } catch (err) {
    // Only log actual errors (not ENOENT which is handled above)
    if (err.code !== 'ENOENT') {
      console.error(`Error parsing JSON ${path}:`, err.message);
    }
    return null;
  }
}

/**
 * Safely write JSON file
 * 
 * @param {string} path - File path
 * @param {object} data - Data to write
 * @returns {boolean} Success
 */
export function writeJsonFile(path, data) {
  try {
    const dir = dirname(path);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    
    writeFileSync(path, JSON.stringify(data, null, 2));
    return true;
  } catch (err) {
    console.error(`Error writing JSON ${path}:`, err.message);
    return false;
  }
}

/**
 * List files in directory matching pattern
 * 
 * @param {string} dir - Directory path
 * @param {RegExp} pattern - Filename pattern to match
 * @returns {string[]} Matching filenames
 */
export function listFiles(dir, pattern = null) {
  try {
    if (!existsSync(dir)) {
      return [];
    }
    
    const files = readdirSync(dir);
    
    if (!pattern) {
      return files;
    }
    
    return files.filter(f => pattern.test(f));
  } catch (err) {
    console.error(`Error listing ${dir}:`, err.message);
    return [];
  }
}

/**
 * Get file stats
 * 
 * @param {string} path - File path
 * @returns {object|null} Stats or null
 */
export function getFileStats(path) {
  try {
    if (!existsSync(path)) {
      return null;
    }
    return statSync(path);
  } catch (err) {
    return null;
  }
}

/**
 * Get directory size recursively
 * 
 * @param {string} dir - Directory path
 * @returns {number} Total size in bytes
 */
export function getDirectorySize(dir) {
  try {
    if (!existsSync(dir)) {
      return 0;
    }
    
    const files = readdirSync(dir, { withFileTypes: true });
    let total = 0;
    
    for (const file of files) {
      const path = join(dir, file.name);
      if (file.isDirectory()) {
        total += getDirectorySize(path);
      } else {
        const stats = getFileStats(path);
        if (stats) {
          total += stats.size;
        }
      }
    }
    
    return total;
  } catch (err) {
    return 0;
  }
}

/**
 * Count files in directory matching pattern
 * 
 * @param {string} dir - Directory path
 * @param {RegExp} pattern - Filename pattern
 * @returns {number} Count
 */
export function countFiles(dir, pattern = null) {
  try {
    if (!existsSync(dir)) {
      return 0;
    }
    
    const files = readdirSync(dir, { withFileTypes: true });
    
    if (!pattern) {
      return files.filter(f => f.isFile()).length;
    }
    
    return files.filter(f => f.isFile() && pattern.test(f.name)).length;
  } catch (err) {
    return 0;
  }
}
