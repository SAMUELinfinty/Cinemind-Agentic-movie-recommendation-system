'use strict';

/**
 * Minimal CORS middleware (no dependencies). Reflects the request Origin
 * only when it is on the allow-list, so browsers on the frontend origin
 * can call the API while other sites get no access headers.
 * Pure (req, res, next) — unit-testable without express.
 */

function cors({ origins = [] } = {}) {
  const allowed = new Set(origins.map((o) => String(o).trim()).filter(Boolean));
  return (req, res, next) => {
    const origin = req.headers?.origin;
    if (origin && allowed.has(origin) && typeof res.set === 'function') {
      res.set('Access-Control-Allow-Origin', origin);
      res.set('Vary', 'Origin');
      res.set('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
      res.set('Access-Control-Allow-Headers', 'Content-Type,Authorization');
    }
    if (req.method === 'OPTIONS') {
      return res.status(204).end();
    }
    return next();
  };
}

module.exports = { cors };
