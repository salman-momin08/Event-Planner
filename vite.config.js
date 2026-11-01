import { defineConfig } from 'vite';

// Frontend dev server. Runs independently from the backend and proxies API calls to it,
// so the browser still sees a single same-origin host (keeps cookies + the CSRF Origin/Host check happy).
// In production the FastAPI backend serves frontend/ directly; this config is dev-only.
const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:3000';

export default defineConfig({
  root: 'frontend',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: false,
    headers: {
      'Cache-Control': 'no-store',
    },
    proxy: {
      // changeOrigin:false keeps the Host header as the dev-server host so backend's Origin==Host check passes.
      '/api/': { target: backendUrl, changeOrigin: false },
      '/healthz': { target: backendUrl, changeOrigin: false },
    },
  },
});
