'use strict';

/**
 * Mongo-backed stores matching the handler store interfaces.
 * Loaded lazily (requires mongoose + models).
 */

function createStores({ User, Rating, Watchlist }) {
  const users = {
    findByEmail: (email) => User.findOne({ email }).lean().exec(),
    findById: (id) => User.findById(id).lean().exec(),
    create: (data) => User.create(data).then((u) => u.toObject()),
  };

  const ratings = {
    listByUser: (userId) => Rating.find({ userId }).sort({ updatedAt: -1 }).lean().exec(),
    upsert: (data) =>
      Rating.findOneAndUpdate(
        { userId: data.userId, movieId: data.movieId },
        { $set: { score: data.score, review: data.review ?? null } },
        { new: true, upsert: true },
      )
        .lean()
        .exec(),
    remove: (userId, movieId) =>
      Rating.deleteOne({ userId, movieId }).exec().then((r) => r.deletedCount > 0),
  };

  const watchlist = {
    listByUser: (userId) => Watchlist.find({ userId }).sort({ addedAt: -1 }).lean().exec(),
    add: async (userId, movieId) => {
      await Watchlist.updateOne(
        { userId, movieId },
        { $setOnInsert: { userId, movieId } },
        { upsert: true },
      ).exec();
      return Watchlist.findOne({ userId, movieId }).lean().exec();
    },
    remove: (userId, movieId) =>
      Watchlist.deleteOne({ userId, movieId }).exec().then((r) => r.deletedCount > 0),
  };

  return { users, ratings, watchlist };
}

module.exports = { createStores };
