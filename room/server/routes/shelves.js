/**
 * Shelves Routes — GET /api/shelves and GET /api/shelves/:id
 */

import { Router } from 'express';
import { loadConfig } from '../utils/configLoader.js';

/**
 * Create shelves router with registry dependency injection
 * @param {ShelfRegistry} shelfRegistry - The initialized shelf registry
 * @returns {Router} Express router
 */
export default function createShelvesRouter(shelfRegistry) {
  const router = Router();

  /**
   * GET /api/shelves
   * List all shelves (manifests only, sorted by priority)
   */
  router.get('/', (req, res) => {
    try {
      const shelves = shelfRegistry.getAll();
      res.json({
        shelves: shelves.map(s => ({
          id: s.manifest.id,
          name: s.manifest.name,
          icon: s.manifest.icon,
          description: s.manifest.description,
          endpoint: s.manifest.endpoint,
          version: s.manifest.version,
          priority: s.manifest.priority,
          refreshIntervalMs: s.manifest.refreshIntervalMs,
          renderer: s.manifest.renderer,
          status: s.status,
          isBuiltin: s.isBuiltin,
        })),
        count: shelves.length,
      });
    } catch (err) {
      console.error('Shelves list route error:', err);
      res.status(500).json({ error: 'Failed to list shelves' });
    }
  });

  /**
   * GET /api/shelves/:id
   * Get full shelf data envelope
   */
  router.get('/:id', async (req, res) => {
    try {
      const { id } = req.params;
      
      const shelf = shelfRegistry.get(id);
      if (!shelf) {
        return res.status(404).json({ error: 'Shelf not found', id });
      }
      
      const config = loadConfig();
      
      let data = null;
      let status = 'ok';
      let error = null;
      
      try {
        data = await shelfRegistry.resolveData(id, config);
        if (data === null) {
          status = 'error';
          error = 'Failed to resolve shelf data';
        }
      } catch (err) {
        console.error(`Error resolving data for shelf ${id}:`, err);
        status = 'error';
        error = err.message;
      }
      
      const response = {
        status,
        shelf: {
          id: shelf.manifest.id,
          name: shelf.manifest.name,
          icon: shelf.manifest.icon,
          renderer: shelf.manifest.renderer,
          isBuiltin: shelf.isBuiltin,
        },
        data,
        updatedAt: new Date().toISOString(),
      };
      
      if (error) {
        response.error = error;
      }
      
      res.json(response);
    } catch (err) {
      console.error('Shelf data route error:', err);
      res.status(500).json({ error: 'Failed to get shelf data' });
    }
  });

  return router;
}
