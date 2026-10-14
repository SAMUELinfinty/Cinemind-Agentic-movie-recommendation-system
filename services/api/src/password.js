'use strict';

/**
 * Password hashing. Production backend is bcryptjs (see package.json).
 * Falls back to node:crypto scrypt when bcryptjs is unavailable so the
 * module (and tests) load without installed dependencies. Plaintext is
 * never stored — only the resulting hash.
 *
 * A custom backend can be injected for tests: { hash, compare }.
 */

const crypto = require('node:crypto');

let backend = null;

function bcryptBackend() {
  // Lazy require: keeps this module loadable without node_modules.
  // eslint-disable-next-line global-require
  const bcrypt = require('bcryptjs');
  return {
    hash: (password) => bcrypt.hash(password, 12),
    compare: (password, hash) => bcrypt.compare(password, hash),
  };
}

function scryptBackend() {
  return {
    hash: (password) =>
      new Promise((resolve, reject) => {
        const salt = crypto.randomBytes(16).toString('hex');
        crypto.scrypt(password, salt, 64, (err, derived) => {
          if (err) return reject(err);
          resolve(`scrypt$${salt}$${derived.toString('hex')}`);
        });
      }),
    compare: (password, stored) =>
      new Promise((resolve, reject) => {
        const parts = String(stored).split('$');
        if (parts[0] !== 'scrypt' || parts.length !== 3) return resolve(false);
        crypto.scrypt(password, parts[1], 64, (err, derived) => {
          if (err) return reject(err);
          resolve(crypto.timingSafeEqual(Buffer.from(parts[2], 'hex'), derived));
        });
      }),
  };
}

function getBackend() {
  if (backend) return backend;
  try {
    backend = bcryptBackend();
  } catch {
    backend = scryptBackend();
  }
  return backend;
}

/** Test-only hook to inject a fake backend. */
function setBackend(next) {
  backend = next;
}

async function hashPassword(password) {
  return getBackend().hash(password);
}

async function comparePassword(password, hash) {
  return getBackend().compare(password, hash);
}

module.exports = { hashPassword, comparePassword, setBackend };
// Aliases matching the handler/store interface ({ hash, compare }).
module.exports.hash = hashPassword;
module.exports.compare = comparePassword;
