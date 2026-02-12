# The Room — Emergence Dashboard

Dashboard for the Emergence agent architecture. A personal space reflecting the agent's inner state.

## Development

```bash
# Install dependencies
npm install

# Run development server (API + Vite)
npm run dev

# Run API only
npm run server

# Build for production
npm run build

# Preview production build
npm run preview
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| GET | /api/config | Agent configuration |
| GET | /api/drives | Drive states |
| POST | /api/drives/:name/satisfy | Satisfy a drive |
| GET | /api/sessions | Recent sessions |
| GET | /api/sessions/:filename | Session detail |
| GET | /api/identity/:file | Identity files (soul, self, aspirations, interests) |
| GET | /api/memory/stats | Memory statistics |
| GET | /api/dreams | Recent dreams |
| GET | /api/first-light | First Light progress |

## Configuration

The dashboard reads `emergence.json` from the workspace root. Supports comments (// and #).

## Architecture

- **Backend**: Express.js 5.x, reads state files on every request
- **Frontend**: React + Vite + TailwindCSS (coming in F020-F026)
- **State**: File-based (JSON + Markdown), no database

## Path Resolution

The Room server automatically resolves the correct state file paths from your `emergence.json` configuration:

1. **Primary**: Uses `getStatePath(config, 'drives.json')` from your `emergence.json` `paths.state` setting
2. **Fallback**: `EMERGENCE_STATE` environment variable (if set)
3. **Legacy**: `~/.openclaw/state/drives.json` (for backward compatibility)

**No manual configuration needed** - it reads your workspace structure automatically.

## Panels

The Room has **core panels** (built-in, all agents get them) and **custom panels** (agent-specific).

### Core Panels

These ship with Emergence and appear for every agent:

| Panel | Description |
|-------|-------------|
| Mirror | SELF.md and SOUL.md viewer |
| Memory | Full memory browser with search, categories, embedding stats |
| Journal | Session browser with drive filtering |
| Aspirations | Dreams and linked projects |
| Projects | Project status board |

### Adding Custom Panels

Custom panels let you extend your Room with agent-specific content. There are two approaches:

#### Approach 1: Data-only shelf (no code)

If you just need to display JSON data, create a shelf manifest and data file:

```bash
# Create shelf directory
mkdir -p ~/.openclaw/state/shelves/my-shelf

# Create manifest (shelf.json)
cat > ~/.openclaw/state/shelves/my-shelf/shelf.json << 'EOF'
{
  "id": "my-shelf",
  "name": "My Custom Panel",
  "icon": "🎯",
  "description": "What this panel shows",
  "version": "1.0",
  "renderer": "generic",
  "dataSource": {
    "type": "file",
    "path": "data.json"
  }
}
EOF

# Create data file
echo '{"items": ["one", "two"]}' > ~/.openclaw/state/shelves/my-shelf/data.json
```

The `generic` renderer will display your data automatically. The panel appears in the tab bar after the core panels.

#### Approach 2: Custom renderer (full control)

For rich UIs, create a React component:

1. **Create the component** in `room/src/components/shelves/custom/`:

```jsx
// MyPanelView.jsx
export default function MyPanelView({ data }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-text">My Panel</h2>
      {/* Your UI here — data comes from your shelf's API */}
    </div>
  );
}
```

2. **Register** in `room/src/components/shelves/ShelfRenderer.jsx`:

```jsx
import MyPanelView from './custom/MyPanelView';

const RENDERER_MAP = {
  // ... existing renderers
  'my-panel': MyPanelView,
};
```

3. **Create shelf manifest** with your renderer name:

```json
{
  "id": "my-panel",
  "name": "My Panel",
  "icon": "🎯",
  "renderer": "my-panel"
}
```

4. **Rebuild**: `cd room && npm run build`

#### Approach 3: Backend shelf (dynamic data)

For panels that compute data on-the-fly, create a builtin shelf in `room/server/shelves/builtins/`:

```javascript
// MyShelf.js
export const MyShelf = {
  manifest: {
    id: 'my-shelf',
    name: 'My Shelf',
    icon: '🎯',
    renderer: 'my-panel',
    // ...
  },
  async resolveData(config) {
    // Read files, query APIs, compute stats
    return { /* your data */ };
  },
};
```

Register it in `room/server/shelves/index.js`:
```javascript
import { MyShelf } from './builtins/MyShelf.js';
registry.registerBuiltin(MyShelf);
```

### Panel Ordering

- **Core panels** always appear first in their fixed order
- **Custom panels** are auto-discovered and appended after core panels
- Custom shelves that duplicate a core panel ID are skipped

### Tips

- Custom components in `shelves/custom/` are `.gitignore`d — they stay local
- Data file changes are picked up automatically (no rebuild needed)
- Component changes require `npm run build`
- Use `curl http://localhost:8800/api/shelves` to verify your shelf is registered
- Shelf data is served at `/api/shelves/<shelf-id>`
