# CineMind Deployment Guide

Recommended free-tier path: **Render** (3 Docker web services) + **Vercel**
(frontend static). MongoDB is already on Atlas.

## 0. Prerequisites (do once)

1. Push the repo to GitHub (Dockerfiles + `docker-compose.yml` included).
2. Atlas → **Network Access** → **Allow Access from Anywhere** (`0.0.0.0/0`).
   Cloud hosts have shifting IPs, so IP-allowlisting will break deploys.
3. Seed Atlas if empty: from `services/movies` with `MONGODB_URI` pointing at
   Atlas, run `python seed.py` (expect `total_rows=1000`).

## 1. Backend on Render (3 services)

Create each at https://dashboard.render.com → **New → Web Service** →
point at the repo, runtime **Docker**, and set the **Dockerfile Path**:

| Service | Dockerfile Path | Port |
|---|---|---|
| `cinemind-movies` | `services/movies/Dockerfile` | 8002 |
| `cinemind-agent` | `services/agent/Dockerfile` | 8001 |
| `cinemind-api` | `services/api/Dockerfile` | 5000 |

Environment per service (Render dashboard → Environment; never commit these):

- **movies**: `MONGODB_URI` (Atlas `.../cinemind?...`), `INTERNAL_API_KEY`
  (generate one, reuse below)
- **agent**: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `INTERNAL_API_KEY`
  (same value), `MOVIES_SERVICE_URL=https://<movies>.onrender.com`
- **api**: `MONGODB_URI`, `JWT_SECRET` (generate), `INTERNAL_API_KEY` (same
  value), `MOVIES_SERVICE_URL`, `AGENT_SERVICE_URL=https://<agent>.onrender.com`,
  `CORS_ORIGIN=https://<your-app>.vercel.app` (step 2 URL)

Render free tiers sleep when idle — first request can take ~1 minute.

## 2. Frontend on Vercel

1. https://vercel.com → **Add New → Project** → import the repo.
2. **Root Directory**: `frontend`. Framework preset: **Vite**.
3. Environment variable: `VITE_API_URL=https://<api>.onrender.com`
   (build-time — redeploy after changing it).
4. Deploy → note the `https://<your-app>.vercel.app` URL → paste it into the
   api service's `CORS_ORIGIN` and redeploy the api service.

## 3. Verify production

```powershell
curl https://<api>.onrender.com/health
curl "https://<api>.onrender.com/api/trending?limit=1"
# register in the Vercel app, open Assistant, send a message
```

## Local prod-like run (needs Docker Desktop)
```powershell
$env:MONGODB_URI="<atlas-uri>"; $env:INTERNAL_API_KEY="<k>"; $env:JWT_SECRET="<j>"
$env:OPENROUTER_API_KEY="<k>"; $env:OPENROUTER_MODEL="liquid/lfm-2.5-2.6b:free"
docker compose up --build
```

## Notes

- The agent's free model is slow (~30–90s per reply); `AGENT_TIMEOUT_MS`
  (45s default) may need raising on sleepy free tiers.
- Rotate `INTERNAL_API_KEY`/`JWT_SECRET` for production (generate fresh ones
  in the dashboards, not the demo values in local `.env` files).

## Alternative: everything on Railway (no Vercel)

The frontend ships an nginx `Dockerfile`, so Railway can host all four
services in one project:

1. Add a 4th service from the repo, **Root Directory `frontend/`**.
2. Set its variable `VITE_API_URL=https://<api>.up.railway.app`
   (baked in at build time — redeploy the frontend if the API URL changes).
3. **Settings → Networking → Generate Domain** for the frontend service.
4. Set the api service's `CORS_ORIGIN` to that frontend domain and redeploy
   the api service.

Internal traffic stays on `*.railway.internal` hostnames exactly as in the
table above; only the api and frontend services need public domains.
