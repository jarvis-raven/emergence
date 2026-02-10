/**
 * First Light Routes — GET /api/first-light
 * 
 * Returns First Light status, gates, progress from .emergence/state/first-light.json
 */

import { Router } from 'express';
import { loadConfig, getStatePath } from '../utils/configLoader.js';
import { readJsonFile } from '../utils/fileReader.js';

const router = Router();

/**
 * GET /api/first-light
 * Returns First Light status, gates, progress
 */
router.get('/', (req, res) => {
  try {
    const config = loadConfig();
    const firstLightPath = getStatePath(config, 'first-light.json');
    
    const data = readJsonFile(firstLightPath);
    
    if (!data) {
      // Return default state if file doesn't exist
      return res.json({
        status: 'pending',
        started_at: null,
        sessions_completed: 0,
        drives_discovered: [],
        gates: {
          drive_diversity: false,
          self_authored_identity: false,
          unprompted_initiative: false,
          profile_stability: false,
          care_signal: false,
        },
        completed_at: null,
        progress_pct: 0,
      });
    }
    
    // Calculate progress percentage
    const gates = data.gates || {};
    const gateKeys = Object.keys(gates);
    const completedGates = gateKeys.filter(k => gates[k]).length;
    const progressPct = gateKeys.length > 0 
      ? Math.round((completedGates / gateKeys.length) * 100) 
      : 0;
    
    res.json({
      ...data,
      progress_pct: progressPct,
      gates_completed: completedGates,
      gates_total: gateKeys.length,
    });
  } catch (err) {
    console.error('First Light route error:', err);
    res.status(500).json({ error: 'Failed to load First Light state' });
  }
});

export default router;
