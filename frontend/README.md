# CineMind Frontend (React + Vite + Tailwind)

Premium-cinematic, AI-native UI per `docs/DESIGN_BRIEF.md`. Talks to the
Express gateway exclusively (`VITE_API_URL`, default
`http://localhost:5000`) — no internal ports or keys here.

## Run

```powershell
cd frontend
copy .env.example .env   # optional; defaults to http://localhost:5000
npm.cmd install
npm.cmd run dev          # http://localhost:5173 (proxies /api to the gateway)
npm.cmd run build        # production bundle in dist/
```

Start the backend first: movies `:8002` (seeded) → agent `:8001` → gateway
`:5000`. See root `README.md` and `docs/DEMO.md`.

## Routes

`/` Home (hero + rails) · `/movies` (filters + grid) · `/movies/:id`
(details + similar + watchlist/rate) · `/watchlist` (auth) ·
`/assistant` (auth, full-page chat) · `/login` · `/register`.

## Notes

- JWT lives in memory; reload signs you out (per design brief).
- Artwork uses catalogue `poster_path` URLs with a title fallback.
- Fonts (Inter + Fraunces) load from Google Fonts at runtime.
