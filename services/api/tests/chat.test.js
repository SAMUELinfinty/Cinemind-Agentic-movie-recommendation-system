'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert/strict');

const { callAgent, AgentError } = require('../src/agentClient');
const { getMovieCard, toCard } = require('../src/moviesClient');
const { createSession, listSessions, getSession, postMessage } = require('../src/handlers/chat');
const {
  validateChatMessage,
  validateSessionTitle,
  validateSessionId,
  validateChatLimit,
} = require('../src/validate');

function fakeRes() {
  return {
    statusCode: 200,
    body: null,
    ended: false,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
    end() {
      this.ended = true;
      return this;
    },
  };
}

function memoryChat() {
  const sessions = [];
  const msgs = [];
  const owned = (id, userId) =>
    sessions.find((s) => String(s._id) === String(id) && s.userId === userId) ?? null;
  return {
    sessions: {
      create: async ({ userId, title }) => {
        const s = {
          _id: `s${sessions.length + 1}`,
          userId,
          title: title ?? 'New chat',
          createdAt: 'now',
          updatedAt: 'now',
        };
        sessions.push(s);
        return s;
      },
      listByUser: async (userId) => sessions.filter((s) => s.userId === userId),
      findOwned: async (id, userId) => owned(id, userId),
    },
    messages: {
      append: async (data) => {
        const m = { ...data, createdAt: 'now' };
        msgs.push(m);
        return m;
      },
      listBySession: async (sessionId, userId) => {
        if (!owned(sessionId, userId)) return null;
        return msgs.filter((m) => String(m.sessionId) === String(sessionId));
      },
      _all: msgs,
    },
  };
}

const CARDS = {
  101: { tmdb_id: 101, title: 'Alpha Dawn', year: 2024, genres: ['Action'], vote_average: 8.0 },
  104: { tmdb_id: 104, title: 'Alpha Returns' },
};

function makeDeps(chat, { agent, movie } = {}) {
  const calls = { agent: [], movies: [] };
  return {
    deps: {
      sessions: chat.sessions,
      messages: chat.messages,
      agentCall:
        agent ??
        (async (payload) => {
          calls.agent.push(payload);
          return { response: 'Try Alpha Dawn.', movieIds: [101, 104, 999] };
        }),
      getMovie:
        movie ??
        (async (id) => {
          calls.movies.push(id);
          if (id === 999) return null; // unknown to movies service
          return CARDS[id] ?? null;
        }),
    },
    calls,
  };
}

const alice = { id: 'u1', email: 'a@b.co' };
const authAlice = { user: alice, headers: { authorization: 'Bearer tok-123' }, body: {}, params: {} };

describe('chat validation', () => {
  it('validates message, title, session id, and limit', () => {
    assert.equal(validateChatMessage('hello'), null);
    assert.ok(validateChatMessage('   '));
    assert.ok(validateChatMessage('x'.repeat(2001)));
    assert.equal(validateSessionTitle(undefined), null);
    assert.ok(validateSessionTitle('x'.repeat(101)));
    assert.ok(validateSessionId(''));
    assert.equal(validateSessionId('s1'), null);
    assert.equal(validateChatLimit(undefined), null);
    assert.equal(validateChatLimit(5), null);
    assert.ok(validateChatLimit(0));
    assert.ok(validateChatLimit(11));
  });
});

describe('agentClient', () => {
  it('sends X-Internal-Key and forwards the user token', async () => {
    let seen;
    const fetchImpl = async (url, opts) => {
      seen = { url, opts };
      return { status: 200, json: async () => ({ response: 'hi', movie_ids: [1, -2, 'x'] }) };
    };
    const out = await callAgent(
      { baseUrl: 'http://agent:8001', internalKey: 'k', timeoutMs: 1000, fetchImpl },
      { message: 'hi', limit: 3, userToken: 'tok-123' },
    );
    assert.equal(seen.url, 'http://agent:8001/chat');
    assert.equal(seen.opts.headers['X-Internal-Key'], 'k');
    assert.deepEqual(JSON.parse(seen.opts.body), { message: 'hi', limit: 3, user_token: 'tok-123' });
    assert.deepEqual(out, { response: 'hi', movieIds: [1] });
  });
  it('omits user_token when anonymous and maps all failures to AgentError', async () => {
    const ok = async () => ({ status: 200, json: async () => ({ response: 'r', movie_ids: [] }) });
    const out = await callAgent(
      { baseUrl: 'http://a', internalKey: 'k', timeoutMs: 1000, fetchImpl: ok },
      { message: 'hi', limit: 5, userToken: null },
    );
    assert.equal(out.response, 'r');

    const cases = [
      async () => {
        throw new Error('down');
      },
      async () => ({ status: 500, json: async () => ({}) }),
      async () => ({ status: 200, json: async () => ({ nope: true }) }),
      async () => ({
        status: 200,
        json: async () => {
          throw new Error('bad json');
        },
      }),
    ];
    for (const fetchImpl of cases) {
      await assert.rejects(
        callAgent({ baseUrl: 'http://a', internalKey: 'k', timeoutMs: 1000, fetchImpl }, { message: 'm', limit: 5 }),
        AgentError,
      );
    }
  });
});

