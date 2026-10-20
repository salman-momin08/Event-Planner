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
.\.venv\Scripts\python -m pytest         # run from the repository root
```

## Enable the AI assistant
1. Create a Hugging Face access token (read / Inference Providers permission).
2. In `backend/.env` set `HF_TOKEN` and `HF_MODEL_ID` (a chat/instruct model you can call through Inference Providers), or set `HF_ENDPOINT_URL` for a dedicated endpoint / self-hosted TGI server.
3. Restart. `GET /api/v1/ai/status` reports `{"available": true}` and the **AI assistant** tab becomes active.

Event data (type, date, attendance, location, budget, your request text) is sent to the configured provider; names, emails, notes, vendors and expenses are not. LangChain/LangSmith tracing is force-disabled. See [secrets-and-configuration](.agents/security/secrets-and-configuration.md). Never commit `.env`.
