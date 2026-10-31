# Event Planning Assistant

AI-assisted planner for weddings, birthdays and community events: events, budgets and expenses, tasks with dependencies, template timelines, vendors, export, and an optional AI assistant that drafts plans you review before applying. Core planning works without AI.

```
backend/     FastAPI app (backend/app), requirements*.txt, .env.example
frontend/    framework-free accessible HTML/JS/CSS, served by the backend
tests/       pytest suite for both (API, AI workflow, static frontend checks)
.agents/     project documentation
```

- **Backend:** Python, FastAPI, Pydantic, SQLite (stdlib).
- **AI:** Hugging Face models through LangChain (`langchain-huggingface`), orchestrated by a LangGraph workflow that validates and self-repairs the model's JSON before anything is stored. Amounts and dates are always computed by the app.
- **Frontend:** vanilla ES modules; the backend serves `frontend/` at `/`, so no separate dev server or build step is needed.

**Status:** first MVP delivery; not release-ready (see [.agents/progress/current-state.md](.agents/progress/current-state.md)). Documentation: [.agents/](.agents/index.md).

## Run
Requires Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
copy backend\.env.example backend\.env   # then edit; leave HF_TOKEN empty to run without AI
cd backend
..\.venv\Scripts\python -m app           # http://127.0.0.1:3000
cd ..
.\.venv\Scripts\python -m pytest         # backend API + AI workflow + static checks
```

## Tests and checks

```powershell
.\.venv\Scripts\python -m pytest          # Python suite (API, AI workflow, static frontend checks)
npm run test:unit                         # Vitest + jsdom: dom.js helpers, XSS safety, form validation
npm run test:a11y                         # Playwright + axe-core: WCAG 2.2 AA on the real rendered UI
npm run lint && npm run format            # ESLint + Prettier (frontend)
pip-audit -r backend\requirements.txt     # backend dependency audit
npm audit                                 # frontend dependency audit
```

`test:a11y` installs browsers once with `npx playwright install chromium` and boots the backend itself
with an ephemeral SQLite database. Set `HF_TOKEN` (+ `HF_MODEL_ID`) to also run the opt-in live-model
test in `tests/test_ai_live.py`, which is skipped otherwise.

## Enable the AI assistant (Gemini Free Tier or OpenAI)
1. **Google Gemini (Free Tier for testing)** — Create a free API key in Google AI Studio (`https://aistudio.google.com/apikey`), then set in `backend/.env`:
   ```ini
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_gemini_api_key_here
   # Optional (defaults to gemini-2.5-flash):
   # AI_MODEL=gemini-2.5-flash
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

Event data (type, date, attendance, location, budget, your request text) is sent to the configured provider; names, emails, notes, vendors and expenses are not. LangChain/LangSmith tracing is force-disabled. See [secrets-and-configuration](.agents/security/secrets-and-configuration.md). Never commit `.env`.
