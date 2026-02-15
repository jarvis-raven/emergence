import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isDev = mode === 'development';
  const isProd = mode === 'production';

  return {
    plugins: [react()],
    
    // Environment variables exposed to the client
    define: {
      __DEV_MODE__: JSON.stringify(isDev),
      __PROD_MODE__: JSON.stringify(isProd),
    },

    server: {
      port: 3000,
      host: '127.0.0.1',
      allowedHosts: ['jarviss-mac-mini.tail869e96.ts.net'],
      proxy: {
        '/api': {
          target: process.env.API_URL || 'http://localhost:8801',
          changeOrigin: true,
        },
      },
    },

    preview: {
      port: isProd ? 8800 : 3000,
      host: '127.0.0.1',
      proxy: {
        '/api': {
          target: process.env.API_URL || 'http://localhost:8801',
          changeOrigin: true,
        },
      },
    },

    build: {
      outDir: 'dist',
      rollupOptions: {
        input: {
          main: './index.html',
        },
      },
    },
  };
});
