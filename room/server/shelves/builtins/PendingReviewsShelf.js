/**
 * PendingReviewsShelf — Built-in shelf for drive consolidation reviews
 *
 * Shows drives awaiting irreducibility testing/consolidation review
 * Data from pending-reviews.json or drives with pending_review flag
 */

import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export const PendingReviewsShelf = {
  manifest: {
    id: 'pending-reviews',
    name: 'Pending Drive Reviews',
    version: '1.0.0',
    description: 'Drives awaiting consolidation review - similarity detected',
    icon: '⚖️',
    priority: 70,
    refreshIntervalMs: 60000,
    dataSource: { type: 'custom' },
    renderer: 'list',
  },

  async resolveData(config) {
    try {
      const workspace = config?._configDir || process.cwd();
      const stateDir = config?.paths?.state
        ? resolve(workspace, config.paths.state)
        : `${process.env.HOME}/.openclaw/state`;
      const drivesPath = `${stateDir}/drives.json`;
      const pendingPath = `${stateDir}/pending-reviews.json`;

      const items = [];

      if (existsSync(pendingPath)) {
        try {
          const content = readFileSync(pendingPath, 'utf-8');
          const pending = JSON.parse(content);

          if (Array.isArray(pending) && pending.length > 0) {
            for (const review of pending) {
              const similarDrives = review.similar_drives || [];
              const similarityText = similarDrives
                .map((d) => `${d.name} (${(d.similarity * 100).toFixed(0)}%)`)
                .join(', ');

              items.push({
                id: review.new_drive,
                title: review.new_drive,
                subtitle: `Similar to: ${similarityText}`,
                description: review.description || 'New drive discovered',
                metadata: {
                  similarity_scores: similarDrives.map((d) => ({
                    drive: d.name,
                    similarity: d.similarity,
                  })),
                  discovered_at: review.discovered_at,
                  review_reason: review.review_reason || 'similarity_detected',
                },
                actions: [
                  {
                    label: 'Review Now',
                    command: `drives review ${review.new_drive}`,
                    type: 'primary',
                  },
                  {
                    label: 'Dismiss',
                    command: `drives dismiss ${review.new_drive}`,
                    type: 'secondary',
                  },
                ],
              });
            }
          }
        } catch (err) {
          console.error('Error reading pending-reviews.json:', err);
        }
      }

      if (existsSync(drivesPath)) {
        try {
          const content = readFileSync(drivesPath, 'utf-8');
          const data = JSON.parse(content);
          const drives = data?.drives || {};

          for (const [name, drive] of Object.entries(drives)) {
            if (drive.pending_review && !items.find((i) => i.id === name)) {
              const similarTo = drive.similar_to || [];
              items.push({
                id: name,
                title: name,
                subtitle:
                  similarTo.length > 0 ? `Similar to: ${similarTo.join(', ')}` : 'Awaiting review',
                description: drive.description,
                metadata: {
                  similar_to: similarTo,
                  created_at: drive.created_at,
                  review_reason: drive.review_reason || 'pending_review',
                },
                actions: [
                  {
                    label: 'Review Now',
                    command: `drives review ${name}`,
                    type: 'primary',
                  },
                ],
              });
            }
          }
        } catch (err) {
          console.error('Error reading drives.json:', err);
        }
      }

      if (items.length === 0) {
        return null;
      }

      return {
        title: `⚖️ Pending Drive Reviews (${items.length})`,
        count: items.length,
        items: items,
        actions: [
          {
            label: 'Review All',
            command: 'drives review --all',
            type: 'primary',
          },
        ],
      };
    } catch (err) {
      console.error('PendingReviewsShelf error:', err);
      return null;
    }
  },
};
