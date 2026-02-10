/**
 * Drives Routes — GET /api/drives, POST /api/drives/:name/satisfy
 * 
 * Returns drive state from .emergence/state/drives.json
 * Handles drive satisfaction (reset pressure to 0)
 */

import { Router } from 'express';
import { loadConfig, getStatePath } from '../utils/configLoader.js';
import { readJsonFile } from '../utils/fileReader.js';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const router = Router();

/**
 * GET /api/drives
 * Returns all drives with pressure, threshold, rate, triggered list
 */
router.get('/', (req, res) => {
  try {
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    
    const data = readJsonFile(drivesPath);
    
    if (!data) {
      // Return empty state if file doesn't exist
      return res.json({
        version: '1.0',
        last_tick: new Date().toISOString(),
        drives: {},
        triggered_drives: [],
        trigger_log: [],
      });
    }
    
    res.json(data);
  } catch (err) {
    console.error('Drives route error:', err);
    res.status(500).json({ error: 'Failed to load drives' });
  }
});

/**
 * POST /api/drives/:name/satisfy
 * Satisfy a drive (reset pressure to 0)
 * Fuzzy matches drive name like the Python side
 */
router.post('/:name/satisfy', (req, res) => {
  try {
    const { name } = req.params;
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    
    if (!existsSync(drivesPath)) {
      return res.status(404).json({ error: 'Drives state file not found' });
    }
    
    // Read current drives state
    const content = readFileSync(drivesPath, 'utf-8');
    const data = JSON.parse(content);
    
    if (!data.drives) {
      return res.status(404).json({ error: 'No drives found' });
    }
    
    // Find drive by name (fuzzy match)
    const driveNames = Object.keys(data.drives);
    const normalizedInput = name.toUpperCase().replace(/[-_]/g, '');
    
    let matchedDrive = null;
    
    // Exact match first
    matchedDrive = driveNames.find(n => n.toUpperCase() === name.toUpperCase());
    
    // Fuzzy match if no exact
    if (!matchedDrive) {
      matchedDrive = driveNames.find(n => {
        const normalized = n.toUpperCase().replace(/[-_]/g, '');
        return normalized === normalizedInput ||
               normalized.includes(normalizedInput) ||
               normalizedInput.includes(normalized);
      });
    }
    
    if (!matchedDrive) {
      return res.status(404).json({ 
        error: `Drive "${name}" not found`,
        available: driveNames
      });
    }
    
    // Update the drive
    const drive = data.drives[matchedDrive];
    const previousPressure = drive.pressure;
    drive.pressure = 0;
    
    // Add satisfaction timestamp
    if (!drive.satisfaction_events) {
      drive.satisfaction_events = [];
    }
    drive.satisfaction_events.push(new Date().toISOString());
    
    // Trim to last 10 events
    if (drive.satisfaction_events.length > 10) {
      drive.satisfaction_events = drive.satisfaction_events.slice(-10);
    }
    
    // Remove from triggered_drives if present
    if (data.triggered_drives) {
      data.triggered_drives = data.triggered_drives.filter(
        d => d.toUpperCase() !== matchedDrive.toUpperCase()
      );
    }
    
    // Update last_tick
    data.last_tick = new Date().toISOString();
    
    // Write back
    writeFileSync(drivesPath, JSON.stringify(data, null, 2));
    
    res.json({
      success: true,
      drive: matchedDrive,
      previous_pressure: previousPressure,
      current_pressure: 0,
      timestamp: data.last_tick,
    });
  } catch (err) {
    console.error('Satisfy drive error:', err);
    res.status(500).json({ error: 'Failed to satisfy drive' });
  }
});

export default router;
