import { useEffect, useState } from 'react';
import { moviesApi } from '../api/movies.js';
import { watchlistApi } from '../api/lists.js';
import { useAuthedApi } from '../auth/AuthContext.jsx';
import { EmptyState, ErrorState, PageSkeleton } from '../components/Chrome.jsx';
import { MovieCard } from '../components/Movies.jsx';
import { useToast } from '../components/Toaster.jsx';

export function Watchlist() {
  const authed = useAuthedApi();
  const { push } = useToast();
  const [state, setState] = useState({ status: 'loading', items: [] });

  useEffect(() => {
    let live = true;
    authed(() => watchlistApi.list())
      .then(async (d) => {
        const entries = d.items ?? [];
        const cards = await Promise.all(
          entries.map((w) => moviesApi.details(w.movieId).catch(() => null)),
        );
        if (live) setState({ status: 'ok', items: cards.filter(Boolean) });
      })
      .catch(() => live && setState({ status: 'error', items: [] }));
    return () => {
      live = false;
    };
  }, []);

  const remove = async (movieId) => {
    const prev = state.items;
    setState((s) => ({ ...s, items: s.items.filter((m) => m.tmdb_id !== movieId) }));
    try {
      await authed(() => watchlistApi.remove(movieId));
      push('Removed from watchlist');
    } catch (e) {
      setState((s) => ({ ...s, items: prev }));
      push(e.message, 'error');
    }
  };

  if (state.status === 'loading') return <PageSkeleton />;
  if (state.status === 'error')
    return <ErrorState message="Could not load your watchlist." onRetry={() => setState({ status: 'loading', items: [] })} />;
  if (!state.items.length)
    return (
      <EmptyState
        title="Your list is unwritten"
        hint="Save films you want to watch, or let the assistant choose."
        action={{ to: '/assistant', label: 'Get recommendations' }}
      />
    );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="font-display text-4xl">Watchlist</h1>
      <p className="mt-1 text-sm text-ash">{state.items.length} saved</p>
      <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {state.items.map((m) => (
          <div key={m.tmdb_id} className="group relative">
            <MovieCard movie={m} />
            <button
              onClick={() => remove(m.tmdb_id)}
              aria-label={`Remove ${m.title}`}
              className="absolute right-2 top-2 rounded-md bg-night/80 px-2 py-1 text-xs text-ash opacity-0 backdrop-blur transition group-hover:opacity-100 hover:text-crimson focus:opacity-100"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
