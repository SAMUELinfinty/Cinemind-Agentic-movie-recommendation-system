import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthGuard, Navbar } from './components/Chrome.jsx';
import { Home } from './pages/Home.jsx';
import { Movies } from './pages/Movies.jsx';
import { MovieDetails } from './pages/MovieDetails.jsx';
import { Watchlist } from './pages/Watchlist.jsx';
import { Login, Register } from './pages/Auth.jsx';
import { Assistant } from './pages/Assistant.jsx';

export default function App() {
  return (
    <div className="min-h-screen bg-night text-parchment">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/movies" element={<Movies />} />
          <Route path="/movies/:id" element={<MovieDetails />} />
          <Route
            path="/watchlist"
            element={
              <AuthGuard>
                <Watchlist />
              </AuthGuard>
            }
          />
          <Route
            path="/assistant"
            element={
              <AuthGuard>
                <Assistant />
              </AuthGuard>
            }
          />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
