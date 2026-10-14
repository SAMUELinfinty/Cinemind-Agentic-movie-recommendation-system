'use strict';

/**
 * Read-through proxy to the private movies service. The browser never calls
 * port 8002 directly; Express forwards with X-Internal-Key and returns the
 * upstream JSON, mapping failures to the consistent error envelope.
 * `fetchImpl` is injectable for tests (defaults to global fetch).
 */

const { sendError } = require('../errors');

const ALLOWED_PATHS = new Set([
  '/movies',
  '/movies/search',
  '/discover',
  '/trending',
]);

function isAllowedMoviePath(path) {
  if (ALLOWED_PATHS.has(path)) return true;
  return /^\/movies\/\d+$/.test(path) || /^\/movies\/\d+\/similar$/.test(path);
}

function moviesProxy({ baseUrl, internalKey, timeoutMs, fetchImpl }) {
  const doFetch = fetchImpl ?? globalThis.fetch;
  return async (req, res) => {
    const upstreamPath = req.path.replace(/^\/api/, '') || '/movies';
    if (!isAllowedMoviePath(upstreamPath)) {
      return sendError(res, 404, 'not_found', 'Not found');
    }
    const query = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    try {
      const upstream = await doFetch(`${baseUrl}${upstreamPath}${query}`, {
        headers: { 'X-Internal-Key': internalKey },
        signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
      });
      const body = await upstream.json();
      return res.status(upstream.status).json(body);
    } catch {
      return sendError(res, 502, 'bad_gateway', 'Movies service unavailable');
    }
  };
}

module.exports = { moviesProxy, isAllowedMoviePath };
