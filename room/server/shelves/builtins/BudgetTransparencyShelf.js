/**
 * BudgetTransparencyShelf — Built-in shelf for budget transparency
 * 
 * Shows daily spend vs limit with color warnings (75% yellow, 90% red)
 * Data from /api/budget/status
 */

const manifest = {
  id: 'budget-transparency',
  name: 'Budget Status',
  version: '1.0.0',
  description: 'Daily spend, limit, and projected monthly costs with warnings',
  icon: '💰',
  priority: 90, // High priority - shows near top
  dataSource: {
    type: 'custom',
    refreshInterval: 30000,
  },
};

/**
 * Resolve budget data for the shelf
 * @param {object} config - App config
 * @returns {Promise<object|null>} Budget data
 */
async function resolveData(config) {
  try {
    // Import dependencies
    const { loadConfig, getStatePath } = await import('../utils/configLoader.js');
    const { readJsonFile } = await import('../utils/fileReader.js');
    
    const appConfig = loadConfig();
    const drivesPath = getStatePath(appConfig, 'drives.json');
    
    const data = readJsonFile(drivesPath);
    const drives = data?.drives || {};
    
    // Get budget from config
    const dailyLimit = appConfig.budget?.daily_limit || 50.00;
    const costPerTrigger = appConfig.budget?.cost_per_trigger || 2.50;
    
    // Calculate daily spend
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
    
    // Calculate projected monthly
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
    
    // Determine warning level
    let warningLevel = 'normal';
    let warningIcon = '✅';
    if (dailyPercent >= 90) {
      warningLevel = 'critical';
      warningIcon = '🔴';
    } else if (dailyPercent >= 75) {
      warningLevel = 'warning';
      warningIcon = '🟡';
    }
    
    // Count active and latent drives
    const activeDrives = Object.values(drives).filter(d => d.status !== 'latent' && !d.aspect_of).length;
    const latentDrives = Object.values(drives).filter(d => d.status === 'latent').length;
    
    return {
      title: `${warningIcon} Budget Status`,
      banner: true, // Indicates this should be a banner-style display
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
      items: [], // Banner shelf, no items
    };
  } catch (err) {
    console.error('BudgetTransparencyShelf error:', err);
    return null;
  }
}

export default {
  manifest,
  resolveData,
};
