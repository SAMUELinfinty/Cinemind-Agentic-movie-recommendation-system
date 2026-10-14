import { request } from './client.js';

export const watchlistApi = {
  list: () => request('/api/watchlist', { auth: true }),
  add: (movieId) => request('/api/watchlist', { method: 'POST', auth: true, body: { movieId } }),
  remove: (movieId) => request(`/api/watchlist/${movieId}`, { method: 'DELETE', auth: true }),
};

export const ratingsApi = {
  upsert: ({ movieId, score, review }) =>
    request('/api/ratings', { method: 'POST', auth: true, body: { movieId, score, review } }),
  remove: (movieId) => request(`/api/ratings/${movieId}`, { method: 'DELETE', auth: true }),
};

export const chatApi = {
  createSession: (title) =>
    request('/api/chat/sessions', { method: 'POST', auth: true, body: title ? { title } : {} }),
  listSessions: () => request('/api/chat/sessions', { auth: true }),
  history: (id) => request(`/api/chat/sessions/${id}`, { auth: true }),
  send: (id, message, limit = 5) =>
    request(`/api/chat/sessions/${id}/messages`, {
      method: 'POST',
      auth: true,
      body: { message, limit },
      timeoutMs: 60000,
    }),
};
