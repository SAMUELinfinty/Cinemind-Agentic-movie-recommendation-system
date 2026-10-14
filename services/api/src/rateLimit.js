'use strict';

/**
 * Minimal in-memory sliding-window rate limiter (no dependencies).
 * Not for multi-process production — it protects the demo/submission
 * deployment behind a single Node process. `now` and `store` are
 * injectable for tests.
 */

const { sendError } = require('./errors');

function clientKey(req) {
  const forwarded = req.headers?.['x-forwarded-for'];
  if (typeof forwarded === 'string' && forwarded.trim() !== '') {
    return forwarded.split(',')[0].trim();
  }
  return req.ip ?? req.socket?.remoteAddress ?? 'unknown';
}

function rateLimit({ windowMs, max, store, now } = {}) {
  const hits = store ?? new Map();
  const clock = now ?? (() => Date.now());
  return (req, res, next) => {
    const key = `${clientKey(req)}`;
    const at = clock();
    const cutoff = at - windowMs;
    const times = (hits.get(key) ?? []).filter((t) => t > cutoff);
    if (times.length >= max) {
      const retryAfter = Math.ceil((times[0] + windowMs - at) / 1000);
      if (typeof res.set === 'function') res.set('Retry-After', String(Math.max(retryAfter, 1)));
      return sendError(res, 429, 'rate_limited', 'Too many requests, slow down');
    }
    times.push(at);
    hits.set(key, times);
    return next();
  };
}

const authLimiter = (overrides = {}) => rateLimit({ windowMs: 15 * 60 * 1000, max: 30, ...overrides });
const chatLimiter = (overrides = {}) => rateLimit({ windowMs: 60 * 1000, max: 30, ...overrides });

module.exports = { rateLimit, authLimiter, chatLimiter, clientKey };
