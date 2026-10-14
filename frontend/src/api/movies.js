import { request } from './client.js';

function params(obj) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== '') q.set(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : '';
}

export const moviesApi = {
  list: ({ page = 1, limit = 20 } = {}) => request(`/api/movies${params({ page, limit })}`),
  search: (q, { page = 1, limit = 20 } = {}) =>
    request(`/api/movies/search${params({ q, page, limit })}`),
  details: (id) => request(`/api/movies/${id}`),
  discover: (filters = {}) => request(`/api/discover${params(filters)}`),
  trending: (limit = 10) => request(`/api/trending${params({ limit })}`),
  similar: (id, limit = 10) => request(`/api/movies/${id}/similar${params({ limit })}`),
};
