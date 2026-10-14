'use strict';

/**
 * Watchlist handlers (protected). Store interface:
 * listByUser(userId), add(userId, movieId), remove(userId, movieId) -> boolean.
 * Adds are idempotent — re-adding returns the existing entry.
 */

const { validationError, internalError, notFound } = require('../errors');
const { validateMovieId } = require('../validate');

function listWatchlist({ watchlist }) {
  return async (req, res) => {
    try {
      const items = await watchlist.listByUser(req.user.id);
      return res.json({ items });
    } catch {
      return internalError(res);
    }
  };
}

function addWatchlist({ watchlist }) {
  return async (req, res) => {
    try {
      const movieId = Number(req.params?.movieId ?? req.body?.movieId);
      const err = validateMovieId(movieId);
      if (err) return validationError(res, err);

      const entry = await watchlist.add(req.user.id, movieId);
      return res.status(201).json({ entry });
    } catch {
      return internalError(res);
    }
  };
}

function removeWatchlist({ watchlist }) {
  return async (req, res) => {
    try {
      const movieId = Number(req.params?.movieId);
      const err = validateMovieId(movieId);
      if (err) return validationError(res, err);

      const removed = await watchlist.remove(req.user.id, movieId);
      if (!removed) return notFound(res, 'Watchlist entry not found');
      return res.status(204).end();
    } catch {
      return internalError(res);
    }
  };
}

module.exports = { listWatchlist, addWatchlist, removeWatchlist };
