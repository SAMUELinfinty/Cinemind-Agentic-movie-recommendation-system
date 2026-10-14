# CineMind Demo Script (~10 minutes)

Prerequisites: MongoDB running, `services/movies` seeded (`python seed.py`
→ `total_rows=1000`), all three services up (see root `README.md`).

## 1. Catalogue (2 min)

```powershell
curl http://localhost:8002/health
curl "http://localhost:8002/movies/search?q=dune&limit=3"        # {items, total}
curl "http://localhost:8002/discover?genre=Comedy&year=2024&limit=3"
curl http://localhost:8002/movies/1115544                        # details
curl http://localhost:8002/movies/1115544/similar?limit=3
```

## 2. Gateway auth + personal lists (2 min)

```powershell
$reg = Invoke-RestMethod -Method Post http://localhost:5000/api/auth/register `
  -ContentType "application/json" -Body '{"email":"demo@cinemind.app","password":"demo-pass-1","name":"Demo"}'
$h = @{ Authorization = "Bearer $($reg.token)" }
Invoke-RestMethod http://localhost:5000/api/users/me -Headers $h
Invoke-RestMethod -Method Post http://localhost:5000/api/watchlist `
  -Headers $h -ContentType "application/json" -Body '{"movieId":1115544}'
```

## 3. Agentic chat (4 min)

```powershell
$s = Invoke-RestMethod -Method Post http://localhost:5000/api/chat/sessions `
  -Headers $h -ContentType "application/json" -Body '{"title":"Sci-fi night"}'
Invoke-RestMethod -Method Post http://localhost:5000/api/chat/sessions/$($s.session.id)/messages `
  -Headers $h -ContentType "application/json" -Body '{"message":"suggest a fun sci-fi comedy"}'
# → {sessionId, reply, movies:[{tmdb_id,title,year,genres,...}]}
Invoke-RestMethod -Method Post http://localhost:5000/api/chat/sessions/$($s.session.id)/messages `
  -Headers $h -ContentType "application/json" -Body '{"message":"something tailored to my watchlist"}'
# → agent used get_user_context (needs the Bearer token above)
Invoke-RestMethod http://localhost:5000/api/chat/sessions -Headers $h
```

Talking points: every `tmdb_id` comes from a tool result (never invented);
empty watchlist → general picks; agent/movies down → graceful 502/empty
cards; foreign session ids → 404.

## 4. Tests (2 min)

```powershell
cd services/movies; python -m pytest tests/ -q   # catalogue + accuracy + limits
cd services/agent;  python -m pytest tests/ -q   # 20-prompt matrix + tools + limits
cd services/api;    npm.cmd test                 # auth, chat flow, security audit
```

## If something fails live

- `502 agent_unavailable` → agent or OpenRouter key; replies still persist history.
- Empty `movies: []` → movies service down; reply still returned.
- `429` → rate limiter; wait for the `Retry-After` window.
