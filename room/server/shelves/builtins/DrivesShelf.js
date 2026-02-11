/**
 * DrivesShelf — Built-in shelf for drives with aspect support
 * 
 * Shows all drives with their aspects, graduation candidates, and status
 * Enhanced for v2 consolidation plan
 */

const manifest = {
  id: 'drives',
  name: 'Drives',
  version: '2.0.0',
  description: 'Drive pressure, aspects, and graduation candidates',
  icon: '🧠',
  priority: 60,
  dataSource: {
    type: 'custom',
    refreshInterval: 30000,
  },
};

/**
 * Format elapsed time since last trigger
 * @param {string} lastTriggered - ISO timestamp
 * @returns {string} Human readable elapsed time
 */
function formatElapsed(lastTriggered) {
  if (!lastTriggered) return 'Never';
  
  const now = new Date();
  const then = new Date(lastTriggered);
  const hours = (now - then) / (1000 * 60 * 60);
  
  if (hours < 1) return '< 1h';
  if (hours < 24) return `${Math.floor(hours)}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

/**
 * Resolve drives data for the shelf
 * @param {object} config - App config
 * @returns {Promise<object|null>} Drives data
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
    
    // Get triggered drives
    const triggeredDrives = data?.triggered_drives || [];
    const triggeredSet = new Set(triggeredDrives.map(d => d.toUpperCase()));
    
    // Group drives by category
    const categories = {
      core: [],
      discovered: [],
      post_emergence: [],
    };
    
    for (const [name, drive] of Object.values(drives).entries()) {
      const category = drive.category || 'discovered';
      const aspects = drive.aspects || [];
      const aspectCount = aspects.length;
      
      // Check for graduation candidates
      const graduationCandidates = [];
      if (drive.aspect_details) {
        for (const aspect of drive.aspect_details) {
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
          
          if (couldGraduate) {
            graduationCandidates.push(aspect.name);
          }
        }
      }
      
      // Calculate pressure percentage
      const pressurePct = drive.threshold > 0 
        ? Math.min(100, Math.round((drive.pressure / drive.threshold) * 100))
        : 0;
      
      // Determine status icon
      let statusIcon = '▫️';
      if (triggeredSet.has(name.toUpperCase())) {
        statusIcon = '⚡';
      } else if (pressurePct >= 80) {
        statusIcon = '🔶';
      } else if (pressurePct >= 50) {
        statusIcon = '🔸';
      }
      
      const driveItem = {
        id: name,
        title: `${statusIcon} ${name}`,
        subtitle: drive.description || '',
        progress: pressurePct,
        progress_label: `${Math.floor(drive.pressure || 0)}/${drive.threshold || 20}`,
        metadata: {
          rate: `${drive.rate_per_hour || 0}/hr`,
          last_triggered: formatElapsed(drive.last_triggered),
          aspect_count: aspectCount,
          aspects: aspects,
          has_aspects: aspectCount > 0,
          max_aspects_reached: aspectCount >= 5,
          category: category,
          is_triggered: triggeredSet.has(name.toUpperCase()),
          graduation_candidates: graduationCandidates,
          has_graduation_candidates: graduationCandidates.length > 0,
        },
        actions: [
          {
            label: 'Satisfy',
            command: `drives satisfy ${name}`,
            type: 'primary',
            visible: triggeredSet.has(name.toUpperCase()),
          },
          {
            label: 'Manage Aspects',
            command: `drives aspects ${name}`,
            type: 'secondary',
            visible: aspectCount > 0,
          },
        ].filter(a => a.visible !== false),
      };
      
      // Group by category
      if (category === 'core') {
        categories.core.push(driveItem);
      } else if (category === 'post_emergence') {
        categories.post_emergence.push(driveItem);
      } else {
        categories.discovered.push(driveItem);
      }
    }
    
    // Build items list with category headers
    const items = [];
    
    if (categories.core.length > 0) {
      items.push(...categories.core);
    }
    
    if (categories.post_emergence.length > 0) {
      items.push(...categories.post_emergence);
    }
    
    if (categories.discovered.length > 0) {
      items.push(...categories.discovered);
    }
    
    // Count stats
    const totalDrives = Object.keys(drives).length;
    const activeAspects = Object.values(drives).reduce((sum, d) => sum + (d.aspects?.length || 0), 0);
    const triggeredCount = triggeredSet.size;
    
    return {
      title: '🧠 Drives',
      count: totalDrives,
      triggered_count: triggeredCount,
      aspect_count: activeAspects,
      categories: categories,
      items: items,
      last_updated: data?.last_updated || new Date().toISOString(),
    };
  } catch (err) {
    console.error('DrivesShelf error:', err);
    return null;
  }
}

export default {
  manifest,
  resolveData,
};
