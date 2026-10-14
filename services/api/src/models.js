'use strict';

/**
 * Mongoose models. Required lazily (see stores/mongo.js) so the rest of the
 * app loads without node_modules installed.
 */

function createModels(mongoose) {
  const { Schema } = mongoose;

  const userSchema = new Schema(
    {
      email: { type: String, required: true, unique: true, lowercase: true, trim: true },
      passwordHash: { type: String, required: true },
      name: { type: String, trim: true, default: null },
    },
    { timestamps: true },
  );

  const ratingSchema = new Schema(
    {
      userId: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
      movieId: { type: Number, required: true, index: true },
      score: { type: Number, required: true, min: 1, max: 10 },
      review: { type: String, default: null },
    },
    { timestamps: true },
  );
  ratingSchema.index({ userId: 1, movieId: 1 }, { unique: true });

  const watchlistSchema = new Schema(
    {
      userId: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
      movieId: { type: Number, required: true, index: true },
    },
    { timestamps: { createdAt: 'addedAt', updatedAt: false } },
  );
  watchlistSchema.index({ userId: 1, movieId: 1 }, { unique: true });

  const chatSessionSchema = new Schema(
    {
      userId: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
      title: { type: String, trim: true, default: 'New chat' },
    },
    { timestamps: true },
  );

  const chatMessageSchema = new Schema(
    {
      sessionId: { type: Schema.Types.ObjectId, ref: 'ChatSession', required: true, index: true },
      userId: { type: Schema.Types.ObjectId, ref: 'User', required: true, index: true },
      role: { type: String, enum: ['user', 'assistant'], required: true },
      content: { type: String, required: true },
      movieIds: { type: [Number], default: [] },
    },
    { timestamps: { createdAt: true, updatedAt: false } },
  );
  chatMessageSchema.index({ sessionId: 1, createdAt: 1 });

  return {
    User: mongoose.models.User ?? mongoose.model('User', userSchema),
    Rating: mongoose.models.Rating ?? mongoose.model('Rating', ratingSchema),
    Watchlist: mongoose.models.Watchlist ?? mongoose.model('Watchlist', watchlistSchema),
    ChatSession:
      mongoose.models.ChatSession ?? mongoose.model('ChatSession', chatSessionSchema),
    ChatMessage:
      mongoose.models.ChatMessage ?? mongoose.model('ChatMessage', chatMessageSchema),
  };
}

module.exports = { createModels };
