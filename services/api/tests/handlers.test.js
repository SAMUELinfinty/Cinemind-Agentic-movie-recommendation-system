'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert/strict');

const { hashPassword, comparePassword, setBackend } = require('../src/password');
const { registerHandler, loginHandler, meHandler } = require('../src/handlers/auth');
const { listRatings, putRating, deleteRating } = require('../src/handlers/ratings');
const { listWatchlist, addWatchlist, removeWatchlist } = require('../src/handlers/watchlist');
const { moviesProxy } = require('../src/handlers/moviesProxy');

const CONFIG = { jwtSecret: 's', jwtExpiresIn: '7d' };

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

function memoryUsers() {
  const rows = [];
  return {
    rows,
    findByEmail: async (email) => rows.find((u) => u.email === email) ?? null,
    findById: async (id) => rows.find((u) => String(u._id) === String(id)) ?? null,
    create: async (data) => {
      const user = { _id: `u${rows.length + 1}`, createdAt: 'now', ...data };
      rows.push(user);
      return user;
    },
  };
}

const fakeHasher = {
  hash: async (pw) => `hashed:${pw}`,
  compare: async (pw, hash) => hash === `hashed:${pw}`,
};

const fakeSigner = {
  sign: (payload) => `token-for-${payload.sub}`,
};

describe('password hashing', () => {
  it('never stores plaintext and verifies correctly', async () => {
    setBackend(null);
    // Force the stdlib fallback regardless of installed deps.
    const crypto = require('node:crypto');
    assert.ok(crypto);
    const hash = await hashPassword('s3cure-pass');
    assert.ok(hash !== 's3cure-pass');
    assert.equal(await comparePassword('s3cure-pass', hash), true);
    assert.equal(await comparePassword('wrong-pass', hash), false);
    setBackend(null);
  });
});

describe('auth handlers', () => {
  let users;
  beforeEach(() => {
    users = memoryUsers();
  });

  it('registers a user with a hashed password and token', async () => {
    const res = fakeRes();
    await registerHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG })(
      { body: { email: 'Ada@Example.com', password: 's3cure-pass', name: 'Ada' } },
      res,
    );
    assert.equal(res.statusCode, 201);
    assert.equal(res.body.user.email, 'ada@example.com');
    assert.ok(res.body.token);
    assert.ok(!('passwordHash' in res.body.user) && !('password' in res.body.user));
    assert.ok(users.rows[0].passwordHash !== 's3cure-pass');
  });
  it('rejects duplicate registration with 409', async () => {
    const handler = registerHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG });
    await handler({ body: { email: 'a@b.co', password: 's3cure-pass' } }, fakeRes());
    const res = fakeRes();
    await handler({ body: { email: 'a@b.co', password: 's3cure-pass' } }, res);
    assert.equal(res.statusCode, 409);
  });
  it('rejects invalid registration input with 400', async () => {
    const handler = registerHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG });
    const res = fakeRes();
    await handler({ body: { email: 'bad', password: 'short' } }, res);
    assert.equal(res.statusCode, 400);
  });
  it('logs in with correct credentials', async () => {
    const handler = loginHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG });
    await registerHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG })(
      { body: { email: 'a@b.co', password: 's3cure-pass' } },
      fakeRes(),
    );
    const res = fakeRes();
    await handler({ body: { email: 'a@b.co', password: 's3cure-pass' } }, res);
    assert.equal(res.statusCode, 200);
    assert.ok(res.body.token);
  });
  it('rejects wrong password and unknown email with 401', async () => {
    const handler = loginHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG });
    await registerHandler({ users, hasher: fakeHasher, signer: fakeSigner, config: CONFIG })(
      { body: { email: 'a@b.co', password: 's3cure-pass' } },
      fakeRes(),
    );
    const wrong = fakeRes();
    await handler({ body: { email: 'a@b.co', password: 'other-pass-1' } }, wrong);
    assert.equal(wrong.statusCode, 401);
    const unknown = fakeRes();
    await handler({ body: { email: 'nobody@b.co', password: 's3cure-pass' } }, unknown);
    assert.equal(unknown.statusCode, 401);
  });
  it('returns the profile without secrets, 404 when missing', async () => {
    await users.create({ email: 'a@b.co', passwordHash: 'h', name: 'A' });
    const res = fakeRes();
    await meHandler({ users })({ user: { id: 'u1' } }, res);
    assert.equal(res.body.user.email, 'a@b.co');
    assert.ok(!('passwordHash' in res.body.user));
    const missing = fakeRes();
    await meHandler({ users })({ user: { id: 'ghost' } }, missing);
    assert.equal(missing.statusCode, 404);
  });
});

