'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { requireAuth, requireInternalKey } = require('../src/middleware');

function fakeRes() {
  return {
    statusCode: null,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
}

describe('requireAuth', () => {
  const verify = (token) => {
    if (token !== 'good-token') throw new Error('bad token');
    return { sub: 'u1', email: 'ada@example.com' };
  };

  it('attaches req.user and calls next on a valid token', () => {
    const req = { headers: { authorization: 'Bearer good-token' } };
    const res = fakeRes();
    let nexted = false;
    requireAuth({ verify, secret: 's' })(req, res, () => {
      nexted = true;
    });
    assert.ok(nexted);
    assert.deepEqual(req.user, { id: 'u1', email: 'ada@example.com' });
  });
  it('returns 401 when the header is missing or malformed', () => {
    for (const headers of [{}, { authorization: '' }, { authorization: 'Token x' }]) {
      const res = fakeRes();
      let nexted = false;
      requireAuth({ verify, secret: 's' })({ headers }, res, () => {
        nexted = true;
      });
      assert.equal(res.statusCode, 401);
      assert.ok(!nexted);
    }
  });
  it('returns 401 on an invalid token', () => {
    const res = fakeRes();
    let nexted = false;
    requireAuth({ verify, secret: 's' })(
      { headers: { authorization: 'Bearer bad-token' } },
      res,
      () => {
        nexted = true;
      },
    );
    assert.equal(res.statusCode, 401);
    assert.ok(!nexted);
  });
});

describe('requireInternalKey', () => {
  it('calls next on a matching key', () => {
    const res = fakeRes();
    let nexted = false;
    requireInternalKey({ expected: 'k' })(
      { headers: { 'x-internal-key': 'k' } },
      res,
      () => {
        nexted = true;
      },
    );
    assert.ok(nexted);
  });
  it('returns 401 when missing, 403 when wrong', () => {
    const missing = fakeRes();
    requireInternalKey({ expected: 'k' })({ headers: {} }, missing, () => {});
    assert.equal(missing.statusCode, 401);

    const wrong = fakeRes();
    let nexted = false;
    requireInternalKey({ expected: 'k' })(
      { headers: { 'x-internal-key': 'nope' } },
      wrong,
      () => {
        nexted = true;
      },
    );
    assert.equal(wrong.statusCode, 403);
    assert.ok(!nexted);
  });
});
