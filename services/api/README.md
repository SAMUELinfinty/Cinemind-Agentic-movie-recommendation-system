# CineMind Express API (port 5000)

Public gateway. The React frontend talks to this service only — the agent
(:8001) and movies (:8002) services stay private.

## Proposed contract (docs/API_CONTRACTS.md does not exist yet)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health`, `/` | no | service status |
| POST | `/api/auth/register` | no | `{email, password, name?}` → 201 `{user, token}` |
| POST | `/api/auth/login` | no | `{email, password}` → 200 `{user, token}` |
| GET | `/api/users/me` | Bearer | own profile (never includes password hash) |
| GET/POST/PUT | `/api/ratings`, `/api/ratings/:movieId` | Bearer | list / upsert `{movieId, score 1-10, review?}` / delete |
| GET/POST | `/api/watchlist`, `/api/watchlist/:movieId` | Bearer | list / idempotent add / delete |
| GET | `/api/movies*` | no | read-through proxy to the movies service (list, search, details, discover, trending, similar) |
| POST | `/api/chat/sessions` | Bearer | `{title?}` → 201 `{session}` |
| GET | `/api/chat/sessions` | Bearer | own sessions → `{items}` |
| GET | `/api/chat/sessions/:id` | Bearer + owner | session + `{messages}` history; 404 for foreign ids |
| POST | `/api/chat/sessions/:id/messages` | Bearer + owner | `{message, limit?}` → `{sessionId, reply, movies}`; agent down → 502 `agent_unavailable` |
| GET | `/internal/status` | X-Internal-Key | internal-only status probe |

Chat flow: Express persists the user message, forwards `{message, limit,
user_token}` to `POST :8001/chat` with `X-Internal-Key` (timeout
`AGENT_TIMEOUT_MS`), resolves the returned `movie_ids` into validated card
records via `:8002/movies/{id}` (invalid/missing cards are dropped), persists
the assistant reply, and returns `{sessionId, reply, movies}`. The internal
key and service URLs never leave the server; React only sends its Bearer
token, which is forwarded as the agent's `user_token` for personal tools.

## Proposed contract (docs/API_CONTRACTS.md does not exist yet)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health`, `/` | no | service status |
| POST | `/api/auth/register` | no | `{email, password, name?}` → 201 `{user, token}` |
| POST | `/api/auth/login` | no | `{email, password}` → 200 `{user, token}` |
| GET | `/api/users/me` | Bearer | own profile (never includes password hash) |
| GET/POST/PUT | `/api/ratings`, `/api/ratings/:movieId` | Bearer | list / upsert `{movieId, score 1-10, review?}` / delete |
| GET/POST | `/api/watchlist`, `/api/watchlist/:movieId` | Bearer | list / idempotent add / delete |
| GET | `/api/movies*` | no | read-through proxy to the movies service (list, search, details, discover, trending, similar) |
| GET | `/internal/status` | X-Internal-Key | internal-only status probe |

Errors always use `{ error: { code, message } }` with 400/401/403/404/409/500/502.
Passwords are hashed (bcryptjs; scrypt fallback) — plaintext is never stored
or returned. Secrets come from the environment; the app fails fast when
`JWT_SECRET` or `INTERNAL_API_KEY` is missing (outside test mode).

## Setup

```powershell
cd services/api
copy .env.example .env   # then fill in real secrets (never commit .env)
npm install
npm start                # listens on :5000
```

## Tests (no install required)

```powershell
cd services/api
npm test                 # node --test on tests/*.test.js
```

Unit tests cover validation, the error envelope, password hashing, JWT and
internal-key middleware, auth/profile/ratings/watchlist/chat handlers
(in-memory fakes), the movies proxy, the agent client (header/timeout/error
mapping), and card validation. Route-level tests with a live Express +
MongoDB are not run here (dependencies are not installed in this workspace);
verify those after `npm install` against a local MongoDB.

## Chat examples

```powershell
$h = @{ Authorization = "Bearer <jwt>" }

# create a session
Invoke-RestMethod -Method Post http://localhost:5000/api/chat/sessions `
  -Headers $h -ContentType "application/json" -Body '{"title":"Sci-fi night"}'

# send a message (persists both sides, returns reply + movie cards)
Invoke-RestMethod -Method Post http://localhost:5000/api/chat/sessions/<id>/messages `
  -Headers $h -ContentType "application/json" -Body '{"message":"suggest a fun sci-fi comedy"}'

# list sessions / load history
Invoke-RestMethod http://localhost:5000/api/chat/sessions -Headers $h
Invoke-RestMethod http://localhost:5000/api/chat/sessions/<id> -Headers $h
```
