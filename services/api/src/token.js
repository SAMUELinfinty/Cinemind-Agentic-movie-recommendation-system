'use strict';

/**
 * JWT helpers. Production backend is jsonwebtoken (see package.json),
 * lazily required so this module loads without installed dependencies.
 * A custom backend can be injected for tests: { sign, verify }.
 */

let backend = null;

function jwtBackend() {
  // eslint-disable-next-line global-require
  const jwt = require('jsonwebtoken');
  return {
    sign: (payload, secret, expiresIn) =>
      jwt.sign(payload, secret, { expiresIn }),
    verify: (token, secret) => jwt.verify(token, secret),
  };
}

function getBackend() {
  if (backend) return backend;
  backend = jwtBackend();
  return backend;
}

/** Test-only hook to inject a fake backend. */
function setBackend(next) {
  backend = next;
}

function signToken(payload, secret, expiresIn) {
  return getBackend().sign(payload, secret, expiresIn);
}

function verifyToken(token, secret) {
  return getBackend().verify(token, secret);
}

module.exports = { signToken, verifyToken, setBackend };
