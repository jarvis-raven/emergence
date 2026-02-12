/**
 * Drives Routes — GET /api/drives, POST /api/drives/:name/satisfy
 * 
 * Returns drive state from .emergence/state/drives.json
 * Handles drive satisfaction (reset pressure to 0)
 * 
 * Phase 3.5 additions:
 * - GET /api/drives/pending-reviews — drives awaiting consolidation review
 * - GET /api/drives/latent — inactive/latent drives
 * - GET /api/drives/:name/aspects — aspects for a drive
 * - POST /api/drives/:name/activate — activate latent drive
 */

import { Router } from 'express';
import { loadConfig, getStatePath } from '../utils/configLoader.js';
import { readJsonFile } from '../utils/fileReader.js';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const router = Router();

/**
 * GET /api/drives/state
 * Returns lightweight runtime state from drives-state.json
 * Used by daemon health monitoring
 */
router.get('/state', (req, res) => {
  try {
    const config = loadConfig();
    const statePath = getStatePath(config, 'drives-state.json');
    
    const data = readJsonFile(statePath);
    
    if (!data) {
      return res.status(404).json({ error: 'Daemon state not found' });
    }
    
    res.json(data);
  } catch (err) {
    console.error('Drives state route error:', err);
    res.status(500).json({ error: 'Failed to load daemon state' });
  }
});

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
    
    // Enhance drives with aspect counts and graduation candidates
    const enhancedDrives = {};
    for (const [name, drive] of Object.entries(data.drives || {})) {
      const aspects = drive.aspects || [];
      const aspectCount = aspects.length;
      
      // Check if this drive has aspects that could graduate
      // (v2 plan: 50% pressure dominance over 7 days + 10 satisfactions + 14 days as aspect)
      const graduationCandidates = [];
      if (drive.aspect_details) {
        for (const aspect of drive.aspect_details) {
          const couldGraduate = 
            (aspect.pressure_contribution_7d || 0) > 0.5 &&
            (aspect.satisfaction_count || 0) >= 10 &&
            aspect.created_at &&
            (new Date() - new Date(aspect.created_at)) > (14 * 24 * 60 * 60 * 1000);
          
          if (couldGraduate) {
            graduationCandidates.push(aspect.name);
          }
        }
      }
      
      enhancedDrives[name] = {
        ...drive,
        aspect_count: aspectCount,
        aspects_list: aspects,
        has_aspects: aspectCount > 0,
        max_aspects_reached: aspectCount >= 5, // v2 plan: max 5 aspects
        graduation_candidates: graduationCandidates,
        has_graduation_candidates: graduationCandidates.length > 0,
      };
    }
    
    res.json({
      ...data,
      drives: enhancedDrives,
      _enhanced: true,
      _timestamp: new Date().toISOString(),
    });
  } catch (err) {
    console.error('Drives route error:', err);
    res.status(500).json({ error: 'Failed to load drives' });
  }
});

/**
 * GET /api/drives/pending-reviews
 * Returns drives awaiting consolidation review
 */
router.get('/pending-reviews', (req, res) => {
  try {
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    const pendingPath = getStatePath(config, 'pending-reviews.json');
    
    // Check for pending-reviews.json first
    if (existsSync(pendingPath)) {
      const pendingData = readJsonFile(pendingPath);
      if (pendingData && pendingData.length > 0) {
        return res.json({
          has_pending: true,
          count: pendingData.length,
          reviews: pendingData,
        });
      }
    }
    
    // Fall back to checking drives with pending_review flag
    const data = readJsonFile(drivesPath);
    const drives = data?.drives || {};
    
    const pendingReviews = [];
    for (const [name, drive] of Object.entries(drives)) {
      if (drive.pending_review || drive.similar_to) {
        pendingReviews.push({
          drive_name: name,
          description: drive.description,
          similar_to: drive.similar_to || [],
          discovered_at: drive.created_at,
          review_reason: drive.review_reason || 'similarity_detected',
        });
      }
    }
    
    res.json({
      has_pending: pendingReviews.length > 0,
      count: pendingReviews.length,
      reviews: pendingReviews,
    });
  } catch (err) {
    console.error('Pending reviews error:', err);
    res.status(500).json({ error: 'Failed to load pending reviews' });
  }
});

/**
 * GET /api/drives/latent
 * Returns inactive/latent drives
 */
router.get('/latent', (req, res) => {
  try {
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    
    const data = readJsonFile(drivesPath);
    const drives = data?.drives || {};
    
    const latentDrives = [];
    for (const [name, drive] of Object.entries(drives)) {
      if (drive.status === 'latent') {
        latentDrives.push({
          name: name,
          description: drive.description,
          created_at: drive.created_at,
          latent_reason: drive.latent_reason || 'Consolidated as aspect',
          aspect_of: drive.aspect_of || null,
          discovered_during: drive.discovered_during,
          // Budget impact if activated
          estimated_daily_cost: 2.50,
        });
      }
    }
    
    // Calculate if budget allows activation
    const dailyLimit = config.budget?.daily_limit || 50.00;
    const today = new Date().toISOString().split('T')[0];
    let todaySpend = 0;
    
    for (const drive of Object.values(drives)) {
      const events = drive.satisfaction_events || [];
      for (const event of events) {
        if (event.startsWith(today)) {
          todaySpend += 2.50; // cost per trigger
        }
      }
    }
    
    const budgetRemaining = dailyLimit - todaySpend;
    const canActivate = budgetRemaining >= 2.50;
    
    res.json({
      has_latent: latentDrives.length > 0,
      count: latentDrives.length,
      drives: latentDrives,
      budget: {
        remaining: Math.round(budgetRemaining * 100) / 100,
        can_activate: canActivate,
        activation_cost: 2.50,
      },
    });
  } catch (err) {
    console.error('Latent drives error:', err);
    res.status(500).json({ error: 'Failed to load latent drives' });
  }
});

