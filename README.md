# CineMind — Agentic Movie Recommendations

Conversational movie recommendations over a 1000-title TMDB catalogue.
React (planned, see `docs/DESIGN_BRIEF.md`) talks only to the Express
gateway; the agent and movie services stay private.

| Service | Stack | Port | Entry |
|---|---|---|---|
| Gateway | Node.js / Express | 5000 | `services/api` |
| Agent | Python / FastAPI + LangChain | 8001 | `services/agent` |
| Movies | Python / FastAPI + MongoDB | 8002 | `services/movies` |

## Quick setup (each service runs independently)

```powershell
# 1. Movies catalogue
cd services/movies
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py                    # ingests ../../tmdb_top1000_movies.csv -> MongoDB
uvicorn app.main:app --host 0.0.0.0 --port 8002

# 2. Agent (needs an OpenRouter key in .env)
cd services/agent
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env            # set OPENROUTER_API_KEY, OPENROUTER_MODEL
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 3. Gateway (needs MongoDB + secrets in .env)
cd services/api
copy .env.example .env            # set JWT_SECRET, INTERNAL_API_KEY
npm.cmd install; npm.cmd start    # :5000
```

MongoDB must be reachable (`MONGODB_URI`, default `mongodb://localhost:27017`).

## Tests (no installs beyond each runtime)

```powershell
cd services/movies; python -m pytest tests/ -q   # 25 passed
cd services/agent;  python -m pytest tests/ -q   # 67 passed (incl. 20-prompt matrix)
cd services/api;    npm.cmd test                 # 43 passed
```

## Docs

- `docs/PROJECT_PLAN.md` — phases and ports
- `docs/ARCHITECTURE.md` — diagram, request flows, auth boundaries
- `docs/DEMO.md` — demonstration script with example requests
- `docs/VIVA.md` — viva questions with answers
- `docs/KNOWN_LIMITATIONS.md` — honest limitations
- `docs/DESIGN_BRIEF.md` — frontend design (not yet implemented)

## Security notes

- Secrets live only in `.env` (git-ignored); only `.env.example` placeholders are committed.
- Service-to-service auth uses `X-Internal-Key`; user auth uses Bearer JWT.
- A credentials file was once committed by mistake and later deleted
  (`23cab4e`); its blob remains in history — rotate those credentials and,
  with approval, purge history before public release. See
  `docs/KNOWN_LIMITATIONS.md`.
