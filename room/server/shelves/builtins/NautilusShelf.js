/**
 * NautilusShelf — Built-in shelf for Nautilus memory system status
 * 
 * Displays Nautilus architecture status:
 * - Phase 1: Gravity (chunk storage)
 * - Phase 2: Chambers (atrium/corridor/vault distribution)
 * - Phase 3: Doors (file tagging coverage)
 * - Phase 4: Mirrors (event reflection coverage)
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const NautilusShelf = {
  manifest: {
    id: 'nautilus',
    name: 'Nautilus',
    icon: '🐚',
    description: 'Memory system architecture and coverage metrics',
    endpoint: '/api/shelves/nautilus',
    version: '1.0',
    priority: 95, // Just below Memory shelf
    refreshIntervalMs: 30000,
    dataSource: { type: 'custom' },
    renderer: 'nautilus',
  },

  async resolveData(config) {
    try {
      const emergenceRoot = process.env.EMERGENCE_ROOT || `${process.env.HOME}/projects/emergence`;
      
      const { stdout, stderr } = await execAsync(
        'python3 -m core.cli nautilus status',
        { 
          cwd: emergenceRoot,
          timeout: 5000,
        }
      );
      
      if (stderr && !stdout) {
        throw new Error(`Nautilus CLI error: ${stderr}`);
      }
      
      const data = JSON.parse(stdout);
      const nautilus = data['🐚 nautilus'] || data.nautilus;
      
      if (!nautilus) {
        throw new Error('Unexpected Nautilus response format');
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
      
      return {
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
      };
    } catch (err) {
      console.error('Nautilus shelf error:', err);
      throw err;
    }
  },
};
