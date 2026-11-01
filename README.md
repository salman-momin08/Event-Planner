# Event Planning Assistant

AI-assisted planner for weddings, birthdays and community events: events, budgets and expenses, tasks with dependencies, template timelines, vendors, export, and an optional AI assistant that drafts plans you review before applying. Core planning works without AI.

```
backend/                 FastAPI app (backend/app), requirements*.txt, .env.example
frontend/                framework-free accessible HTML/JS/CSS, served by the backend
tests/                   pytest, Vitest, and Playwright suites (excluded from the container image)
Dockerfile               non-root production image containing only backend/app and frontend
compose.production.yml   hardened single-instance production service definition
docker-compose.yml       optional local PostgreSQL 16 service bound to 127.0.0.1
```

- **Backend:** Python 3.12+, FastAPI, Pydantic, PostgreSQL (`DATABASE_URL`) or SQLite (`DATABASE_PATH`, WAL mode).
- **AI (optional):** Gemini, OpenAI-compatible endpoints, or Hugging Face models orchestrated by LangGraph with input/image guardrails and schema validation before persistence. Amounts and dates are computed deterministically by the application.
- **Frontend:** vanilla ES modules; FastAPI serves `frontend/` directly at `/` in production, while Vite is used only for local frontend development.

## Local Development
Requires Python 3.12+ and Node.js `^20.19.0 || ^22.13.0 || >=24`.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
npm install
copy backend\.env.example backend\.env   # leave DATABASE_URL and AI keys empty for local SQLite without AI
cd backend
..\.venv\Scripts\python -m app           # http://127.0.0.1:3000
```

## Release Checks

```powershell
.\.venv\Scripts\python -m pytest          # Python suite (API, AI workflow, static frontend checks)
npm run test:unit                         # Vitest + jsdom: dom.js helpers, XSS safety, form validation
npm run test:a11y                         # Playwright + axe-core: WCAG 2.2 AA on the real rendered UI
npm run lint && npm run format            # ESLint + Prettier (frontend)
npm run audit:backend                     # pip-audit on backend/requirements.txt
npm run audit                             # npm audit on frontend tooling
```

`test:a11y` installs browsers once with `npx playwright install chromium` and boots the backend itself
with an isolated temporary SQLite database. Set `PLANNER_TEST_POSTGRES_URL` to a disposable PostgreSQL
database to run the PostgreSQL integration smoke test, and set `RUN_LIVE_AI_TESTS=1` with provider
credentials to run the opt-in live model test in `tests/test_ai_live.py`.

## Enable the AI assistant (Gemini Free Tier or OpenAI)
1. **Google Gemini (Free Tier for testing)** — Create a free API key in Google AI Studio (`https://aistudio.google.com/apikey`), then set in `backend/.env`:
   ```ini
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_gemini_api_key_here
   # Optional (defaults to gemini-3-flash-preview):
   # AI_MODEL=gemini-3-flash-preview
   ```
2. **OpenAI (or Production / OpenAI-compatible endpoints)** — Set in `backend/.env`:
   ```ini
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   # Optional (defaults to gpt-4o-mini and https://api.openai.com/v1):
   # AI_MODEL=gpt-4o-mini
   # AI_BASE_URL=https://api.openai.com/v1
   ```
3. Restart the backend. `GET /api/v1/ai/status` reports `{"available": true}` and the **AI assistant** tab becomes active. To switch from free-tier testing to production keys later, simply update `AI_PROVIDER`, `GEMINI_API_KEY` / `OPENAI_API_KEY`, and `AI_MODEL` in your environment variables—no code changes required.

Plan generation sends only event type, date, attendance, location, budget, your request text, and prior plan drafts; decor analysis also sends the selected venue/lighting metadata and optional compressed venue photo; invitation drafting sends event title, date, location, attendance, current card copy, and your wording request. Account emails, passwords, vendor contacts, guest lists, and expense records are never sent. LangChain/LangSmith tracing is force-disabled. Never commit `.env`.

## Production Deployment
1. **Configure secrets and storage** outside Git:
   - `APP_ENV=production`
   - `COOKIE_SECURE=true` (required in production; startup fails if disabled)
   - `SECURITY_LOG_KEY=<random secret>` so pseudonymized audit-log IP hashes stay consistent across restarts
   - `DATABASE_URL=postgresql://...` for managed PostgreSQL (remote hosts default to `sslmode=require`) or mount a persistent volume at `/app/backend/data` for single-node SQLite
   - `TRUST_PROXY=true` only when running behind a reverse proxy you control that overwrites `X-Forwarded-For`
2. **Build and run the production container** (excludes `tests/`, `node_modules/`, `.venv/`, and `.env` via `.dockerignore`):
   ```sh
   docker compose -f compose.production.yml up -d --build
   ```
3. **Operational constraints:**
   - Terminate HTTPS at your reverse proxy or load balancer in front of `127.0.0.1:3000`
   - Run a single container/worker unless rate limiting and database connection pooling are moved to shared external infrastructure, because rate-limit buckets are in-process memory and the PostgreSQL adapter uses a single synchronous connection per process
   - Configure automated backups and restore verification for your PostgreSQL database or `/app/backend/data` volume before going live
