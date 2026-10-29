import { defineConfig } from 'vitest/config';

// Frontend unit tests run in jsdom so the text-node DOM helpers (dom.js) execute exactly as in
// the browser. Kept separate from the Python API suite; see tests/frontend/.
export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['tests/frontend/**/*.test.js'],
    globals: false,
  },
});
