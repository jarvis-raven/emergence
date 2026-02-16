# Shelf Migration Safety Design

## Problem

When users upgrade Emergence via `pip install --upgrade emergence-ai`, the `room/server/shelves/index.js` file gets replaced, losing any custom builtin shelf registrations.

**Current behavior:**

- Builtins hardcoded in `index.js` → replaced on upgrade
- Custom shelves in `~/.openclaw/state/shelves/` → safe from upgrades ✅
- Custom builtin registrations → lost on upgrade ❌

## Solution: Separate User Config from Package Code

### Approach 1: User Shelf Config File (Recommended)

**Create:** `~/.openclaw/config/shelves.json`

```json
{
  "builtins": {
    "memory": { "enabled": true, "priority": 90 },
    "aspirations": { "enabled": true, "priority": 85 },
    "budget": { "enabled": true, "priority": 95 },
    "drives": { "enabled": true, "priority": 100 },
    "pending-reviews": { "enabled": true, "priority": 80 },
    "latent-drives": { "enabled": true, "priority": 75 }
  },
  "custom": {
    "library": { "enabled": true, "priority": 88 }
  }
}
```

**Updated `index.js` logic:**

```javascript
export async function initializeShelves(config) {
  const statePath = getStatePath(config, '');
  const registry = new ShelfRegistry(statePath);

  // Load user preferences
  const userConfig = loadUserShelfConfig();

  // Register built-in shelves (always available, but respect user enable/disable)
  const builtinDefs = {
    budget: BudgetTransparencyShelf,
    drives: DrivesShelf,
    'pending-reviews': PendingReviewsShelf,
    'latent-drives': LatentDrivesShelf,
    memory: MemoryShelf,
    aspirations: AspirationsShelf,
  };

  for (const [id, def] of Object.entries(builtinDefs)) {
    const userPref = userConfig.builtins?.[id];
    if (userPref?.enabled !== false) {
      // Apply user priority override if set
      if (userPref?.priority) {
        def.manifest.priority = userPref.priority;
      }
      registry.registerBuiltin(def);
    }
  }

  // Discover custom shelves from statePath/shelves/
  await registry.discover();

  // Apply user preferences to custom shelves
  for (const [id, pref] of Object.entries(userConfig.custom || {})) {
    if (pref.enabled === false) {
      registry.disableShelf(id);
    }
    if (pref.priority) {
      registry.setShelfPriority(id, pref.priority);
    }
  }

  const all = registry.getAll();
  const builtinCount = all.filter((s) => s.isBuiltin).length;
  const customCount = all.filter((s) => !s.isBuiltin).length;
  console.log(`📚 Shelves: ${builtinCount} built-in, ${customCount} custom discovered`);

  return registry;
}

function loadUserShelfConfig() {
  const configPath = path.join(os.homedir(), '.openclaw', 'config', 'shelves.json');
  if (!existsSync(configPath)) {
    return { builtins: {}, custom: {} };
  }
  try {
    return JSON.parse(readFileSync(configPath, 'utf-8'));
  } catch (err) {
    console.error('Failed to load user shelf config:', err.message);
    return { builtins: {}, custom: {} };
  }
}
```

### Approach 2: Builtin Manifest File

**Create:** `room/server/shelves/builtins.json` (shipped with package)

```json
[
  { "id": "budget", "module": "./builtins/BudgetTransparencyShelf.js", "priority": 95 },
  { "id": "drives", "module": "./builtins/DrivesShelf.js", "priority": 100 },
  { "id": "pending-reviews", "module": "./builtins/PendingReviewsShelf.js", "priority": 80 },
  { "id": "latent-drives", "module": "./builtins/LatentDrivesShelf.js", "priority": 75 },
  { "id": "memory", "module": "./builtins/MemoryShelf.js", "priority": 90 },
  { "id": "aspirations", "module": "./builtins/AspirationsShelf.js", "priority": 85 }
]
```

**Updated `index.js`:**

```javascript
export async function initializeShelves(config) {
  const statePath = getStatePath(config, '');
  const registry = new ShelfRegistry(statePath);

  // Load builtin manifest
  const builtinsPath = new URL('./builtins.json', import.meta.url);
  const builtins = JSON.parse(readFileSync(builtinsPath, 'utf-8'));

  // Dynamically import and register
  for (const def of builtins) {
    try {
      const module = await import(def.module);
      const ShelfDef = module.default || module[Object.keys(module)[0]];
      registry.registerBuiltin(ShelfDef);
    } catch (err) {
      console.error(`Failed to load builtin shelf ${def.id}:`, err.message);
    }
  }

  await registry.discover();

  return registry;
}
```

## Recommendation

**Use Approach 1** for these reasons:

1. **User control:** Users can enable/disable builtins without touching package code
2. **Priority override:** Users can reorder shelves
3. **Survives upgrades:** User config in `~/.openclaw/config/` is never touched by pip
4. **Backwards compatible:** Missing config file = default behavior
5. **Migration path:** `emergence update` can create initial config from current state

## Implementation Checklist

- [ ] Add `ShelfRegistry.disableShelf(id)` method
- [ ] Add `ShelfRegistry.setShelfPriority(id, priority)` method
- [ ] Create `loadUserShelfConfig()` helper
- [ ] Update `initializeShelves()` to respect user config
- [ ] Add `emergence shelves` CLI command:
  - `emergence shelves list` — show all available shelves
  - `emergence shelves enable <id>` — enable a shelf
  - `emergence shelves disable <id>` — disable a shelf
  - `emergence shelves priority <id> <value>` — set priority
- [ ] Create default `~/.openclaw/config/shelves.json` during `emerge init`
- [ ] Document in getting-started.md

## Migration Strategy for v0.2.2

When users upgrade to v0.2.2:

1. **Detect first run:** Check if `~/.openclaw/config/shelves.json` exists
2. **If missing:** Generate from current state (all builtins enabled)
3. **Log:** "Created shelf config at ~/.openclaw/config/shelves.json"
4. **Recommend:** "Run `emergence shelves list` to customize"

This ensures:

- Existing users get seamless upgrade
- New users get config file from `emerge init`
- Custom shelves never break on upgrade
