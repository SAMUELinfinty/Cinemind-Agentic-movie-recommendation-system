'use strict';

/**
 * Express app wiring. Requires express only when called, so pure modules
 * stay loadable without node_modules. `deps` may be overridden in tests:
 * { users, ratings, watchlist, hasher, signer, config, fetchImpl }.
 */

function createApp(deps = {}) {
  // eslint-disable-next-line global-require
  const express = require('express');
  const { loadConfig } = require('./config');
  const { requireAuth, requireInternalKey } = require('./middleware');
  const { internalError, notFound } = require('./errors');
  const authHandlers = require('./handlers/auth');
  const ratingsHandlers = require('./handlers/ratings');
  const watchlistHandlers = require('./handlers/watchlist');
  const chatHandlers = require('./handlers/chat');
  const { moviesProxy } = require('./handlers/moviesProxy');
  const { callAgent } = require('./agentClient');
  const { getMovieCard } = require('./moviesClient');

  const config = deps.config ?? loadConfig();
  const hasher = deps.hasher ?? require('./password');
  const signer = deps.signer ?? require('./token');
  const stores = {
    users: deps.users,
    ratings: deps.ratings,
    watchlist: deps.watchlist,
    sessions: deps.sessions,
    messages: deps.messages,
  };
  const agentBase = {
    baseUrl: config.agentServiceUrl,
    internalKey: config.internalApiKey,
    timeoutMs: config.agentTimeoutMs,
    fetchImpl: deps.fetchImpl,
  };
  const moviesBase = {
    baseUrl: config.moviesServiceUrl,
    internalKey: config.internalApiKey,
    fetchImpl: deps.fetchImpl,
  };

  const app = express();
  app.use(express.json());

  app.get('/health', (req, res) => res.json({ status: 'ok', service: 'api' }));
  app.get('/', (req, res) =>
    res.json({ service: 'api', health: '/health' }),
  );

  const auth = authHandlers;
  app.post('/api/auth/register', auth.registerHandler({ users: stores.users, hasher, signer, config }));
  app.post('/api/auth/login', auth.loginHandler({ users: stores.users, hasher, signer, config }));

  const guard = requireAuth({ secret: config.jwtSecret });
  app.get('/api/users/me', guard, auth.meHandler({ users: stores.users }));
  app.get('/api/ratings', guard, ratingsHandlers.listRatings({ ratings: stores.ratings }));
  app.post('/api/ratings', guard, ratingsHandlers.putRating({ ratings: stores.ratings }));
  app.put('/api/ratings/:movieId', guard, ratingsHandlers.putRating({ ratings: stores.ratings }));
  app.delete('/api/ratings/:movieId', guard, ratingsHandlers.deleteRating({ ratings: stores.ratings }));

  app.get('/api/watchlist', guard, watchlistHandlers.listWatchlist({ watchlist: stores.watchlist }));
  app.post('/api/watchlist', guard, watchlistHandlers.addWatchlist({ watchlist: stores.watchlist }));
  app.delete(
    '/api/watchlist/:movieId',
    guard,
    watchlistHandlers.removeWatchlist({ watchlist: stores.watchlist }),
  );

  // Public movie reads, served through Express (browser never calls :8002).
  const proxy = moviesProxy({
    baseUrl: config.moviesServiceUrl,
    internalKey: config.internalApiKey,
    fetchImpl: deps.fetchImpl,
  });
  app.get('/api/movies*', proxy);

  // Chat sessions: authenticated user <-> internal agent (:8001, X-Internal-Key).
  // No chat logic here — Express persists history and resolves movie cards.
  const chatDeps = {
    sessions: stores.sessions,
    messages: stores.messages,
    agentCall: (payload) => callAgent(agentBase, payload),
    getMovie: (id) => getMovieCard(moviesBase, id),
  };
  app.post('/api/chat/sessions', guard, chatHandlers.createSession(chatDeps));
  app.get('/api/chat/sessions', guard, chatHandlers.listSessions(chatDeps));
  app.get('/api/chat/sessions/:id', guard, chatHandlers.getSession(chatDeps));
  app.post('/api/chat/sessions/:id/messages', guard, chatHandlers.postMessage(chatDeps));

  // Internal-only endpoint (chat integration lands here in a later phase).
  app.get(
    '/internal/status',
    requireInternalKey({ expected: config.internalApiKey }),
    (req, res) => res.json({ status: 'ok', service: 'api' }),
  );

  app.use((req, res) => notFound(res));
  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => internalError(res));

  return app;
}

module.exports = { createApp };
