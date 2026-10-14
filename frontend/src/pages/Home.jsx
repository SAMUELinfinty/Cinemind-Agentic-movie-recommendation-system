import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { moviesApi } from '../api/movies.js';
import { MetadataRow, ErrorState } from '../components/Chrome.jsx';
import { Rail, RailSkeleton } from '../components/Movies.jsx';

function useRail(fetcher) {
  const [state, setState] = useState({ status: 'loading', items: [] });
  useEffect(() => {
    let live = true;
    fetcher()
      .then((items) => live && setState({ status: 'ok', items }))
      .catch(() => live && setState({ status: 'error', items: [] }));
    return () => {
      live = false;
    };
  }, []);
  return [state, () => setState({ status: 'loading', items: [] })];
}

function Hero() {
  const [state, retry] = useRail(() =>
    moviesApi.trending(1).then((d) => d.items ?? []),
  );
  if (state.status === 'loading')
    return <div className="skeleton h-[52vh] min-h-[380px] w-full" aria-busy="true" />;
  if (state.status === 'error' || !state.items.length) {
    if (!state.items.length && state.status === 'ok')
      return (
        <div className="flex h-[40vh] min-h-[300px] flex-col items-start justify-end px-4 pb-10 sm:px-6">
          <h1 className="font-display text-5xl sm:text-6xl">
            Every great night starts with the right film.
          </h1>
          <Link
            to="/assistant"
            className="mt-6 rounded-md bg-crimson px-6 py-3 text-sm font-medium text-white transition hover:bg-crimson-deep"
          >
            Ask the Assistant
          </Link>
        </div>
      );
    return <ErrorState message="Could not load the spotlight." onRetry={retry} />;
  }
  const m = state.items[0];
  return (
    <section className="relative h-[52vh] min-h-[380px] w-full overflow-hidden animate-fade">
      {m.poster_path && (
        <img
          src={m.poster_path}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-cover object-top"
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-night via-night/60 to-night/10" />
      <div className="absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-4 pb-10 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-crimson">
          Trending now
        </p>
        <h1 className="mt-2 max-w-3xl font-display text-5xl leading-[1.05] sm:text-6xl">
          {m.title}
        </h1>
        {m.overview && <p className="mt-3 max-w-xl line-clamp-2 text-ash">{m.overview}</p>}
        <MetadataRow movie={m} />
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to={`/assistant?q=${encodeURIComponent(`Recommend movies like ${m.title}`)}`}
            className="rounded-md bg-crimson px-6 py-2.5 text-sm font-medium text-white transition hover:bg-crimson-deep"
          >
            Ask the Assistant
          </Link>
          <Link
            to={`/movies/${m.tmdb_id}`}
            className="rounded-md border border-line px-6 py-2.5 text-sm transition hover:border-ash"
          >
            Details
          </Link>
        </div>
      </div>
    </section>
  );
}

const PROMPTS = ['A tense sci-fi night', 'Comedies from 2024', 'Hidden gems I missed'];

export function Home() {
  const [trending, retryTrending] = useRail(() => moviesApi.trending(10).then((d) => d.items ?? []));
  const [topRated, retryTop] = useRail(() =>
    moviesApi.discover({ min_vote: 8, limit: 10 }).then((d) => d.items ?? []),
  );
  const [scifi, retryScifi] = useRail(() =>
    moviesApi.discover({ genre: 'Science Fiction', limit: 10 }).then((d) => d.items ?? []),
  );

  return (
    <div className="pb-16">
      <Hero />
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {trending.status === 'loading' ? (
          <RailSkeleton title="Trending Now" />
        ) : trending.status === 'error' ? (
          <ErrorState message="Could not load trending." onRetry={retryTrending} />
        ) : (
          <Rail
            title="Trending Now"
            action={{ to: '/movies?sort=trending', label: 'View all' }}
            items={trending.items}
          />
        )}
        {topRated.status === 'loading' ? (
          <RailSkeleton title="Top Rated" />
        ) : topRated.status === 'error' ? (
          <ErrorState message="Could not load top rated." onRetry={retryTop} />
        ) : (
          <Rail
            title="Top Rated"
            action={{ to: '/movies?min_vote=8', label: 'View all' }}
            items={topRated.items}
          />
        )}
        {scifi.status === 'loading' ? (
          <RailSkeleton title="Science Fiction" />
        ) : scifi.status === 'error' ? (
          <ErrorState message="Could not load this collection." onRetry={retryScifi} />
        ) : (
          <Rail
            title="Science Fiction"
            action={{ to: '/movies?genre=Science Fiction', label: 'View all' }}
            items={scifi.items}
          />
        )}

        <section className="mt-12 rounded-xl border border-line bg-coal p-6 sm:p-8">
          <h2 className="font-display text-2xl sm:text-3xl">Can't decide? Ask CineMind.</h2>
          <p className="mt-2 max-w-lg text-sm text-ash">
            Tell the assistant your mood and get picks grounded in the catalogue.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {PROMPTS.map((p) => (
              <Link
                key={p}
                to={`/assistant?q=${encodeURIComponent(p)}`}
                className="rounded-full border border-line px-4 py-2 text-sm text-ash transition hover:border-crimson hover:text-parchment"
              >
                {p}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