describe('moviesClient cards', () => {
  it('keeps valid records and drops malformed ones', () => {
    assert.equal(toCard(null), null);
    assert.equal(toCard({ tmdb_id: 1 }), null); // no title
    assert.equal(toCard({ tmdb_id: 'x', title: 'T' }), null);
    const card = toCard({ tmdb_id: 101, title: 'Alpha Dawn', genres: ['Action', 7] });
    assert.deepEqual(card.genres, ['Action']);
    assert.equal(card.year, null);
  });
  it('resolves 200s and degrades on 404s and outages', async () => {
    const byId = async (url) => {
      if (url.endsWith('/movies/101')) return { status: 200, json: async () => CARDS[101] };
      return { status: 404, json: async () => ({}) };
    };
    const base = { baseUrl: 'http://m:8002', internalKey: 'k', fetchImpl: byId };
    assert.equal((await getMovieCard(base, 101)).title, 'Alpha Dawn');
    assert.equal(await getMovieCard(base, 999), null);
    assert.equal(
      await getMovieCard({ ...base, fetchImpl: async () => { throw new Error('down'); } }, 101),
      null,
    );
  });
});

describe('chat sessions', () => {
  let chat;
  beforeEach(() => {
    chat = memoryChat();
  });

  it('creates a session with 201 and validates the title', async () => {
    const { deps } = makeDeps(chat);
    const res = fakeRes();
    await createSession(deps)({ ...authAlice, body: { title: 'Sci-fi night' } }, res);
    assert.equal(res.statusCode, 201);
    assert.equal(res.body.session.title, 'Sci-fi night');

    const bad = fakeRes();
    await createSession(deps)({ ...authAlice, body: { title: 'x'.repeat(101) } }, bad);
    assert.equal(bad.statusCode, 400);
  });

  it('runs the full message flow and persists both sides', async () => {
    const { deps, calls } = makeDeps(chat);
    const created = fakeRes();
    await createSession(deps)({ ...authAlice, body: {} }, created);
    const sid = created.body.session.id;

    const res = fakeRes();
    await postMessage(deps)(
      { ...authAlice, params: { id: sid }, body: { message: 'something fun', limit: 3 } },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.sessionId, sid);
    assert.equal(res.body.reply, 'Try Alpha Dawn.');
    // 999 resolved to null -> dropped; only validated cards returned.
    assert.deepEqual(res.body.movies.map((m) => m.tmdb_id), [101, 104]);

    // Agent got the message, limit, and caller token (never the internal key).
    assert.deepEqual(calls.agent, [{ message: 'something fun', limit: 3, userToken: 'tok-123' }]);

    const stored = chat.messages._all;
    assert.equal(stored.length, 2);
    assert.deepEqual([stored[0].role, stored[1].role], ['user', 'assistant']);
    assert.deepEqual(stored[1].movieIds, [101, 104, 999]);

    const history = fakeRes();
    await getSession(deps)({ ...authAlice, params: { id: sid } }, history);
    assert.equal(history.body.messages.length, 2);
    assert.equal(history.body.messages[0].content, 'something fun');
  });

  it('lists only the caller sessions', async () => {
    const { deps } = makeDeps(chat);
    await createSession(deps)({ ...authAlice, body: { title: 'A' } }, fakeRes());
    await createSession(deps)(
      { user: { id: 'u2' }, headers: {}, body: { title: 'B' }, params: {} },
      fakeRes(),
    );
    const res = fakeRes();
    await listSessions(deps)({ ...authAlice }, res);
    assert.equal(res.body.items.length, 1);
    assert.equal(res.body.items[0].title, 'A');
  });

  it('enforces ownership with 404 and never calls the agent', async () => {
    const { deps, calls } = makeDeps(chat);
    const created = fakeRes();
    await createSession(deps)({ ...authAlice, body: {} }, created);

    for (const req of [
      { user: { id: 'u2' }, headers: {}, params: { id: created.body.session.id }, body: { message: 'hi' } },
      { ...authAlice, params: { id: 'missing' }, body: { message: 'hi' } },
    ]) {
      const res = fakeRes();
      await postMessage(deps)(req, res);
      assert.equal(res.statusCode, 404);
      const history = fakeRes();
      await getSession(deps)(req, history);
      assert.equal(history.statusCode, 404);
    }
    assert.deepEqual(calls.agent, []);
    assert.equal(chat.messages._all.length, 0);
  });

  it('validates input before touching services', async () => {
    const { deps, calls } = makeDeps(chat);
    const created = fakeRes();
    await createSession(deps)({ ...authAlice, body: {} }, created);
    const sid = created.body.session.id;

    for (const body of [{ message: '' }, { message: 'hi', limit: 11 }]) {
      const res = fakeRes();
      await postMessage(deps)({ ...authAlice, params: { id: sid }, body }, res);
      assert.equal(res.statusCode, 400);
    }
    assert.deepEqual(calls.agent, []);
    assert.equal(chat.messages._all.length, 0);
  });

  it('returns a clear 502 when the agent is down', async () => {
    const { deps } = makeDeps(chat, {
      agent: async () => {
        throw new AgentError();
      },
    });
    const created = fakeRes();
    await createSession(deps)({ ...authAlice, body: {} }, created);

    const res = fakeRes();
    await postMessage(deps)(
      { ...authAlice, params: { id: created.body.session.id }, body: { message: 'hi' } },
      res,
    );
    assert.equal(res.statusCode, 502);
    assert.equal(res.body.error.code, 'agent_unavailable');
    // The user message is kept; no assistant reply is stored.
    assert.deepEqual(chat.messages._all.map((m) => m.role), ['user']);
  });

  it('degrades gracefully when movie cards are unavailable', async () => {
    const { deps } = makeDeps(chat, { movie: async () => null });
    const created = fakeRes();
    await createSession(deps)({ ...authAlice, body: {} }, created);

    const res = fakeRes();
    await postMessage(deps)(
      { ...authAlice, params: { id: created.body.session.id }, body: { message: 'hi' } },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.reply, 'Try Alpha Dawn.');
    assert.deepEqual(res.body.movies, []);
  });
});
