import { defineConfig } from 'vite';

// Frontend dev server. Runs independently from the backend and proxies API calls to it,
// so the browser still sees a single same-origin host (keeps cookies + the CSRF Origin/Host check happy).
// In production the FastAPI backend serves frontend/ directly; this config is dev-only.
export default defineConfig({
  root: 'frontend',
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // changeOrigin:false keeps the Host header as the dev-server host so backend's Origin==Host check passes.
      '/api': { target: 'http://127.0.0.1:3000', changeOrigin: false },
      '/healthz': { target: 'http://127.0.0.1:3000', changeOrigin: false },
    },
  },
});
