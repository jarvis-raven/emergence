/**
 * The Room — Dashboard API Server
 * 
 * Express.js server that reads Emergence state files and serves them as JSON.
 * Files are the source of truth — re-read on every request.
 * 
 * Supports both HTTP and HTTPS (HTTPS preferred with self-signed certs).
 * 
 * WebSocket Support:
 * - Watches drives state file for changes and broadcasts to connected clients
 * - Message format: {"type": "drives_update", "data": <drives.json contents>}
 */

import express, { Router } from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { createServer as createHttpsServer } from 'https';
import { readFileSync, existsSync, watchFile, readFile } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { WebSocketServer } from 'ws';
import os from 'os';

// Import routes
import configRoutes from './routes/config.js';
import drivesRoutes from './routes/drives.js';
import sessionsRoutes from './routes/sessions.js';
import identityRoutes from './routes/identity.js';
import memoryRoutes from './routes/memory.js';
import dreamsRoutes from './routes/dreams.js';
import firstLightRoutes from './routes/first-light.js';
import budgetRoutes from './routes/budget.js';
import createShelvesRouter from './routes/shelves.js';

// Import utils
import { loadConfig, getStatePath } from './utils/configLoader.js';
import { ensureCertificates } from './utils/certGen.js';
import { initializeShelves } from './shelves/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Initialize Express app
const app = express();

// Load configuration
const config = loadConfig();
const PORT = process.env.PORT || config.room?.port || 8765;
const HOST = process.env.HOST || config.room?.host || '127.0.0.1';
const USE_HTTPS = process.env.HTTPS !== 'false' && config.room?.https !== false;

// SSL directory
const SSL_DIR = join(__dirname, '..', 'ssl');

// WebSocket clients
const wsClients = new Set();

// Get drives state file path
const drivesStatePath = process.env.EMERGENCE_STATE 
  ? join(process.env.EMERGENCE_STATE, 'drives.json')
  : join(os.homedir(), '.openclaw/state', 'drives.json');

// Middleware
app.use(cors({
  origin: [
    'http://localhost:3000',
    'https://localhost:3000',
    'http://localhost:5173',
    'https://localhost:5173',
    'http://127.0.0.1:3000',
    'https://127.0.0.1:3000',
    'http://127.0.0.1:5173',
    'https://127.0.0.1:5173',
  ],
  credentials: true,
}));

app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    agent: config.agent?.name || 'My Agent',
    websocketClients: wsClients.size,
  });
});

// Mount API routes
app.use('/api/config', configRoutes);
app.use('/api/drives', drivesRoutes);
app.use('/api/sessions', sessionsRoutes);
app.use('/api/identity', identityRoutes);
app.use('/api/memory', memoryRoutes);
app.use('/api/dreams', dreamsRoutes);
app.use('/api/first-light', firstLightRoutes);
app.use('/api/budget', budgetRoutes);

// Shelves (convention-based discovery) — initialized async before server start
// Placeholder mounted synchronously, replaced in startServer()
let shelvesRouter = Router();
app.use('/api/shelves', (req, res, next) => shelvesRouter(req, res, next));

// Note: Express 5 doesn't support wildcard catch-all easily.
// Unknown API routes will fall through to the SPA handler or 404 naturally.

// Serve static files in production
const STATIC_DIR = join(__dirname, '..', 'dist');
if (existsSync(STATIC_DIR)) {
  app.use(express.static(STATIC_DIR));
  // SPA fallback handled by Vite dev server in development
  // In production, configure reverse proxy for SPA routing
}

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

/**
 * Broadcast a message to all connected WebSocket clients
 * @param {object} message - Message to broadcast
 */
function broadcastToClients(message) {
  const data = JSON.stringify(message);
  wsClients.forEach((ws) => {
    if (ws.readyState === 1) { // WebSocket.OPEN
      ws.send(data);
    }
  });
}

/**
 * Read and broadcast the current drives state
 */
function broadcastDrivesState() {
  readFile(drivesStatePath, 'utf-8', (err, content) => {
    if (err) {
      console.error('Failed to read drives state:', err.message);
      return;
    }
    
    try {
      const data = JSON.parse(content);
      broadcastToClients({
        type: 'drives_update',
        data: data,
      });
      console.log(`[WebSocket] Broadcasted drives update to ${wsClients.size} client(s)`);
    } catch (parseErr) {
      console.error('Failed to parse drives state:', parseErr.message);
    }
  });
}

/**
 * Setup WebSocket server
 * @param {http.Server} server - HTTP/HTTPS server instance
 */
