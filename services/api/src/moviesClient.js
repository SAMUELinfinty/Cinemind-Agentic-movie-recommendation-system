'use strict';

/**
 * Movies-service reads for inline chat movie cards. Best-effort: any
 * failure resolves to null so one bad id never breaks the reply.
 * `fetchImpl` is injectable for tests (defaults to global fetch).
 */

function toCard(data) {
  if (!data || typeof data !== 'object') return null;
  const id = data.tmdb_id;
  const title = data.title;
  if (!Number.isInteger(id) || id <= 0) return null;
  if (typeof title !== 'string' || title.trim() === '') return null;
  return {
    tmdb_id: id,
    title,
    year: Number.isInteger(data.year) ? data.year : null,
    genres: Array.isArray(data.genres) ? data.genres.filter((g) => typeof g === 'string') : [],
    vote_average: typeof data.vote_average === 'number' ? data.vote_average : null,
    poster_path: typeof data.poster_path === 'string' ? data.poster_path : null,
    overview: typeof data.overview === 'string' ? data.overview : null,
  };
}

async function getMovieCard({ baseUrl, internalKey, timeoutMs, fetchImpl }, movieId) {
  const doFetch = fetchImpl ?? globalThis.fetch;
  try {
    const res = await doFetch(`${baseUrl}/movies/${movieId}`, {
      headers: { 'X-Internal-Key': internalKey },
      signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
    });
    if (!res || res.status !== 200) return null;
    return toCard(await res.json());
  } catch {
    return null;
  }
}

module.exports = { getMovieCard, toCard };
