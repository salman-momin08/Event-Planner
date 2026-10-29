import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { rmSync } from 'node:fs';

// Ephemeral SQLite file so the a11y run never touches real data and always starts empty.
const DB_PATH = join(tmpdir(), 'planner-a11y.db');
for (const suffix of ['', '-wal', '-shm']) {
  rmSync(DB_PATH + suffix, { force: true });
}

const PORT = 3100;

export default defineConfig({
  testDir: 'tests/a11y',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
  },
  webServer: {
    command: '..\\.venv\\Scripts\\python -m app',
    cwd: 'backend',
    url: `http://127.0.0.1:${PORT}/healthz`,
    reuseExistingServer: true,
    timeout: 300_000,
    env: {
      HOST: '127.0.0.1',
      PORT: String(PORT),
      APP_ENV: 'development',
      COOKIE_SECURE: 'false',
      DATABASE_PATH: DB_PATH,
    },
  },
});
