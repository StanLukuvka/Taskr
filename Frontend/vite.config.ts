/// <reference types="vitest/config" />
import path from 'node:path';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv, type Plugin, type ViteDevServer } from 'vite';

/**
 * Serve index.html for direct browser navigations to client-side routes
 * before Vite's proxy middleware intercepts the request as an API call.
 */
function spaFallbackPlugin(): Plugin {
  return {
    name: 'spa-fallback',
    configureServer(server: ViteDevServer) {
      server.middlewares.use((req, _res, next) => {
        const accept = req.headers?.accept ?? '';
        if (
          typeof accept === 'string' &&
          accept.includes('text/html') &&
          req.url &&
          !req.url.startsWith('/@') &&
          !req.url.startsWith('/src/') &&
          !req.url.startsWith('/assets/') &&
          !req.url.startsWith('/node_modules/') &&
          !req.url.match(/\.(js|css|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot|json|map)$/i)
        ) {
          req.url = '/index.html';
        }
        next();
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const port = Number(env.VITE_PORT ?? 9112);
  const apiBase = env.VITE_API_BASE?.replace(/\/$/, '') ?? 'http://127.0.0.1:9113';
  const apiHost = apiBase;

  return {
    plugins: [react(), tailwindcss(), spaFallbackPlugin()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/tests/setup.ts'],
      css: false,
      include: ['src/**/*.test.{ts,tsx}'],
      pool: 'forks',
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
    server: {
      port,
      proxy: {
        '/runs': { target: apiHost, changeOrigin: true },
        '/flows': { target: apiHost, changeOrigin: true },
        '/bindings': { target: apiHost, changeOrigin: true },
        '/node-states': { target: apiHost, changeOrigin: true },
        '/flow_versions': { target: apiHost, changeOrigin: true },
        '/flow_nodes': { target: apiHost, changeOrigin: true },
      },
    },
    appType: 'spa', 
  };
});