/**
 * GET /api/drives/:name/aspects
 * Returns aspects for a specific drive
 */
router.get('/:name/aspects', (req, res) => {
  try {
    const { name } = req.params;
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    
    if (!existsSync(drivesPath)) {
      return res.status(404).json({ error: 'Drives state file not found' });
    }
    
    const content = readFileSync(drivesPath, 'utf-8');
    const data = JSON.parse(content);
    
    if (!data.drives) {
      return res.status(404).json({ error: 'No drives found' });
    }
    
    // Find drive by name (case insensitive)
    const driveName = Object.keys(data.drives).find(
      n => n.toUpperCase() === name.toUpperCase()
    );
    
    if (!driveName) {
      return res.status(404).json({ error: `Drive "${name}" not found` });
    }
    
    const drive = data.drives[driveName];
    const aspects = drive.aspects || [];
    const aspectDetails = drive.aspect_details || [];
    
    // Calculate if any aspect could graduate
    const graduationInfo = [];
    for (const aspect of aspectDetails) {
      const satisfactionCount = aspect.satisfaction_count || 0;
      const pressureContribution = aspect.pressure_contribution_7d || 0;
      const createdAt = aspect.created_at ? new Date(aspect.created_at) : null;
      const daysAsAspect = createdAt 
        ? Math.floor((new Date() - createdAt) / (1000 * 60 * 60 * 24))
        : 0;
      
      const couldGraduate = 
        pressureContribution > 0.5 &&
        satisfactionCount >= 10 &&
        daysAsAspect >= 14;
      
      graduationInfo.push({
        name: aspect.name,
        satisfaction_count: satisfactionCount,
        pressure_contribution_7d: pressureContribution,
        days_as_aspect: daysAsAspect,
        could_graduate: couldGraduate,
      });
    }
    
    res.json({
      drive: driveName,
      aspect_count: aspects.length,
      aspects: aspects,
      aspect_details: aspectDetails,
      graduation_candidates: graduationInfo.filter(a => a.could_graduate),
      max_aspects_reached: aspects.length >= 5,
      remaining_aspect_slots: Math.max(0, 5 - aspects.length),
    });
  } catch (err) {
    console.error('Aspects error:', err);
    res.status(500).json({ error: 'Failed to load aspects' });
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

/**
 * POST /api/drives/:name/activate
 * Activate a latent drive
 */
router.post('/:name/activate', (req, res) => {
  try {
    const { name } = req.params;
    const config = loadConfig();
    const drivesPath = getStatePath(config, 'drives.json');
    
    if (!existsSync(drivesPath)) {
      return res.status(404).json({ error: 'Drives state file not found' });
    }
    
    const content = readFileSync(drivesPath, 'utf-8');
    const data = JSON.parse(content);
    
    if (!data.drives) {
      return res.status(404).json({ error: 'No drives found' });
    }
    
    // Find drive by name
    const driveName = Object.keys(data.drives).find(
      n => n.toUpperCase() === name.toUpperCase()
    );
    
    if (!driveName) {
      return res.status(404).json({ error: `Drive "${name}" not found` });
    }
    
    const drive = data.drives[driveName];
    
    // Check if drive is latent
    if (drive.status !== 'latent') {
      return res.status(400).json({ 
        error: `Drive "${name}" is not latent`,
        status: drive.status || 'active',
      });
    }
    
    // Check budget
    const dailyLimit = config.budget?.daily_limit || 50.00;
    const today = new Date().toISOString().split('T')[0];
    let todaySpend = 0;
    
    for (const d of Object.values(data.drives)) {
      const events = d.satisfaction_events || [];
      for (const event of events) {
        if (event.startsWith(today)) {
          todaySpend += 2.50;
        }
      }
    }
    
    const budgetRemaining = dailyLimit - todaySpend;
    
    if (budgetRemaining < 2.50) {
      return res.status(403).json({
        error: 'Budget limit reached',
        daily_limit: dailyLimit,
        spent: todaySpend,
        remaining: budgetRemaining,
      });
    }
    
    // Activate the drive
    drive.status = 'active';
    drive.activated_at = new Date().toISOString();
    drive.previous_status = 'latent';
    
    // Initialize pressure at 0
    drive.pressure = 0;
    
    // Set rate if not present
    if (!drive.rate_per_hour) {
      drive.rate_per_hour = 1.5; // Base rate for discovered drives
    }
    
    // Write back
    writeFileSync(drivesPath, JSON.stringify(data, null, 2));
    
    res.json({
      success: true,
      drive: driveName,
      status: 'active',
      activated_at: drive.activated_at,
      estimated_daily_cost: 2.50,
    });
  } catch (err) {
    console.error('Activate drive error:', err);
    res.status(500).json({ error: 'Failed to activate drive' });
  }
});

/**
 * POST /api/drives/review
 * Trigger a review for all pending reviews
 */
router.post('/review', (req, res) => {
  try {
    const config = loadConfig();
    const pendingPath = getStatePath(config, 'pending-reviews.json');
    
    if (!existsSync(pendingPath)) {
      return res.json({
        has_pending: false,
        message: 'No pending reviews',
      });
    }
    
    const content = readFileSync(pendingPath, 'utf-8');
    const pending = JSON.parse(content);
    
    res.json({
      has_pending: pending.length > 0,
      count: pending.length,
      message: pending.length > 0 
        ? `Found ${pending.length} drive(s) awaiting review`
        : 'No pending reviews',
      reviews: pending,
    });
  } catch (err) {
    console.error('Review error:', err);
    res.status(500).json({ error: 'Failed to process review' });
  }
});

export default router;
