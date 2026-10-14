'use strict';

/**
 * Authentication middleware factories. Verifiers are injectable so the
 * middleware is unit-testable without jsonwebtoken installed.
 */

const { unauthorized, forbidden } = require('./errors');

/** Bearer JWT -> req.user = { id, email }. */
function requireAuth({ verify, secret } = {}) {
  const verifyFn = verify ?? require('./token').verifyToken;
  const jwtSecret = secret ?? process.env.JWT_SECRET;
  return (req, res, next) => {
    const header = req.headers?.authorization ?? '';
    const [scheme, token] = header.split(' ');
    if (scheme !== 'Bearer' || !token) {
      return unauthorized(res);
    }
    try {
      const payload = verifyFn(token, jwtSecret);
      req.user = { id: String(payload.sub), email: payload.email };
      return next();
    } catch {
      return unauthorized(res, 'Invalid or expired token');
    }
  };
}

/** Shared internal key for service-to-service endpoints. */
function requireInternalKey({ expected } = {}) {
  const key = expected ?? process.env.INTERNAL_API_KEY;
  return (req, res, next) => {
    const provided = req.headers?.['x-internal-key'];
    if (!provided) {
      return unauthorized(res, 'Missing internal key');
    }
    if (provided !== key) {
      return forbidden(res, 'Invalid internal key');
    }
    return next();
  };
}

module.exports = { requireAuth, requireInternalKey };
