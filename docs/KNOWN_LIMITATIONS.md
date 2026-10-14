# Known Limitations (honest)

1. **No live-LLM evaluation.** No OpenRouter key exists in this workspace, so
   the 20-prompt matrix (`services/agent/tests/test_prompt_matrix.py`) scripts
   the model's tool-call decisions. Dispatch, grounding, auth gating, and
   failure paths are verified; actual model wording and tool *choice* are not.
2. **No frontend implementation.** Only `docs/DESIGN_BRIEF.md` exists;
   `frontend/` is empty.
3. **No Docker Compose.** Docker is unavailable here, so independent operation
   could not be confirmed — compose was withheld per the task's own condition.
   Run the three services separately; keep `:8001`/`:8002` off public networks.
4. **No live integration run.** Dependencies for a full stack run (MongoDB
   data, `npm install`, `pip install`, model key) were out of scope here, so
   service-to-service calls are verified by contract tests and fakes, not by a
   running deployment. The demo script (`docs/DEMO.md`) is the runbook.
5. **Single-process rate limits.** The limiters are in-memory; they do not
   share state across processes/hosts. Adequate for demo, not for production.
6. **Secret history.** A credentials file was committed by mistake and later
   deleted (`23cab4e`), but its blob remains in git history. Rotate those
   credentials and purge history (with explicit approval) before any public
   release.
7. **No CORS layer.** The gateway serves same-origin/Vite-proxied use; direct
   cross-origin browser calls need a CORS policy added and tested with Express
   installed.
8. **Static catalogue.** 1000 TMDB rows, no refresh pipeline; "trending" is a
   documented popularity proxy (no time dimension in the data).
