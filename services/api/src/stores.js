'use strict';

/**
 * Mongo-backed stores matching the handler store interfaces.
 * Loaded lazily (requires mongoose + models).
 */

function createStores({ User, Rating, Watchlist, ChatSession, ChatMessage }) {
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

  const sessions = {
    create: ({ userId, title }) =>
      ChatSession.create({ userId, title: title ?? 'New chat' }).then((s) => s.toObject()),
    listByUser: (userId) => ChatSession.find({ userId }).sort({ updatedAt: -1 }).lean().exec(),
    findOwned: (id, userId) => ChatSession.findOne({ _id: id, userId }).lean().exec(),
  };

  const messages = {
    append: (data) => ChatMessage.create(data).then((m) => m.toObject()),
    listBySession: async (sessionId, userId) => {
      const session = await ChatSession.findOne({ _id: sessionId, userId }).lean().exec();
      if (!session) return null;
      return ChatMessage.find({ sessionId }).sort({ createdAt: 1 }).lean().exec();
    },
  };

  return { users, ratings, watchlist, sessions, messages };
}

module.exports = { createStores };
