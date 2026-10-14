# CineMind — Design Brief & Frontend Implementation Plan

Status: **design only**. No frontend code is implemented in this task.
Stack for implementation (later): React + Vite + Tailwind CSS, talking to the
Express gateway (`:5000`) exclusively. Backend contracts referenced below are
read-only; nothing here changes them (`docs/API_CONTRACTS.md` still does not
exist — endpoint tables live in `services/api/README.md` and
`services/movies/README.md`).

---

## 1. Design language: Premium Cinematic × AI-Native

### 1.1 Visual identity (tokens)

| Token | Value | Usage |
|---|---|---|
| `bg` | `#0B0B0D` | app background everywhere |
| `surface` | `#18181C` | cards, panels, composer, sidebar |
| `surface-2` | `#202027` | hover/raised surfaces (derived, sparing) |
| `accent` | `#E53945` | primary actions, active states, key highlights only |
| `ink` | `#F3F0EB` | primary text |
| `ink-dim` | `#A8A29B` (derived) | secondary text, metadata |
| `line` | `rgba(243,240,235,0.10)` | subtle 1px borders |
| Interface font | Inter (or Geist if licensed) | UI, body, metadata |
| Display font | A refined editorial serif or condensed grotesk for headlines only (e.g. a Fraunces/Oswald-class face — final pick at implementation) | hero titles, page headlines, empty-state statements |

Rules: no glassmorphism panels, no neon, no rainbow gradients. Depth comes
from layered near-black surfaces, 1px borders, soft black shadows
(`0 8px 30px rgba(0,0,0,.45)`), and atmospheric dark overlays on artwork
(bottom-up black scrims for legibility). Crimson is rationed: one primary
action per view, active nav/selected states, rating highlights.

### 1.2 Cinematic principles

- **Artwork-led**: hero backdrops (`poster_path`/backdrop art), poster grids
  at a strict 2:3 ratio, consistent 8px radius, generous gutters.
- **Type hierarchy**: oversized display headline → one-line premise →
  single metadata row (year · runtime · genres · rating). Never walls of text.
- **Motion with restraint**: 150–250ms ease-out hovers (poster lift + scrim),
  fade/slide entrances on route change and card mount, skeleton shimmer on
  loads. No autoplay video, no parallax gimmicks.
- **Originality guard**: the look targets "midnight repertory cinema
  programme" — editorial, dark, quiet — not a SaaS dashboard and not a clone
  of any streaming site. No carousels-as-decoration; every rail is a curated
  collection with a real title and a "view all" target.

### 1.3 AI-native principles

- The Assistant is a **full page** (`/assistant`), not a floating widget.
- Desktop: three columns — session sidebar (240px) | conversation (max
  ~760px, centered) | no right rail (keeps focus; cards render inline).
- Mobile: conversation first; sessions behind a slide-over drawer.
- New conversations show **suggested prompts** (tappable chips).
- Recommendations render as **reusable inline `MovieCard` components** inside
  replies (same card used on Movies/Watchlist — one component, three sizes).
- Every async state is designed: skeleton loading, inline error + retry,
  agent-down notice, empty states with a next action.
- Follow-ups are one tap: "More like this", "Why this pick?", "Add to
  watchlist" action rows under assistant replies.

### 1.4 Responsive & accessibility baselines

- Breakpoints: `sm 640 / md 768 / lg 1024 / xl 1280`. Grids: 2 cols mobile →
  3–4 tablet → 5–6 desktop for posters.
- Contrast: warm-white on near-black passes AAA for body; dim text reserved
  for non-essential metadata. Focus-visible rings in crimson. All icon
  buttons labelled. Chat composer is a real `<form>` (Enter to send,
  Shift+Enter newline).

---

## 2. Information architecture & routes

| Route | Page | Auth | Data (all via `:5000`) |
|---|---|---|---|
| `/` | Home | public | `GET /api/movies/trending`, `GET /api/discover`, `GET /api/movies/search` |
| `/movies` | Movies | public | `GET /api/movies`, `/discover` (filters), `/movies/search` |
| `/movies/:id` | Movie Details | public; actions need login | `GET /api/movies/:id`, `/movies/:id/similar`; `POST /api/watchlist`, ratings upsert |
| `/watchlist` | Watchlist | required | `GET /api/watchlist` + card resolution via `/api/movies/:id` |
| `/login`, `/register` | Auth | guest | `POST /api/auth/login`, `POST /api/auth/register` |
| `/assistant` | AI Assistant | required | chat-session endpoints (see §4) |

Auth model: JWT in memory + `GET /api/users/me` hydration on load; Bearer
header on every protected call; 401 → redirect to `/login` with return path.
Guest clicking a protected action gets an inline sign-in nudge, not a dead end.

---

## 3. Page-by-page plan

### 3.1 Home (`/`)

1. **Hero** — full-bleed trending #1 artwork with bottom-up black scrim;
   display headline = title, one-line overview clamp, metadata row
   (year · genres · ★ vote_average), two actions: primary crimson
   "Ask the Assistant" (deep-links `/assistant?q=…`), secondary
   "Details". Fallback: if trending is empty, a typographic hero (no art).
