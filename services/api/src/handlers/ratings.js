'use strict';

/**
 * Ratings handlers (protected). Store interface:
 * listByUser(userId), upsert({ userId, movieId, score, review }),
 * remove(userId, movieId) -> boolean.
 */

const { validationError, internalError, notFound } = require('../errors');
const { validateMovieId, validateScore, validateReview } = require('../validate');

function listRatings({ ratings }) {
  return async (req, res) => {
    try {
      const items = await ratings.listByUser(req.user.id);
      return res.json({ items });
    } catch {
      return internalError(res);
    }
  };
}

function putRating({ ratings }) {
  return async (req, res) => {
    try {
      const movieId = Number(req.params?.movieId ?? req.body?.movieId);
      const { score, review } = req.body ?? {};
      const err =
        validateMovieId(movieId) ?? validateScore(score) ?? validateReview(review);
      if (err) return validationError(res, err);

      const saved = await ratings.upsert({
        userId: req.user.id,
        movieId,
        score: Number(score),
        review,
      });
      return res.status(201).json({ rating: saved });
    } catch {
      return internalError(res);
    }
  };
}

function deleteRating({ ratings }) {
  return async (req, res) => {
    try {
      const movieId = Number(req.params?.movieId);
      const err = validateMovieId(movieId);
      if (err) return validationError(res, err);

      const removed = await ratings.remove(req.user.id, movieId);
      if (!removed) return notFound(res, 'Rating not found');
      return res.status(204).end();
    } catch {
      return internalError(res);
    }
  };
}

module.exports = { listRatings, putRating, deleteRating };
