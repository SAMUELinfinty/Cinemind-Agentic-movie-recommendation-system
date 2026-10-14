import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { moviesApi } from '../api/movies.js';
import { EmptyState, ErrorState, PageSkeleton } from '../components/Chrome.jsx';
import { PosterGrid } from '../components/Movies.jsx';
import { useToast } from '../components/Toaster.jsx';

function useDebounced(value, ms) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

const GENRES = ['', 'Action', 'Adventure', 'Comedy', 'Crime', 'Drama', 'Fantasy', 'Horror', 'Romance', 'Science Fiction', 'Thriller'];

export function Movies() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') ?? '');
  const [genre, setGenre] = useState(params.get('genre') ?? '');
  const [year, setYear] = useState(params.get('year') ?? '');
  const [minVote, setMinVote] = useState(params.get('min_vote') ?? '');
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ status: 'loading', items: [], total: 0 });
  const { push } = useToast();
  const debouncedQ = useDebounced(q, 350);

  const filters = useMemo(
    () => ({ q: debouncedQ, genre, year, min_vote: minVote, page }),
    [debouncedQ, genre, year, minVote, page],
  );

  useEffect(() => {
    setParams(
      Object.fromEntries(Object.entries({ q: debouncedQ, genre, year, min_vote: minVote }).filter(([, v]) => v)),
      { replace: true },
    );
  }, [debouncedQ, genre, year, minVote]);

  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, status: 'loading' }));
    const run = filters.q
      ? moviesApi.search(filters.q, { page, limit: 20 })
      : moviesApi.discover({ ...filters, limit: 20 });
    run
      .then((d) => live && setState({ status: 'ok', items: d.items ?? [], total: d.total ?? 0 }))
      .catch((e) => {
        if (live) {
          setState({ status: 'error', items: [], total: 0 });
          push(e.message, 'error');
        }
      });
    return () => {
      live = false;
    };
  }, [filters, page]);

  const clearAll = () => {
    setQ('');
    setGenre('');
    setYear('');
    setMinVote('');
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="font-display text-4xl">Movies</h1>
      <div className="sticky top-14 z-30 -mx-4 mt-6 border-y border-line bg-night/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder="Search titles…"
            aria-label="Search titles"
            className="h-10 w-full rounded-md border border-line bg-coal px-3 text-sm placeholder:text-ash/70 focus:border-crimson focus:outline-none sm:w-56"
          />
          <select
            value={genre}
            onChange={(e) => {
              setGenre(e.target.value);
              setPage(1);
            }}
            aria-label="Genre"
            className="h-10 rounded-md border border-line bg-coal px-2 text-sm focus:border-crimson focus:outline-none"
          >
            {GENRES.map((g) => (
              <option key={g} value={g}>
                {g || 'All genres'}
              </option>
            ))}
          </select>
          <input
            value={year}
            onChange={(e) => {
              setYear(e.target.value.replace(/\D/g, '').slice(0, 4));
              setPage(1);
            }}
            placeholder="Year"
            aria-label="Year"
            inputMode="numeric"
            className="h-10 w-24 rounded-md border border-line bg-coal px-3 text-sm placeholder:text-ash/70 focus:border-crimson focus:outline-none"
          />
          <label className="flex items-center gap-2 text-sm text-ash">
            ★ {minVote || 'any'}
            <input
              type="range"
              min="0"
              max="10"
              step="1"
              value={minVote || 0}
              onChange={(e) => {
                setMinVote(e.target.value === '0' ? '' : e.target.value);
                setPage(1);
              }}
              aria-label="Minimum rating"
              className="accent-crimson"
            />
          </label>
          {(q || genre || year || minVote) && (
            <button onClick={clearAll} className="text-sm text-ash transition hover:text-crimson">
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="mt-6">
        {state.status === 'loading' ? (
          <PageSkeleton />
        ) : state.status === 'error' ? (
          <ErrorState
            message="Could not load titles."
            onRetry={() => setState((s) => ({ ...s, status: 'loading' }))}
          />
        ) : !state.items.length ? (
          <EmptyState
            title="No reels match"
            hint="Try clearing a filter or two."
          />
        ) : (
          <>
            <p className="mb-4 text-sm text-ash">{state.total} titles</p>
            <PosterGrid items={state.items} />
            <div className="mt-8 flex items-center justify-center gap-4">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-md border border-line px-4 py-2 text-sm transition enabled:hover:border-ash disabled:opacity-40"
              >
                ← Prev
              </button>
              <span className="text-sm text-ash">Page {page}</span>
              <button
                disabled={state.items.length < 20}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-md border border-line px-4 py-2 text-sm transition enabled:hover:border-ash disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
