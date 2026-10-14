import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { moviesApi } from '../api/movies.js';
import { ratingsApi, watchlistApi } from '../api/lists.js';
import { useAuth, useAuthedApi } from '../auth/AuthContext.jsx';
import { EmptyState, ErrorState, MetadataRow, PageSkeleton } from '../components/Chrome.jsx';
import { Rail } from '../components/Movies.jsx';
import { useToast } from '../components/Toaster.jsx';

export function MovieDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const authed = useAuthedApi();
  const { push } = useToast();
  const [movie, setMovie] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [status, setStatus] = useState('loading');
  const [saved, setSaved] = useState(false);
  const [score, setScore] = useState(8);

  useEffect(() => {
    let live = true;
    setStatus('loading');
    moviesApi
      .details(id)
      .then((m) => {
        if (!live) return;
        setMovie(m);
        setStatus('ok');
        moviesApi.similar(id, 10).then((d) => live && setSimilar(d.items ?? [])).catch(() => {});
        if (user) {
          watchlistApi
            .list()
            .then((d) => live && setSaved((d.items ?? []).some((w) => Number(w.movieId) === Number(id))))
            .catch(() => {});
        }
      })
      .catch((e) => live && setStatus(e.status === 404 ? 'missing' : 'error'));
    return () => {
      live = false;
    };
  }, [id]);

  const needLogin = () => {
    push('Sign in to save and rate films', 'error');
    navigate('/login', { state: { from: `/movies/${id}` } });
  };

  const toggleWatchlist = async () => {
    if (!user) return needLogin();
    try {
      if (saved) {
        await authed(() => watchlistApi.remove(id));
        setSaved(false);
      } else {
        await authed(() => watchlistApi.add(Number(id)));
        setSaved(true);
        push('Added to your watchlist');
      }
    } catch (e) {
      push(e.message, 'error');
    }
  };

  const rate = async () => {
    if (!user) return needLogin();
    try {
      await authed(() => ratingsApi.upsert({ movieId: Number(id), score }));
      push(`Rated ★ ${score}`);
    } catch (e) {
      push(e.message, 'error');
    }
  };

  if (status === 'loading') return <PageSkeleton />;
  if (status === 'missing')
    return <EmptyState title="This reel is missing" hint="The film may have left the catalogue." action={{ to: '/movies', label: 'Browse movies' }} />;
  if (status === 'error' || !movie)
    return <ErrorState message="Could not load this film." onRetry={() => setStatus('loading')} />;

  return (
    <div className="pb-16 animate-fade">
      <section className="relative overflow-hidden">
        {movie.poster_path && (
          <img src={movie.poster_path} alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover object-top opacity-30" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-night via-night/80 to-night/30" />
        <div className="relative mx-auto grid max-w-7xl gap-8 px-4 pb-10 pt-12 sm:grid-cols-[220px_1fr] sm:px-6">
          {movie.poster_path ? (
            <img src={movie.poster_path} alt={`${movie.title} poster`} className="aspect-[2/3] w-40 rounded-lg border border-line shadow-lift sm:w-full" />
          ) : (
            <div className="flex aspect-[2/3] w-40 items-center justify-center rounded-lg border border-line bg-coal p-4 text-center sm:w-full">
              <span className="font-display text-xl text-ash">{movie.title}</span>
            </div>
          )}
          <div>
            <h1 className="font-display text-4xl leading-tight sm:text-5xl">{movie.title}</h1>
            <MetadataRow movie={movie} />
            {movie.overview && <p className="mt-4 max-w-2xl leading-relaxed text-parchment/90">{movie.overview}</p>}
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              {movie.director && (
                <span className="rounded-full border border-line bg-coal px-3 py-1 text-ash">Dir. {movie.director}</span>
              )}
              {(movie.top_cast ?? []).slice(0, 4).map((c) => (
                <span key={c} className="rounded-full border border-line bg-coal px-3 py-1 text-ash">{c}</span>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                onClick={toggleWatchlist}
                className={`rounded-md px-5 py-2.5 text-sm font-medium transition ${
                  saved ? 'border border-crimson text-crimson' : 'bg-crimson text-white hover:bg-crimson-deep'
                }`}
              >
                {saved ? '✓ In watchlist' : '+ Watchlist'}
              </button>
              <label className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm">
                ★
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={score}
                  onChange={(e) => setScore(Math.min(10, Math.max(1, Number(e.target.value) || 1)))}
                  aria-label="Your rating"
                  className="w-10 bg-transparent text-center focus:outline-none"
                />
                <button onClick={rate} className="text-crimson transition hover:text-parchment">
                  Rate
                </button>
              </label>
              <Link
                to={`/assistant?movie=${movie.tmdb_id}`}
                className="rounded-md border border-line px-5 py-2.5 text-sm transition hover:border-ash"
              >
                Ask about this film
              </Link>
            </div>
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <Rail title="More like this" action={{ to: `/movies?genre=${encodeURIComponent((movie.genres ?? [])[0] ?? '')}`, label: 'View all' }} items={similar} />
      </div>
    </div>
  );
}
