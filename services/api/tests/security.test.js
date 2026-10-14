'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { rateLimit } = require('../src/rateLimit');
const { isAllowedMoviePath, moviesProxy } = require('../src/handlers/moviesProxy');
const { callAgent } = require('../src/agentClient');

function fakeRes() {
  const headers = {};
  return {
    statusCode: 200,
    body: null,
    headers,
    status(code) {
      this.statusCode = code;
      return this;
    },
    set(k, v) {
      this.headers[k] = v;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
}

function req(ip = '1.1.1.1') {
  return { ip, headers: {}, socket: {} };
}

describe('rate limiter', () => {
  it('allows under the limit then answers 429 with Retry-After', () => {
    let now = 0;
    const limiter = rateLimit({ windowMs: 60000, max: 2, now: () => now });
    let passed = 0;
    const next = () => {
      passed += 1;
    };
    limiter(req(), fakeRes(), next);
    limiter(req(), fakeRes(), next);
    assert.equal(passed, 2);

    const res = fakeRes();
    limiter(req(), res, next);
    assert.equal(passed, 2);
    assert.equal(res.statusCode, 429);
    assert.equal(res.body.error.code, 'rate_limited');
    assert.ok(res.headers['Retry-After']);
  });
  it('resets after the window and isolates clients', () => {
    let now = 0;
    const limiter = rateLimit({ windowMs: 1000, max: 1, now: () => now });
    let passed = 0;
    const next = () => {
      passed += 1;
    };
    limiter(req('a'), fakeRes(), next);
    limiter(req('b'), fakeRes(), next); // different IP unaffected
    assert.equal(passed, 2);
    now = 2000; // window elapsed
    limiter(req('a'), fakeRes(), next);
    assert.equal(passed, 3);
  });
});

describe('public-route audit: internal paths stay unreachable', () => {
  it('rejects docs, schemas, health, and non-numeric ids', () => {
    for (const p of ['/docs', '/openapi.json', '/health', '/', '/movies/abc', '/internal/status', '/movies/search/extra']) {
      assert.equal(isAllowedMoviePath(p), false, p);
    }
    for (const p of ['/movies', '/movies/search', '/discover', '/trending', '/movies/101', '/movies/101/similar']) {
      assert.equal(isAllowedMoviePath(p), true, p);
    }
  });
  it('proxy forwards a timeout signal and only the internal header', async () => {
    let seen;
    const fetchImpl = async (url, opts) => {
      seen = opts;
      return { status: 200, json: async () => ({ ok: true }) };
    };
    const res = fakeRes();
    await moviesProxy({ baseUrl: 'http://m:8002', internalKey: 'k', timeoutMs: 1500, fetchImpl })(
      { path: '/api/movies', url: '/api/movies' },
      res,
    );
    assert.equal(res.statusCode, 200);
    assert.deepEqual(Object.keys(seen.headers), ['X-Internal-Key']);
    assert.ok(seen.signal);
  });
  it('agent client never puts credentials in the body', async () => {
    let seen;
    const fetchImpl = async (url, opts) => {
      seen = JSON.parse(opts.body);
      return { status: 200, json: async () => ({ response: 'r', movie_ids: [] }) };
    };
    await callAgent(
      { baseUrl: 'http://a:8001', internalKey: 'SECRET', timeoutMs: 1000, fetchImpl },
      { message: 'hi', limit: 5, userToken: 'tok' },
    );
    const body = JSON.stringify(seen);
    assert.ok(!body.includes('SECRET'));
    assert.deepEqual(Object.keys(seen).sort(), ['limit', 'message', 'user_token']);
  });
});
