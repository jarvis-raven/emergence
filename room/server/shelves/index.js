/**
 * Shelves Index — Initialize and export the ShelfRegistry
 */

import { ShelfRegistry } from './ShelfRegistry.js';
import { MemoryShelf } from './builtins/MemoryShelf.js';
import { NautilusShelf } from './builtins/NautilusShelf.js';
import AspirationsShelf from './builtins/AspirationsShelf.js';
import { BudgetTransparencyShelf } from './builtins/BudgetTransparencyShelf.js';
import { PendingReviewsShelf } from './builtins/PendingReviewsShelf.js';
import { LatentDrivesShelf } from './builtins/LatentDrivesShelf.js';
import { DrivesShelf } from './builtins/DrivesShelf.js';
import { getStatePath } from '../utils/configLoader.js';

/**
 * Initialize the shelf registry
 * @param {object} config - Loaded app config
 * @returns {Promise<ShelfRegistry>} Configured registry
 */
export async function initializeShelves(config) {
  const statePath = getStatePath(config, '');
  const registry = new ShelfRegistry(statePath);
  
  // Load user preferences
  const userConfig = registry.loadUserConfig();
  
  // Register built-in shelves (order matters for default priority)
  registry.registerBuiltin(BudgetTransparencyShelf);
  registry.registerBuiltin(DrivesShelf);
  registry.registerBuiltin(PendingReviewsShelf);
  registry.registerBuiltin(LatentDrivesShelf);
  registry.registerBuiltin(MemoryShelf);
  registry.registerBuiltin(NautilusShelf);
  registry.registerBuiltin(AspirationsShelf);
  
  // Discover custom shelves from filesystem
  await registry.discover();
  
  // Apply user preferences (enable/disable, priority overrides)
  registry.applyUserPreferences(userConfig);
  
  const all = registry.getAll(true); // Include disabled for counting
  const active = all.filter(s => s.status !== 'disabled');
  const builtinCount = active.filter(s => s.isBuiltin).length;
  const customCount = active.filter(s => !s.isBuiltin).length;
  const disabledCount = all.length - active.length;
  
  console.log(`📚 Shelves: ${builtinCount} built-in, ${customCount} custom discovered` + 
              (disabledCount > 0 ? `, ${disabledCount} disabled` : ''));
  
  return registry;
}
