/**
 * Shelves Index — Initialize and export the ShelfRegistry
 */

import { ShelfRegistry } from './ShelfRegistry.js';
import { MemoryShelf } from './builtins/MemoryShelf.js';
import AspirationsShelf from './builtins/AspirationsShelf.js';
import BudgetTransparencyShelf from './builtins/BudgetTransparencyShelf.js';
import PendingReviewsShelf from './builtins/PendingReviewsShelf.js';
import LatentDrivesShelf from './builtins/LatentDrivesShelf.js';
import DrivesShelf from './builtins/DrivesShelf.js';
import { getStatePath } from '../utils/configLoader.js';

/**
 * Initialize the shelf registry
 * @param {object} config - Loaded app config
 * @returns {Promise<ShelfRegistry>} Configured registry
 */
export async function initializeShelves(config) {
  const statePath = getStatePath(config, '');
  const registry = new ShelfRegistry(statePath);
  
  // Register built-in shelves (order matters for priority)
  registry.registerBuiltin(BudgetTransparencyShelf);
  registry.registerBuiltin(DrivesShelf);
  registry.registerBuiltin(PendingReviewsShelf);
  registry.registerBuiltin(LatentDrivesShelf);
  registry.registerBuiltin(MemoryShelf);
  registry.registerBuiltin(AspirationsShelf);
  
  await registry.discover();
  
  const all = registry.getAll();
  const builtinCount = all.filter(s => s.isBuiltin).length;
  const customCount = all.filter(s => !s.isBuiltin).length;
  console.log(`📚 Shelves: ${builtinCount} built-in, ${customCount} custom discovered`);
  
  return registry;
}
