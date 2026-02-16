/**
 * Config Routes — GET /api/config
 *
 * Returns agent name, theme, room settings from emergence.json
 */

import { Router } from 'express';
import { loadConfig } from '../utils/configLoader.js';

const router = Router();

/**
 * GET /api/config
 * Returns configuration for the dashboard
 */
router.get('/', (req, res) => {
  try {
    const config = loadConfig();

    // Return only the necessary config values
    const response = {
      agent: {
        name: config.agent?.name || 'My Agent',
        model: config.agent?.model || 'unknown',
      },
      room: {
        port: config.room?.port || 8765,
        theme: config.room?.theme || 'default',
        https: config.room?.https !== false,
      },
      drives: {
        tick_interval: config.drives?.tick_interval || 900,
        quiet_hours: config.drives?.quiet_hours || [23, 7],
      },
      paths: {
        workspace: config.paths?.workspace || '.',
        state: config.paths?.state || '.emergence/state',
        memory: config.paths?.memory || 'memory',
        identity: config.paths?.identity || '.',
      },
    };

    res.json(response);
  } catch (err) {
    console.error('Config route error:', err);
    res.status(500).json({ error: 'Failed to load configuration' });
  }
});

export default router;
