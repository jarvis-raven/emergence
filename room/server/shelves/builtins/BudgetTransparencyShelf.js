/**
 * BudgetTransparencyShelf — Built-in shelf for budget transparency
 * 
 * Shows daily spend vs limit with color warnings (75% yellow, 90% red)
 * Data from drives.json
 */

import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export const BudgetTransparencyShelf = {
  manifest: {
    id: 'budget-transparency',
    name: 'Budget Status',
    version: '1.0.0',
    description: 'Daily spend, limit, and projected monthly costs with warnings',
    icon: '💰',
    priority: 90,
    refreshIntervalMs: 30000,
    dataSource: { type: 'custom' },
    renderer: 'banner',
  },

  async resolveData(config) {
    try {
      // Resolve state path properly
      const workspace = config?._configDir || process.cwd();
      const stateDir = config?.paths?.state 
        ? resolve(workspace, config.paths.state)
        : `${process.env.HOME}/.openclaw/state`;
      const drivesPath = `${stateDir}/drives.json`;
      
      if (!existsSync(drivesPath)) {
        console.log('Budget shelf: drives.json not found at', drivesPath);
        return null;
      }
      
      const content = readFileSync(drivesPath, 'utf-8');
      const data = JSON.parse(content);
      const drives = data?.drives || {};
      
      const dailyLimit = config?.budget?.daily_limit || 50.00;
      const costPerTrigger = config?.budget?.cost_per_trigger || 2.50;
      
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
      
      const dailySpend = dailyTriggers * costPerTrigger;
      const dailyPercent = dailyLimit > 0 ? (dailySpend / dailyLimit) * 100 : 0;
      
      const allEvents = [];
      for (const drive of Object.values(drives)) {
        allEvents.push(...(drive.satisfaction_events || []));
      }
      
      let avgTriggersPerDay = 0;
      if (allEvents.length > 0) {
        allEvents.sort();
        const firstEvent = new Date(allEvents[0]);
        const lastEvent = new Date(allEvents[allEvents.length - 1]);
        const daysElapsed = Math.max(1, (lastEvent - firstEvent) / (1000 * 60 * 60 * 24));
        avgTriggersPerDay = allEvents.length / daysElapsed;
      }
      
      const projectedMonthly = avgTriggersPerDay * costPerTrigger * 30;
      
      let warningLevel = 'normal';
      let warningIcon = '✅';
      if (dailyPercent >= 90) {
        warningLevel = 'critical';
        warningIcon = '🔴';
      } else if (dailyPercent >= 75) {
        warningLevel = 'warning';
        warningIcon = '🟡';
      }
      
      const activeDrives = Object.values(drives).filter(d => d.status !== 'latent' && !d.aspect_of).length;
      const latentDrives = Object.values(drives).filter(d => d.status === 'latent').length;
      
      return {
        title: `${warningIcon} Budget Status`,
        banner: true,
        warning_level: warningLevel,
        daily: {
          spent: Math.round(dailySpend * 100) / 100,
          limit: dailyLimit,
          percent: Math.round(dailyPercent * 10) / 10,
          triggers: dailyTriggers,
        },
        projected: {
          monthly: Math.round(projectedMonthly * 100) / 100,
          daily_average: Math.round(avgTriggersPerDay * costPerTrigger * 100) / 100,
        },
        drives: {
          active: activeDrives,
          latent: latentDrives,
        },
        items: [],
      };
    } catch (err) {
      console.error('BudgetTransparencyShelf error:', err);
      return null;
    }
  },
};
