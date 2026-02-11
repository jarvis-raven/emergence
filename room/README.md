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

## Custom Shelves

When adding custom shelves to your Room:

1. Create shelf data files in `~/.emergence/state/shelves/your-shelf/`
2. Add shelf component in `room/src/components/shelves/YourShelfView.jsx`
3. Register in `room/src/components/shelves/ShelfRenderer.jsx`
4. **Rebuild frontend**: `npm run build` (required for changes to appear)

The backend will serve your shelf data automatically, but the frontend needs rebuilding to include the new component.
