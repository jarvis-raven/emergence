/**
 * LatentDrivesShelf — Built-in shelf for inactive/latent drives
 * 
 * Shows drives that are latent (consolidated as aspects or manually deactivated)
 * Budget-aware activation
 */

import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export const LatentDrivesShelf = {
  manifest: {
    id: 'latent-drives',
    name: 'Latent Drives',
    version: '1.0.0',
    description: 'Inactive drives - consolidated or awaiting activation',
    icon: '○',
    priority: 40,
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
      
      if (!existsSync(drivesPath)) {
        return null;
      }
      
      const content = readFileSync(drivesPath, 'utf-8');
      const data = JSON.parse(content);
      const drives = data?.drives || {};
      
      const dailyLimit = config?.budget?.daily_limit || 50.00;
      const costPerTrigger = config?.budget?.cost_per_trigger || 2.50;
      
      const today = new Date().toISOString().split('T')[0];
      let todaySpend = 0;
      
      for (const drive of Object.values(drives)) {
        const events = drive.satisfaction_events || [];
        for (const event of events) {
          if (event.startsWith(today)) {
            todaySpend += costPerTrigger;
          }
        }
      }
      
      const budgetRemaining = dailyLimit - todaySpend;
      const canActivate = budgetRemaining >= costPerTrigger;
      
      const items = [];
      for (const [name, drive] of Object.entries(drives)) {
        if (drive.status === 'latent') {
          const latentReason = drive.latent_reason || 'Consolidated as aspect';
          const aspectOf = drive.aspect_of;
          
          items.push({
            id: name,
            title: name,
            subtitle: latentReason,
            description: drive.description,
            metadata: {
              created_at: drive.created_at,
              aspect_of: aspectOf,
              discovered_during: drive.discovered_during,
              activation_cost: costPerTrigger,
              estimated_daily_impact: `+~$${costPerTrigger}/day`,
            },
            actions: [
              {
                label: 'Activate',
                command: `drives activate ${name}`,
                type: 'primary',
                enabled: canActivate,
                disabled_reason: canActivate ? null : 'Budget limit reached',
              },
              {
                label: 'Keep Latent',
                command: `drives dismiss ${name}`,
                type: 'secondary',
              },
            ],
          });
        }
      }
      
      if (items.length === 0) {
        return null;
      }
      
      return {
        title: `○ Latent Drives (${items.length})`,
        count: items.length,
        budget: {
          remaining: Math.round(budgetRemaining * 100) / 100,
          daily_limit: dailyLimit,
          can_activate: canActivate,
          activation_cost: costPerTrigger,
        },
        items: items,
      };
    } catch (err) {
      console.error('LatentDrivesShelf error:', err);
      return null;
    }
  },
};
