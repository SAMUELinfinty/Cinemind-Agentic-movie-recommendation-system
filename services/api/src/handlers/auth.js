'use strict';

/**
 * Auth + profile handlers. All dependencies are injected:
 * { users, hasher, signer, config } so handlers run without mongoose,
 * bcryptjs, or jsonwebtoken installed. `users` store interface:
 * findByEmail(email), findById(id), create({ email, passwordHash, name }).
 */

const {
  validationError,
  unauthorized,
  conflict,
  internalError,
  notFound,
} = require('../errors');
const {
  validateEmail,
  validatePassword,
  validateName,
} = require('../validate');

function safeUser(user) {
  return {
    id: String(user._id ?? user.id),
    email: user.email,
    name: user.name ?? null,
    createdAt: user.createdAt ?? null,
  };
}

function registerHandler({ users, hasher, signer, config }) {
  return async (req, res) => {
    try {
      const { email, password, name } = req.body ?? {};
      const err =
        validateEmail(email) ?? validatePassword(password) ?? validateName(name);
      if (err) return validationError(res, err);

      const normalizedEmail = email.trim().toLowerCase();
      if (await users.findByEmail(normalizedEmail)) {
        return conflict(res, 'An account with this email already exists');
      }
      const passwordHash = await hasher.hash(password);
      const user = await users.create({
        email: normalizedEmail,
        passwordHash,
        name: name?.trim(),
      });
      const token = signer.sign(
        { sub: String(user._id ?? user.id), email: user.email },
        config.jwtSecret,
        config.jwtExpiresIn,
      );
      return res.status(201).json({ user: safeUser(user), token });
    } catch {
      return internalError(res);
    }
  };
}

function loginHandler({ users, hasher, signer, config }) {
  return async (req, res) => {
    try {
      const { email, password } = req.body ?? {};
      const err = validateEmail(email) ?? validatePassword(password);
      if (err) return validationError(res, err);

      const user = await users.findByEmail(email.trim().toLowerCase());
      if (!user) return unauthorized(res, 'Invalid email or password');
      if (!(await hasher.compare(password, user.passwordHash))) {
        return unauthorized(res, 'Invalid email or password');
      }
      const token = signer.sign(
        { sub: String(user._id ?? user.id), email: user.email },
        config.jwtSecret,
        config.jwtExpiresIn,
      );
      return res.json({ user: safeUser(user), token });
    } catch {
      return internalError(res);
    }
  };
}

function meHandler({ users }) {
  return async (req, res) => {
    try {
      const user = await users.findById(req.user.id);
      if (!user) return notFound(res, 'User not found');
      return res.json({ user: safeUser(user) });
    } catch {
      return internalError(res);
    }
  };
}

module.exports = { registerHandler, loginHandler, meHandler, safeUser };