2. **Rails** (each with title + "View all" → `/movies?…`): Trending Now,
   Top Rated (`discover?min_vote=8`), a genre collection
   (`discover?genre=…`), New & Notable (`discover?year=…`). Horizontal scroll
   with edge fades on desktop, snap scroll on mobile.
3. **Assistant invitation band** — charcoal panel, three suggested-prompt
   chips that deep-link into `/assistant`. This is the cinematic→AI bridge.
4. States: hero skeleton, rail skeletons, section-level error with retry
   (one failed rail never blanks the page).

### 3.2 Movies (`/movies`)

- Sticky filter bar: search field (debounced → `/movies/search`), genre
  select, year input, language select, min-rating slider → all mapped 1:1 to
  `/discover` params. Filters are URL-synced (`?genre=&year=…`) so rails and
  assistant links can target exact views.
- Poster grid (`MovieCard`, 2:3), paginated (`page`/`limit`, total count
  line "248 titles"). Empty result → editorial empty state ("No reels match
  — clear filters" button). Error → retry preserving filters.

### 3.3 Movie Details (`/movies/:id`)

- Backdrop header (artwork + scrim), title hierarchy, metadata row, overview,
  director/cast chips, actions: **+ Watchlist** (toggles, needs login),
  **Rate** (1–10 stepper → ratings upsert), **Ask about this film**
  (→ `/assistant?movie=<id>`).
- "More like this" rail from `/movies/:id/similar` (same `MovieCard`).
- 404 state for unknown ids ("This reel is missing" + back link); actions
  show inline auth nudges for guests.

### 3.4 Watchlist (`/watchlist`, auth)

- Poster grid of saved titles with remove-on-hover; sort by added date
  (server order). Empty state is a designed moment: display serif line
  ("Your list is unwritten"), plus "Get recommendations" → `/assistant`.
- Removing is optimistic with error rollback + toast.

### 3.5 Login / Register (guest)

- Centered charcoal panel on near-black, single column, generous spacing.
- Register: name/email/password (+ confirm); Login: email/password. Inline
  field errors from the API envelope (`{error:{code,message}}`); 409 on
  duplicate email → "Sign in instead" link. Submit → store JWT → `GET
  /api/users/me` → redirect to return path. No social login in v1.

### 3.6 AI Assistant (`/assistant`, auth) — the centerpiece

- **Desktop**: session sidebar (new-chat button, search-less list with
  timestamps, delete if later added) | central thread (max-w ~760px) |
  composer pinned bottom (textarea, char count toward 2000, send button,
  disabled-while-streaming state even though v1 is request/response).
- **Mobile**: header menu button opens sessions drawer; thread is full width.
- **New conversation**: greeting headline + 4 suggested-prompt chips
  ("A tense sci-fi night", "Comedies from 2024", "Movies like …", "Hidden
  gems I missed") + optional `?q=` / `?movie=` prefill from deep links.
- **Messages**: user right-aligned charcoal bubbles; assistant replies as
  readable prose (comfortable measure, `1.65` line-height) with `MovieCard`
  rows inline wherever `movies[]` returns records — the same component as
  grids, compact variant. Follow-up action row per assistant message.
- **States**: streaming-style skeleton ("Consulting the reels…") while
  `POST …/messages` is in flight; 502 `agent_unavailable` → error bubble
  with **Retry** (re-sends, no duplicate user message); empty history for a
  fresh session → prompt chips; session list empty → "Start your first
  conversation".
- History loads via `GET /api/chat/sessions/:id`; switching sessions keeps
  scroll position per session (simple cache).

---

## 4. Data & component map (implementation checklist)

- **API layer** (`src/api/`): typed `fetch` wrapper (base URL from env,
  Bearer injection, envelope errors, `AbortSignal.timeout`); modules
  `auth.js`, `movies.js` (list/search/details/discover/trending/similar),
  `watchlist.js`, `ratings.js`, `chat.js` (sessions CRUD + messages).
- **Shared components**: `MovieCard` (grid/compact/row variants),
  `PosterGrid`, `Rail`, `MetadataRow`, `RatingInput`, `EmptyState`,
  `ErrorState(retry)`, `Skeleton`, `PromptChips`, `Composer`, `SessionList`,
  `AuthGuard`, `Toaster`.
- **State**: `AuthContext` (JWT + profile); React Query (or minimal
  cache hooks) for movies; chat thread state local to `/assistant` with
  per-session cache. No global store library beyond context in v1.
- **Tailwind theme**: extend with the five tokens + display font + radius/
  shadow scale; dark-only (no light mode in v1).
- **Env**: single `VITE_API_URL` (default `http://localhost:5000`); internal
  ports/keys never referenced in frontend code.

## 5. Build order (later tasks) & acceptance look

1. Tokens/theme + `MovieCard` + skeletons/errors → 2. Home → 3. Movies +
   Details → 4. Auth + Watchlist → 5. Assistant page → 6. Motion/empty-state
   polish + responsive pass.
- Done looks like: every page renders correct loading/error/empty states;
  assistant answers show inline cards; no floating chatbot exists anywhere;
  palette/fonts/spacing match §1 on desktop and mobile widths.

---

## 6. Explicit non-goals (this task changed nothing)

No frontend code, no dependency installs, no backend or contract changes, no
file deletions, no git operations. Only this new file was created.
