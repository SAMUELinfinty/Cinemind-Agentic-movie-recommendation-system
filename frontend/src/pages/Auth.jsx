import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

function Field({ label, ...props }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-ash">{label}</span>
      <input
        {...props}
        className="h-11 w-full rounded-md border border-line bg-night px-3 text-parchment placeholder:text-ash/60 focus:border-crimson focus:outline-none"
      />
    </label>
  );
}

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const from = location.state?.from ?? '/';

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 animate-fade">
      <h1 className="font-display text-4xl">Welcome back</h1>
      <p className="mt-2 text-sm text-ash">Log in to your watchlist and assistant.</p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-4 rounded-xl border border-line bg-coal p-6">
        <Field label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        <Field label="Password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        {error && (
          <p role="alert" className="text-sm text-crimson">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="h-11 rounded-md bg-crimson font-medium text-white transition hover:bg-crimson-deep disabled:opacity-60"
        >
          {busy ? 'Logging in…' : 'Log in'}
        </button>
        <p className="text-center text-sm text-ash">
          New here?{' '}
          <Link to="/register" className="text-crimson hover:underline">
            Create an account
          </Link>
        </p>
      </form>
    </div>
  );
}

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    setError('');
    setBusy(true);
    try {
      await register({ email, password, name: name || undefined });
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.code === 'conflict' ? 'An account with this email already exists.' : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 animate-fade">
      <h1 className="font-display text-4xl">Join CineMind</h1>
      <p className="mt-2 text-sm text-ash">Save films and chat with your movie assistant.</p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-4 rounded-xl border border-line bg-coal p-6">
        <Field label="Name (optional)" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada" />
        <Field label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        <Field label="Password (8+ characters)" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        <Field label="Confirm password" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" />
        {error && (
          <p role="alert" className="text-sm text-crimson">
            {error}{' '}
            {error.startsWith('An account') && (
              <Link to="/login" className="underline">
                Sign in instead
              </Link>
            )}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="h-11 rounded-md bg-crimson font-medium text-white transition hover:bg-crimson-deep disabled:opacity-60"
        >
          {busy ? 'Creating…' : 'Create account'}
        </button>
        <p className="text-center text-sm text-ash">
          Have an account?{' '}
          <Link to="/login" className="text-crimson hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
