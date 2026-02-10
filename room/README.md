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
