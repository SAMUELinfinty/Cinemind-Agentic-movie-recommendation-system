'use strict';

/**
 * Chat-session handlers (all protected; ownership enforced by scoping every
 * lookup to req.user.id — foreign ids answer 404, never 403 details).
 *
 * Deps: { sessions, messages, agentCall, getMovie } where
 * agentCall({ message, limit, userToken }) -> { response, movieIds } and
 * getMovie(movieId) -> validated card record or null.
 */

const { validationError, internalError, notFound, sendError } = require('../errors');
const { AgentError } = require('../agentClient');
const {
  validateChatMessage,
  validateSessionTitle,
  validateSessionId,
  validateChatLimit,
} = require('../validate');

function publicSession(session) {
  return {
    id: String(session._id ?? session.id),
    title: session.title,
    createdAt: session.createdAt ?? null,
    updatedAt: session.updatedAt ?? null,
  };
}

function publicMessage(message) {
  return {
    role: message.role,
    content: message.content,
    movieIds: Array.isArray(message.movieIds) ? message.movieIds : [],
    createdAt: message.createdAt ?? null,
  };
}

function bearerToken(req) {
  const header = req.headers?.authorization ?? '';
  const [scheme, token] = header.split(' ');
  return scheme === 'Bearer' && token ? token : null;
}

function createSession({ sessions }) {
  return async (req, res) => {
    try {
      const err = validateSessionTitle(req.body?.title);
      if (err) return validationError(res, err);

      const session = await sessions.create({
        userId: req.user.id,
        title: req.body?.title?.trim(),
      });
      return res.status(201).json({ session: publicSession(session) });
    } catch {
      return internalError(res);
    }
  };
}

function listSessions({ sessions }) {
  return async (req, res) => {
    try {
      const rows = await sessions.listByUser(req.user.id);
      return res.json({
        items: rows.map((s) => ({
          ...publicSession(s),
          messageCount: s.messageCount ?? null,
        })),
      });
    } catch {
      return internalError(res);
    }
  };
}

function getSession({ sessions, messages }) {
  return async (req, res) => {
    try {
      const err = validateSessionId(req.params?.id);
      if (err) return validationError(res, err);

      const session = await sessions.findOwned(req.params.id, req.user.id);
      if (!session) return notFound(res, 'Session not found');
      const history = await messages.listBySession(session._id ?? req.params.id, req.user.id);
      if (!history) return notFound(res, 'Session not found');
      return res.json({ session: publicSession(session), messages: history.map(publicMessage) });
    } catch {
      return internalError(res);
    }
  };
}

function postMessage({ sessions, messages, agentCall, getMovie }) {
  return async (req, res) => {
    try {
      const idErr = validateSessionId(req.params?.id);
      if (idErr) return validationError(res, idErr);
      const err =
        validateChatMessage(req.body?.message) ?? validateChatLimit(req.body?.limit);
      if (err) return validationError(res, err);

      const session = await sessions.findOwned(req.params.id, req.user.id);
      if (!session) return notFound(res, 'Session not found');

      const sessionId = session._id ?? req.params.id;
      await messages.append({
        sessionId,
        userId: req.user.id,
        role: 'user',
        content: req.body.message,
        movieIds: [],
      });

      let agentReply;
      try {
        agentReply = await agentCall({
          message: req.body.message,
          limit: req.body.limit ?? 5,
          userToken: bearerToken(req),
        });
      } catch (error) {
        if (error instanceof AgentError) {
          return sendError(res, 502, 'agent_unavailable', 'Agent service unavailable');
        }
        return internalError(res);
      }

      const ids = [...new Set(agentReply.movieIds)].slice(0, 10);
      const cards = [];
      for (const id of ids) {
        const card = await getMovie(id);
        if (card) cards.push(card);
      }

      await messages.append({
        sessionId,
        userId: req.user.id,
        role: 'assistant',
        content: agentReply.response,
        movieIds: ids,
      });

      return res.json({ sessionId: String(sessionId), reply: agentReply.response, movies: cards });
    } catch {
      return internalError(res);
    }
  };
}

module.exports = { createSession, listSessions, getSession, postMessage };
