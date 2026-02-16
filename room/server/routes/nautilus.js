/**
 * Nautilus Routes — GET /api/nautilus/status
 *
 * Returns Nautilus memory system status
 * - Gravity: total chunks, accesses, DB stats
 * - Chambers: atrium/corridor/vault distribution
 * - Doors: file tagging coverage
 * - Mirrors: event reflection coverage
 */

import { Router } from 'express';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);
const router = Router();

/**
 * GET /api/nautilus/status
 * Returns Nautilus system status by calling emergence CLI
 */
router.get('/status', async (req, res) => {
  try {
    // Call emergence CLI for nautilus status
    const { stdout, stderr } = await execAsync('python3 -m core.cli nautilus status', {
      cwd: process.env.EMERGENCE_ROOT || `${process.env.HOME}/projects/emergence`,
      timeout: 5000,
    });

    if (stderr && !stdout) {
      console.error('Nautilus CLI error:', stderr);
      return res.status(500).json({
        error: 'Failed to get Nautilus status',
        details: stderr,
      });
    }

    // Parse JSON output
    const data = JSON.parse(stdout);
    const nautilus = data['🐚 nautilus'] || data.nautilus;

    if (!nautilus) {
      return res.status(500).json({
        error: 'Unexpected Nautilus response format',
        raw: data,
      });
    }

    // Extract and normalize data
    const gravity = nautilus.phase_1_gravity || {};
    const chambers = nautilus.phase_2_chambers || {};
    const doors = nautilus.phase_3_doors || {};
    const mirrors = nautilus.phase_4_mirrors || {};
    const summaryFiles = nautilus.summary_files || {};

    // Calculate percentages
    const totalChunks = gravity.total_chunks || 0;
    const chamberCategorized = (chambers.atrium || 0) + (chambers.corridor || 0);
    const chamberUnknown = chambers.unknown || 0;
    const chamberTotal = chamberCategorized + chamberUnknown;

    const doorTagged = doors.tagged_files || 0;
    const doorTotal = doors.total_files || 0;
    const doorCoverage = doorTotal > 0 ? (doorTagged / doorTotal) * 100 : 0;

    const mirrorTotal = mirrors.total_events || 0;
    const mirrorFull = mirrors.fully_mirrored || 0;
    const mirrorCoverage = mirrors.coverage || {};

    // Build response
    const response = {
      timestamp: new Date().toISOString(),
      gravity: {
        total_chunks: totalChunks,
        total_accesses: gravity.total_accesses || 0,
        superseded: gravity.superseded || 0,
        db_size: gravity.db_size || 0,
        db_path: gravity.db_path,
      },
      chambers: {
        atrium: chambers.atrium || 0,
        corridor: chambers.corridor || 0,
        unknown: chamberUnknown,
        total: chamberTotal,
        categorized: chamberCategorized,
        coverage_pct: chamberTotal > 0 ? (chamberCategorized / chamberTotal) * 100 : 0,
      },
      doors: {
        tagged_files: doorTagged,
        total_files: doorTotal,
        coverage_pct: doorCoverage,
        coverage_display: doors.coverage || `${doorTagged}/${doorTotal}`,
      },
      mirrors: {
        total_events: mirrorTotal,
        fully_mirrored: mirrorFull,
        coverage: {
          raw: mirrorCoverage.raw || 0,
          summary: mirrorCoverage.summary || 0,
          lesson: mirrorCoverage.lesson || 0,
        },
        coverage_pct: mirrorTotal > 0 ? (mirrorFull / mirrorTotal) * 100 : 0,
      },
      summary_files: {
        corridors: summaryFiles.corridors || 0,
        vaults: summaryFiles.vaults || 0,
      },
      _raw: nautilus, // Include raw data for debugging
    };

    res.json(response);
  } catch (err) {
    console.error('Nautilus status error:', err);
    res.status(500).json({
      error: 'Failed to get Nautilus status',
      message: err.message,
      details: err.stderr || err.stdout,
    });
  }
});

export default router;