function setupWebSocket(server) {
  const wss = new WebSocketServer({ server });

  wss.on('connection', (ws, req) => {
    const clientId = `${req.socket.remoteAddress}:${req.socket.remotePort}`;
    console.log(`[WebSocket] Client connected: ${clientId}`);
    
    wsClients.add(ws);

    // Send initial drives state to the new client
    readFile(drivesStatePath, 'utf-8', (err, content) => {
      if (!err) {
        try {
          const data = JSON.parse(content);
          ws.send(JSON.stringify({
            type: 'drives_update',
            data: data,
          }));
        } catch (parseErr) {
          console.error('Failed to parse drives state for new client:', parseErr.message);
        }
      }
    });

    // Handle client disconnect
    ws.on('close', () => {
      console.log(`[WebSocket] Client disconnected: ${clientId}`);
      wsClients.delete(ws);
    });

    // Handle errors
    ws.on('error', (err) => {
      console.error(`[WebSocket] Error from ${clientId}:`, err.message);
      wsClients.delete(ws);
    });

    // Handle ping/pong for connection keepalive
    ws.isAlive = true;
    ws.on('pong', () => {
      ws.isAlive = true;
    });
  });

  // Periodic heartbeat to detect dead connections
  const heartbeatInterval = setInterval(() => {
    wsClients.forEach((ws) => {
      if (!ws.isAlive) {
        ws.terminate();
        wsClients.delete(ws);
        return;
      }
      ws.isAlive = false;
      ws.ping();
    });
  }, 30000);

  wss.on('close', () => {
    clearInterval(heartbeatInterval);
  });

  console.log('[WebSocket] Server initialized');
}

/**
 * Watch drives state file for changes
 */
function watchDrivesState() {
  if (!existsSync(drivesStatePath)) {
    console.warn(`[Watch] Drives state file not found: ${drivesStatePath}`);
    // Try to resolve through config as fallback
    try {
      const configPath = getStatePath(config, 'drives.json');
      if (existsSync(configPath)) {
        console.log(`[Watch] Found drives state at: ${configPath}`);
        setupWatch(configPath);
        return;
      }
    } catch (err) {
      // Fall through to error
    }
    console.error('[Watch] Unable to find drives state file to watch');
    return;
  }
  
  setupWatch(drivesStatePath);
}

function setupWatch(filePath) {
  console.log(`[Watch] Watching drives state: ${filePath}`);
  
  // Use watchFile (stat-polling) instead of watch (inode-based) because
  // the drives engine writes atomically via temp file + rename.
  // fs.watch loses track of the file after rename on macOS.
  watchFile(filePath, { interval: 1000 }, (curr, prev) => {
    if (curr.mtimeMs !== prev.mtimeMs) {
      broadcastDrivesState();
    }
  });
}

// Start server
async function startServer() {
  try {
    // Initialize shelf discovery
    const shelfRegistry = await initializeShelves(config);
    shelvesRouter = createShelvesRouter(shelfRegistry);

    if (USE_HTTPS) {
      // Ensure certificates exist
      const certs = ensureCertificates(SSL_DIR);
      
      if (certs.error) {
        console.warn('⚠️  HTTPS certificates not available, falling back to HTTP');
        console.warn('   Run with OpenSSL available to generate certificates');
        
        // Fallback to HTTP
        const server = createServer(app);
        setupWebSocket(server);
        watchDrivesState();
        
        server.listen(PORT, HOST, () => {
          console.log(`🌙 The Room API running on http://0.0.0.0:${PORT}`);
          console.log(`   Agent: ${config.agent?.name || 'My Agent'}`);
          console.log(`   Config: ${config._configPath || 'defaults'}`);
          console.log(`   WebSocket: ws://0.0.0.0:${PORT}`);
        });
        return;
      }
      
      // Read certificates
      const key = readFileSync(certs.keyPath);
      const cert = readFileSync(certs.certPath);
      
      const server = createHttpsServer({ key, cert }, app);
      setupWebSocket(server);
      watchDrivesState();
      
      server.listen(PORT, HOST, () => {
        console.log(`🌙 The Room API running on https://0.0.0.0:${PORT}`);
        console.log(`   Agent: ${config.agent?.name || 'My Agent'}`);
        console.log(`   Config: ${config._configPath || 'defaults'}`);
        console.log(`   Note: Self-signed certificate — expect browser warnings`);
        console.log(`   WebSocket: wss://0.0.0.0:${PORT}`);
      });
    } else {
      // HTTP only
      const server = createServer(app);
      setupWebSocket(server);
      watchDrivesState();
      
      server.listen(PORT, HOST, () => {
        console.log(`🌙 The Room API running on http://0.0.0.0:${PORT}`);
        console.log(`   Agent: ${config.agent?.name || 'My Agent'}`);
        console.log(`   Config: ${config._configPath || 'defaults'}`);
        console.log(`   WebSocket: ws://0.0.0.0:${PORT}`);
      });
    }
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

startServer();
