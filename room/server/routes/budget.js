/**
 * Budget Routes — GET /api/budget/status
 *
 * Returns budget status: daily spend, limit, projected monthly costs
 * Reads from drives.json and emergence.json config
 */

import { Router } from 'express';
import { loadConfig, getStatePath } from '../utils/configLoader.js';
import { readJsonFile } from '../utils/fileReader.js';

const router = Router();

/**
 * Calculate daily spend from satisfaction events
 * @param {object} drives - Drives data
 * @returns {number} Estimated daily spend
 */
function calculateDailySpend(drives) {
  const today = new Date().toISOString().split('T')[0];
  let dailyTriggers = 0;

  for (const drive of Object.values(drives)) {
    const events = drive.satisfaction_events || [];
    for (const event of events) {
      if (event.startsWith(today)) {
        dailyTriggers++;
      }
    }
  }

  // Estimate cost at $2.50 per trigger (configurable by model)
  const costPerTrigger = 2.5;
  return dailyTriggers * costPerTrigger;
}

/**
 * Calculate average triggers per day from history
 * @param {object} drives - Drives data
 * @returns {number} Average triggers per day
 */
function calculateAvgTriggersPerDay(drives) {
  const allEvents = [];

  for (const drive of Object.values(drives)) {
    const events = drive.satisfaction_events || [];
    allEvents.push(...events);
  }

  if (allEvents.length === 0) {
    return 0;
  }

  // Sort events by date
  allEvents.sort();

  const firstEvent = new Date(allEvents[0]);
  const lastEvent = new Date(allEvents[allEvents.length - 1]);
  const daysElapsed = Math.max(1, (lastEvent - firstEvent) / (1000 * 60 * 60 * 24));

  return allEvents.length / daysElapsed;
}

/**
 * Count active base drives (not latent, not aspects)
 * @param {object} drives - Drives data
 * @returns {number} Count of active base drives
 */
function countActiveDrives(drives) {
  return Object.values(drives).filter((d) => {
    // Skip latent drives
    if (d.status === 'latent') return false;
    // Skip aspect-only drives (they're part of a parent)
    if (d.aspect_of) return false;
    return true;
  }).length;
}

/**
 * Count latent drives
 * @param {object} drives - Drives data
 * @returns {number} Count of latent drives
 */
function countLatentDrives(drives) {
  return Object.values(drives).filter((d) => d.status === 'latent').length;
}

/**
 * Count pending reviews
 * @param {object} drives - Drives data
 * @returns {number} Count of drives with pending reviews
 */
function countPendingReviews(drives) {
  return Object.values(drives).filter((d) => d.pending_review === true).length;
}

/**
 * GET /api/budget/status
 * Returns daily spend, limit, projected monthly costs
 */
router.get('/status', (req, res) => {
  try {
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');

    const data = readJsonFile(drivesPath);
    const drives = data?.drives || {};

    // Get budget from config
    const dailyLimit = config.budget?.daily_limit || 50.0;
    const costPerTrigger = config.budget?.cost_per_trigger || 2.5;

    // Calculate metrics
    const dailySpend = calculateDailySpend(drives);
    const dailyPercent = dailyLimit > 0 ? (dailySpend / dailyLimit) * 100 : 0;

    const avgTriggersPerDay = calculateAvgTriggersPerDay(drives);
    const projectedDaily = avgTriggersPerDay * costPerTrigger;
    const projectedMonthly = projectedDaily * 30;

    const activeDrives = countActiveDrives(drives);
    const latentDrives = countLatentDrives(drives);
    const pendingReviews = countPendingReviews(drives);

    // Determine warning level
    let warningLevel = 'normal'; // green
    if (dailyPercent >= 90) {
      warningLevel = 'critical'; // red
    } else if (dailyPercent >= 75) {
      warningLevel = 'warning'; // yellow
    }

    res.json({
      daily: {
        spent: Math.round(dailySpend * 100) / 100,
        limit: dailyLimit,
        percent: Math.round(dailyPercent * 10) / 10,
        warning_level: warningLevel,
      },
      projected: {
        triggers_per_day: Math.round(avgTriggersPerDay * 10) / 10,
        cost_per_day: Math.round(projectedDaily * 100) / 100,
        monthly: Math.round(projectedMonthly * 100) / 100,
      },
      drives: {
        active: activeDrives,
        latent: latentDrives,
        total: activeDrives + latentDrives,
      },
      consolidation: {
        pending_reviews: pendingReviews,
        has_pending: pendingReviews > 0,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    console.error('Budget route error:', err);
    res.status(500).json({ error: 'Failed to load budget status' });
  }
});

export default router;
