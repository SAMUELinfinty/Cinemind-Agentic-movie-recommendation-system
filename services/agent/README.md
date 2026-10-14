# CineMind Agent Service (FastAPI, port 8001)

Single-turn movie agent with five tools. No multi-agent setups, RAG,
embeddings, or memory frameworks.

## Tools (each maps to an existing service endpoint — nothing invented)

| Tool | Service call | Auth |
|---|---|---|
| `search_movies` | `GET :8002/movies/search` | X-Internal-Key |
| `get_movie_details` | `GET :8002/movies/{id}` | X-Internal-Key |
| `discover_movies` | `GET :8002/discover` (genre/year/language/min_vote) | X-Internal-Key |
| `find_similar_movies` | `GET :8002/movies/{id}/similar` | X-Internal-Key |
| `get_user_context` | `GET :5000/api/users/me`, `/api/watchlist`, `/api/ratings` | caller JWT (`user_token`) + sign-in required |

`movie_ids` come only from catalogue tool results — never invented. Empty
watchlist/ratings → general catalogue recommendations, never invented tastes.

## Contract

No `docs/API_CONTRACTS.md` entry defines agent endpoints yet, so this is the
proposal (agent surface only — the movies-service call below reuses its
existing contract, no change needed there):

- `POST /chat` (requires `X-Internal-Key`)
  - Body: `{"message": str (1-2000 chars), "limit": int 1-10 default 5}`
  - Returns: `{"response": str, "movie_ids": [int], "model": str}`
  - `movie_ids` come only from tool results — never invented.
  - Errors: 401 missing/bad key, 422 bad input, 502 LLM unavailable.
- `GET /health` (open) → `{"status": "ok", "service": "agent"}`

Internal movies call (existing contract, unchanged):
`GET {MOVIES_SERVICE_URL}/movies/search?q=...&limit=...` with `X-Internal-Key`.

## Setup

```powershell
cd services/agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in OPENROUTER_API_KEY (never commit .env)
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Required env: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `INTERNAL_API_KEY`.
`POST /chat` also accepts an optional `user_token` (caller JWT, forwarded as
Bearer to the approved Express user endpoints only — never logged or stored).
See `.env.example` for placeholders (safe to commit; never commit `.env`).

## Sample request

```powershell
curl -X POST http://localhost:8001/chat `
  -H "Content-Type: application/json" `
  -H "X-Internal-Key: <your-internal-key>" `
  -d '{"message": "Suggest a fun sci-fi comedy", "limit": 3}'
```

Expected output (IDs vary with the catalogue):

```json
{
  "response": "Try Mike & Nick & Nick & Alice (2026) — a time-travel comedy...",
  "movie_ids": [1115544],
  "model": "openrouter/model-id"
}
```

Chit-chat (`{"message": "hi"}`) answers directly with `"movie_ids": []`.
If the movies service is down, the agent says so and returns `"movie_ids": []`.
If the LLM is unreachable, the endpoint returns 502.

## Tests (no network, no real LLM, no install beyond current env)

```powershell
cd services/agent
python -m pytest tests/ -q
```

44 tests (fakes only): the original 18 plus per-tool suites — details (6),
discover (5), similar (5), user context (7: Bearer forwarding, trim, missing /
expired auth, no-leak, empty-data fallback) — and multi-tool turns (3:
combined deduped IDs in one round, unknown-tool handling, `user_token`
forwarding through `POST /chat`).
