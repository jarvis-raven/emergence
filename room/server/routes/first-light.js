/**
 * First Light Routes — GET /api/first-light, GET /api/first-light/status
 *
 * Returns First Light status, gates, progress from .emergence/state/first-light.json
 * Enhanced with v2 plan gate tracking
 */

import { Router } from 'express';
import { loadConfig, getStatePath } from '../utils/configLoader.js';
import { readJsonFile } from '../utils/fileReader.js';
import { existsSync, readFileSync, writeFileSync } from 'fs';

const router = Router();

/**
 * Calculate gate status for First Light v2
 * @param {object} fl - First light data
 * @returns {object} Gate status
 */
function calculateGateStatus(fl) {
  const now = new Date();
  const startedAt = fl.started_at ? new Date(fl.started_at) : null;
  const elapsedDays = startedAt ? Math.floor((now - startedAt) / (1000 * 60 * 60 * 24)) : 0;

  // Count discovered drives
  const drives = fl.drives || [];
  const discoveredCount = drives.filter((d) => d.category === 'discovered').length;

  // Session count (from v2 plan)
  const sessionCount = fl.session_count || fl.sessions_completed || 0;

  // Default gates from v2 plan
  const gates = fl.gates || {
    min_sessions: 10,
    min_days_elapsed: 7,
    min_discovered_drives: 3,
    max_drives_soft_limit: 8,
  };

  const gateStatus = {
    sessions_met: sessionCount >= gates.min_sessions,
    days_met: elapsedDays >= gates.min_days_elapsed,
    drives_met: discoveredCount >= gates.min_discovered_drives,
    over_soft_limit: discoveredCount > gates.max_drives_soft_limit,
  };

  // All core gates met (not including soft limit)
  const canComplete = gateStatus.sessions_met && gateStatus.days_met && gateStatus.drives_met;

  return {
    sessions: {
      current: sessionCount,
      required: gates.min_sessions,
      met: gateStatus.sessions_met,
    },
    days: {
      current: elapsedDays,
      required: gates.min_days_elapsed,
      met: gateStatus.days_met,
    },
    drives: {
      current: discoveredCount,
      required: gates.min_discovered_drives,
      met: gateStatus.drives_met,
    },
    soft_limit: {
      current: discoveredCount,
      limit: gates.max_drives_soft_limit,
      exceeded: gateStatus.over_soft_limit,
    },
    can_complete: canComplete,
    all_gates_met: canComplete,
  };
}

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

    // Calculate v2 gate status
    const gateStatus = calculateGateStatus(data);

    // Legacy gate calculation
    const gates = data.gates || {};
    const gateKeys = Object.keys(gates);
    const completedGates = gateKeys.filter((k) => gates[k]).length;
    const progressPct =
      gateKeys.length > 0 ? Math.round((completedGates / gateKeys.length) * 100) : 0;

    res.json({
      ...data,
      progress_pct: progressPct,
      gates_completed: completedGates,
      gates_total: gateKeys.length,
      v2_gates: gateStatus,
    });
  } catch (err) {
    console.error('First Light route error:', err);
    res.status(500).json({ error: 'Failed to load First Light state' });
  }
});

/**
 * GET /api/first-light/status
 * Returns detailed First Light status with v2 gate tracking
 */
router.get('/status', (req, res) => {
  try {
    const config = loadConfig();
    const firstLightPath = getStatePath(config, 'first-light.json');

    const data = readJsonFile(firstLightPath);

    if (!data) {
      return res.json({
        active: false,
        status: 'not_started',
        message: 'First Light has not been started',
      });
    }

    // Check if graduated
    if (data.status === 'graduated' || data.status === 'completed') {
      return res.json({
        active: false,
        status: data.status,
        completed_at: data.completed_at,
        sessions: data.session_count || data.sessions_completed || 0,
        message: 'First Light has been completed',
      });
    }

    // Check if active
    const isActive = data.status === 'active' || data.started_at !== null;

    if (!isActive) {
      return res.json({
        active: false,
        status: data.status || 'pending',
        message: 'First Light is pending',
      });
    }

    // Calculate gate status
    const gateStatus = calculateGateStatus(data);

    res.json({
      active: true,
      status: data.status || 'active',
      started_at: data.started_at,
      session_count: data.session_count || data.sessions_completed || 0,
      gates: gateStatus,
      can_complete: gateStatus.can_complete,
      drives: (data.drives || []).map((d) => ({
        name: d.name,
        category: d.category,
        discovered_at: d.discovered_at || data.started_at,
      })),
    });
  } catch (err) {
    console.error('First Light status error:', err);
    res.status(500).json({ error: 'Failed to load First Light status' });
  }
});

/**
 * POST /api/first-light/complete
 * Manually complete First Light
 */
router.post('/complete', (req, res) => {
  try {
    const config = loadConfig();
    const firstLightPath = getStatePath(config, 'first-light.json');

    if (!existsSync(firstLightPath)) {
      return res.status(404).json({ error: 'First Light not started' });
    }

    const content = readFileSync(firstLightPath, 'utf-8');
    const data = JSON.parse(content);

    // Check if already completed
    if (data.status === 'graduated' || data.status === 'completed') {
      return res.json({
        success: false,
        message: 'First Light already completed',
        status: data.status,
      });
    }

    // Calculate gate status
    const gateStatus = calculateGateStatus(data);

    // Complete First Light
    data.status = 'completed';
    data.completed_at = new Date().toISOString();

    // Lock in discovered drives
    const discoveredDrives = (data.drives || [])
      .filter((d) => d.category === 'discovered')
      .map((d) => d.name);

    data.completion_transition = {
      notified: false,
      locked_drives: discoveredDrives,
      transition_message: null,
      manually_completed: true,
    };

    // Write back
    writeFileSync(firstLightPath, JSON.stringify(data, null, 2));

    res.json({
      success: true,
      message: 'First Light completed successfully',
      locked_drives: discoveredDrives,
      gates_at_completion: gateStatus,
    });
  } catch (err) {
    console.error('First Light complete error:', err);
    res.status(500).json({ error: 'Failed to complete First Light' });
  }
});

export default router;