function memoryRatings() {
  const rows = [];
  return {
    listByUser: async (userId) => rows.filter((r) => r.userId === userId),
    upsert: async (data) => {
      const existing = rows.find((r) => r.userId === data.userId && r.movieId === data.movieId);
      if (existing) {
        Object.assign(existing, data);
        return existing;
      }
      const row = { ...data };
      rows.push(row);
      return row;
    },
    remove: async (userId, movieId) => {
      const i = rows.findIndex((r) => r.userId === userId && r.movieId === movieId);
      if (i < 0) return false;
      rows.splice(i, 1);
      return true;
    },
  };
}

describe('ratings handlers', () => {
  it('adds, lists, updates, and deletes own ratings', async () => {
    const ratings = memoryRatings();
    const req = { user: { id: 'u1' }, body: { movieId: 101, score: 8 }, params: {} };
    const added = fakeRes();
    await putRating({ ratings })(req, added);
    assert.equal(added.statusCode, 201);

    const listed = fakeRes();
    await listRatings({ ratings })({ user: { id: 'u1' } }, listed);
    assert.equal(listed.body.items.length, 1);

    const removed = fakeRes();
    await deleteRating({ ratings })({ user: { id: 'u1' }, params: { movieId: '101' } }, removed);
    assert.equal(removed.statusCode, 204);

    const again = fakeRes();
    await deleteRating({ ratings })({ user: { id: 'u1' }, params: { movieId: '101' } }, again);
    assert.equal(again.statusCode, 404);
  });
  it('rejects out-of-range scores with 400', async () => {
    const res = fakeRes();
    await putRating({ ratings: memoryRatings() })(
      { user: { id: 'u1' }, body: { movieId: 101, score: 11 }, params: {} },
      res,
    );
    assert.equal(res.statusCode, 400);
  });
});

function memoryWatchlist() {
  const rows = [];
  return {
    listByUser: async (userId) => rows.filter((r) => r.userId === userId),
    add: async (userId, movieId) => {
      const existing = rows.find((r) => r.userId === userId && r.movieId === movieId);
      if (existing) return existing;
      const row = { userId, movieId };
      rows.push(row);
      return row;
    },
    remove: async (userId, movieId) => {
      const i = rows.findIndex((r) => r.userId === userId && r.movieId === movieId);
      if (i < 0) return false;
      rows.splice(i, 1);
      return true;
    },
  };
}

describe('watchlist handlers', () => {
  it('adds idempotently, lists, and removes', async () => {
    const watchlist = memoryWatchlist();
    const req = { user: { id: 'u1' }, body: { movieId: 101 }, params: {} };
    await addWatchlist({ watchlist })(req, fakeRes());
    const second = fakeRes();
    await addWatchlist({ watchlist })(req, second);
    assert.equal(second.statusCode, 201);

    const listed = fakeRes();
    await listWatchlist({ watchlist })({ user: { id: 'u1' } }, listed);
    assert.equal(listed.body.items.length, 1);

    const removed = fakeRes();
    await removeWatchlist({ watchlist })({ user: { id: 'u1' }, params: { movieId: '101' } }, removed);
    assert.equal(removed.statusCode, 204);
  });
  it('rejects invalid movie ids with 400 and missing entries with 404', async () => {
    const bad = fakeRes();
    await addWatchlist({ watchlist: memoryWatchlist() })(
      { user: { id: 'u1' }, body: { movieId: 'abc' }, params: {} },
      bad,
    );
    assert.equal(bad.statusCode, 400);
    const missing = fakeRes();
    await removeWatchlist({ watchlist: memoryWatchlist() })(
      { user: { id: 'u1' }, params: { movieId: '5' } },
      missing,
    );
    assert.equal(missing.statusCode, 404);
  });
});

describe('movies proxy', () => {
  it('forwards allowed paths with the internal key', async () => {
    let seen;
    const fetchImpl = async (url, opts) => {
      seen = { url, opts };
      return { status: 200, json: async () => ({ items: [] }) };
    };
    const res = fakeRes();
    await moviesProxy({ baseUrl: 'http://movies:8002', internalKey: 'k', fetchImpl })(
      { path: '/api/movies/search', url: '/api/movies/search?q=alpha' },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.equal(seen.url, 'http://movies:8002/movies/search?q=alpha');
    assert.equal(seen.opts.headers['X-Internal-Key'], 'k');
  });
  it('rejects non-movie paths and maps outages to 502', async () => {
    const res = fakeRes();
    await moviesProxy({ baseUrl: 'http://x', internalKey: 'k', fetchImpl: async () => ({}) })(
      { path: '/api/users/me', url: '/api/users/me' },
      res,
    );
    assert.equal(res.statusCode, 404);

    const down = fakeRes();
    await moviesProxy({ baseUrl: 'http://x', internalKey: 'k', fetchImpl: async () => { throw new Error('down'); } })(
      { path: '/api/movies', url: '/api/movies' },
      down,
    );
    assert.equal(down.statusCode, 502);
  });
});
