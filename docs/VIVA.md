# CineMind Viva — Questions & Answers

1. **Why three services instead of one app?**
   Separation of concerns: the gateway owns identity and sessions, the agent
   owns reasoning, the movies service owns catalogue data. Each scales and
   deploys independently; the browser only ever sees port 5000.

2. **How does the agent avoid inventing movies?**
   `movie_ids` are collected exclusively from tool results (`collect_movie_ids`
   in `orchestrator.py`), never parsed from free text. Cards are re-validated
   by Express against the movies service before reaching the UI.

3. **What stops one user reading another's chats?**
   Every session/message query is scoped to `req.user.id` (`findOwned`,
   `listBySession`); foreign ids return 404, indistinguishable from missing.

4. **How are internal services protected?**
   `X-Internal-Key` (constant-time compare) on agent `/chat` and all
   server-to-service calls; Bearer JWT for user routes; the browser never
   learns internal URLs or keys (tested: credentials absent from bodies).

5. **What happens when the agent or movies service is down?**
   Timeouts on every hop (`AGENT_TIMEOUT_MS`, `MOVIES_TIMEOUT_MS`,
   `LLM/MOVIES_TIMEOUT_S`); agent failure → 502 `agent_unavailable` with the
   user message preserved; movies failure → reply with `movies: []`.

6. **How is seeding repeatable without duplicates?**
   Upsert on the stable unique `tmdb_id` (`tmdb_top1000_movies.csv` has 1000
   unique ids); reruns update in place and the script never deletes.

7. **Why genre overlap instead of embeddings for "similar"?**
   Transparent, dependency-free, and fully supported by the dataset
   (shared-genre count, vote/rating tiebreaks). Embeddings would add infra
   without evaluation data to justify it.

8. **How do you handle empty watchlists/ratings?**
   The agent reports empty context and the prompt instructs general catalogue
   recommendations; tastes are never invented (tested in the prompt matrix).

9. **Where are passwords and tokens kept?**
   bcrypt (scrypt fallback) hashes only; JWTs are stateless Bearer tokens;
   secrets live in git-ignored `.env`, with fail-fast startup checks.

10. **What limits abuse?**
    Express sliding-window limits (auth 30/15min, chat 30/min, 429 +
    `Retry-After`); FastAPI middleware (movies 300/min, agent 60/min,
    `/health` exempt); validation at every boundary.

11. **Why no Docker Compose?**
    Compose was deliberately withheld: Docker is unavailable here, so
    independent operation could not be confirmed. Until then, run services
    separately and bind `:8001`/`:8002` to localhost.

12. **Biggest known limitation?**
    No live-LLM evaluation has run (no key in this workspace) — tool routing
    is verified with 20 scripted prompt scenarios, not model wording. The
    React frontend is designed (`DESIGN_BRIEF.md`) but not implemented.
