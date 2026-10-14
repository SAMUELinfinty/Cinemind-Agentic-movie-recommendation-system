import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

export function Navbar() {
  const { user, logout } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-night/95 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2" aria-label="CineMind home">
          <img src="/logo.svg" alt="" aria-hidden="true" className="h-7 w-7" />
          <span className="font-display text-xl tracking-wide">
            Cine<span className="text-crimson">Mind</span>
          </span>
        </Link>
        <div className="flex items-center gap-4 text-sm text-ash">
          <Link to="/movies" className="transition hover:text-parchment">
            Movies
          </Link>
          <Link to="/assistant" className="transition hover:text-parchment">
            Assistant
          </Link>
          {user && (
            <Link to="/watchlist" className="transition hover:text-parchment">
              Watchlist
            </Link>
          )}
        </div>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="hidden text-ash sm:inline">{user.name || user.email}</span>
              <button
                onClick={logout}
                className="rounded-md border border-line px-3 py-1.5 text-ash transition hover:border-ash hover:text-parchment"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-ash transition hover:text-parchment">
                Log in
              </Link>
              <Link
                to="/register"
                className="rounded-md bg-crimson px-3 py-1.5 font-medium text-white transition hover:bg-crimson-deep"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

export function AuthGuard({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <PageSkeleton />;
  if (!user)
    return (
      <EmptyState
        title="Sign in to continue"
        hint="This reel is for members."
        action={{ to: '/login', label: 'Log in' }}
      />
    );
  return children;
}

export function PageSkeleton() {
  return (
    <div className="mx-auto max-w-7xl animate-fade px-4 py-8 sm:px-6" aria-busy="true">
      <div className="skeleton h-8 w-56 rounded-md" />
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="skeleton aspect-[2/3] rounded-lg" />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-20 text-center animate-fade">
      <p className="font-display text-3xl">{title}</p>
      {hint && <p className="mt-3 text-ash">{hint}</p>}
      {action && (
        <Link
          to={action.to}
          className="mt-6 rounded-md bg-crimson px-5 py-2.5 text-sm font-medium text-white transition hover:bg-crimson-deep"
        >
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-16 text-center animate-fade">
      <p className="font-display text-2xl">The projector jammed</p>
      <p className="mt-2 text-sm text-ash">{message || 'Something went wrong.'}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 rounded-md border border-line px-5 py-2 text-sm transition hover:border-ash hover:text-parchment"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function MetadataRow({ movie }) {
  const bits = [
    movie.year,
    movie.runtime_min ? `${movie.runtime_min} min` : null,
    (movie.genres ?? []).slice(0, 3).join(' · '),
  ].filter(Boolean);
  return (
    <p className="mt-1 text-[13px] text-ash">
      {bits.join('  ·  ')}
      {movie.vote_average != null && (
        <span className="ml-2 text-crimson">★ {Number(movie.vote_average).toFixed(1)}</span>
      )}
    </p>
  );
}
