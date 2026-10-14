import { useState } from 'react';
import { Link } from 'react-router-dom';

function Artwork({ movie, className }) {
  const [failed, setFailed] = useState(false);
  if (!movie.poster_path || failed) {
    return (
      <div className={`flex items-center justify-center bg-seam p-3 text-center ${className}`}>
        <span className="font-display text-lg text-ash">{movie.title}</span>
      </div>
    );
  }
  return (
    <img
      src={movie.poster_path}
      alt={`${movie.title} poster`}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`bg-seam object-cover ${className}`}
    />
  );
}

/** Reusable card: variant "grid" (posters) or "compact" (inline rows). */
export function MovieCard({ movie, variant = 'grid' }) {
  if (variant === 'compact') {
    return (
      <Link
        to={`/movies/${movie.tmdb_id}`}
        className="group flex items-center gap-3 rounded-lg border border-line bg-coal p-2 pr-4 transition duration-200 hover:-translate-y-0.5 hover:border-ash/40 hover:shadow-lift"
      >
        <Artwork movie={movie} className="h-20 w-[54px] shrink-0 rounded-md" />
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium group-hover:text-white">
            {movie.title}
          </span>
          <span className="mt-0.5 block text-xs text-ash">
            {[movie.year, (movie.genres ?? []).slice(0, 2).join(' · ')]
              .filter(Boolean)
              .join('  ·  ')}
            {movie.vote_average != null && (
              <span className="ml-2 text-crimson">★ {Number(movie.vote_average).toFixed(1)}</span>
            )}
          </span>
        </span>
      </Link>
    );
  }
  return (
    <Link
      to={`/movies/${movie.tmdb_id}`}
      className="group animate-rise block"
      aria-label={movie.title}
    >
      <span className="relative block overflow-hidden rounded-lg border border-line transition duration-200 group-hover:-translate-y-1 group-hover:border-ash/40 group-hover:shadow-lift">
        <Artwork movie={movie} className="aspect-[2/3] w-full" />
        <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 transition duration-200 group-hover:opacity-100" />
      </span>
      <span className="mt-2 block truncate text-sm font-medium group-hover:text-white">
        {movie.title}
      </span>
      <span className="block text-xs text-ash">
        {movie.year}
        {movie.vote_average != null && (
          <span className="ml-2 text-crimson">★ {Number(movie.vote_average).toFixed(1)}</span>
        )}
      </span>
    </Link>
  );
}

export function PosterGrid({ items }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {items.map((m) => (
        <MovieCard key={m.tmdb_id} movie={m} />
      ))}
    </div>
  );
}

export function Rail({ title, action, items }) {
  if (!items?.length) return null;
  return (
    <section className="mt-10">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-display text-2xl">{title}</h2>
        {action && (
          <Link to={action.to} className="text-sm text-ash transition hover:text-crimson">
            {action.label} →
          </Link>
        )}
      </div>
      <div className="no-scrollbar -mx-4 flex snap-x gap-4 overflow-x-auto px-4 pb-2 sm:-mx-6 sm:px-6">
        {items.map((m) => (
          <div key={m.tmdb_id} className="w-32 shrink-0 snap-start sm:w-40">
            <MovieCard movie={m} />
          </div>
        ))}
      </div>
    </section>
  );
}

export function RailSkeleton({ title }) {
  return (
    <section className="mt-10" aria-busy="true" aria-label={title}>
      <div className="skeleton mb-4 h-7 w-48 rounded-md" />
      <div className="flex gap-4 overflow-hidden">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="skeleton aspect-[2/3] w-32 shrink-0 rounded-lg sm:w-40" />
        ))}
      </div>
    </section>
  );
}
