# CineMind — Project Plan (Phase 0)

## 1. Project Overview and Goals

CineMind is an agentic movie recommendation web application.

Goals:
- Provide conversational, agent-driven movie recommendations.
- Separate concerns across dedicated services: public API gateway, movie data service, and AI agent service.
- Ship a React frontend backed by an Express API layer, Python/FastAPI agent and movie services, and MongoDB persistence.
- Keep API contracts explicit and versioned so frontend and services can evolve independently.
- Enforce authentication on internal traffic and safe handling of secrets from day one.

Non-goals for Phase 0:
- No application source code.
- No dependency installation.
- No `package.json` or Python dependency files.
- No placeholder application files.

## 2. Implementation Phases

### Phase 1 — Backend and Dataset
- Stand up the Express API service and the FastAPI movies service.
- Ingest and model the movie dataset in MongoDB.
- Define persistent schemas and data-access patterns.

### Phase 2 — Agent Service
- Build the FastAPI agent service for recommendation reasoning and tool use.
- Wire the agent to the movies service and any external model providers.
- Define agent request/response shapes (to be frozen in `API_CONTRACTS.md`).

### Phase 3 — Chat Integration
- Add conversational endpoints to the Express API gateway.
- Proxy chat traffic to the agent service with auth, validation, and error mapping.
- Establish session/conversation persistence.

### Phase 4 — Frontend Integration
- Build the React frontend: discovery views, detail views, and chat UI.
- Integrate the frontend against the Express API only (never directly against internal services).
- Handle loading, error, and empty states.

### Phase 5 — Agent Evaluation
- Define recommendation quality and safety evaluations.
- Add regression tests and golden conversation sets.
- Gate agent changes on eval results.

### Phase 6 — Hardening and Packaging
- Harden auth, rate limiting, logging, and observability.
- Finalize Docker/compose packaging and deployment docs.
- Security review and release readiness.

## 3. Intended Service Ports

| Service | Stack | Port |
|---------|-------|------|
| Express API gateway (`services/api`) | Node.js / Express | 5000 |
| Agent service (`services/agent`) | Python / FastAPI | 8001 |
| Movies service (`services/movies`) | Python / FastAPI | 8002 |

- The React frontend (`frontend/`) calls only the Express API on port 5000.
- Internal service-to-service calls use the ports above and must authenticate (see Section 5).
- Port assignments are fixed unless changed via an explicit plan update.

## 4. API Contracts Source of Truth

- `docs/API_CONTRACTS.md` will be the source of truth for API contracts.
- If code and `API_CONTRACTS.md` disagree, `API_CONTRACTS.md` wins and code must be updated.
- Every new or changed endpoint must first be specified in `API_CONTRACTS.md`.
- `API_CONTRACTS.md` does not exist yet; it will be created when contracts are defined (Phase 1 or later).

## 5. Security Requirements

### Internal Service Authentication
- All internal service-to-service calls (API ↔ agent, API ↔ movies, agent ↔ movies) require authentication.
- Use a shared internal secret / service token (e.g., `INTERNAL_API_KEY`) sent as a bearer token or signed header; reject unauthenticated requests with 401/403.
- Never expose internal service ports or admin endpoints directly to the public internet; only the Express gateway (5000) and frontend are public-facing.
- Rotate internal credentials without code changes (via environment, not hard-coded values).

### Secrets Management
- Secrets live only in environment files / secret managers, never in source control.
- `.env` and `.env.*` files are git-ignored (see root `.gitignore`); commit only `.env.example` with placeholder values.
- Required secrets (to be documented in a future `.env.example`): database connection string, internal service key, and any third-party model API keys.
- Application code must fail fast on missing required secrets and must never log secret values.
