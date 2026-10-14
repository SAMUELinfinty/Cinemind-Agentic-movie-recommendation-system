'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { cors } = require('../src/cors');

function fakeRes() {
  const headers = {};
  return {
    statusCode: 200,
    headers,
    ended: false,
    status(code) {
      this.statusCode = code;
      return this;
    },
    set(k, v) {
      this.headers[k] = v;
      return this;
    },
    end() {
      this.ended = true;
      return this;
    },
  };
}

describe('cors', () => {
  it('answers preflight with 204 and the calling origin', () => {
    const res = fakeRes();
    let nexted = false;
    cors({ origins: ['http://localhost:5173'] })(
      { method: 'OPTIONS', headers: { origin: 'http://localhost:5173' } },
      res,
      () => {
        nexted = true;
      },
    );
    assert.equal(res.statusCode, 204);
    assert.ok(res.ended && !nexted);
    assert.equal(res.headers['Access-Control-Allow-Origin'], 'http://localhost:5173');
    assert.ok(res.headers['Access-Control-Allow-Headers'].includes('Authorization'));
  });
  it('passes normal requests through with headers set', () => {
    const res = fakeRes();
    let nexted = false;
    cors({ origins: ['http://localhost:5173'] })(
      { method: 'GET', headers: { origin: 'http://localhost:5173' } },
      res,
      () => {
        nexted = true;
      },
    );
    assert.ok(nexted);
    assert.equal(res.headers['Access-Control-Allow-Origin'], 'http://localhost:5173');
  });
  it('gives no access headers to unlisted origins', () => {
    const res = fakeRes();
    let nexted = false;
    cors({ origins: ['http://localhost:5173'] })(
      { method: 'GET', headers: { origin: 'http://evil.example' } },
      res,
      () => {
        nexted = true;
      },
    );
    assert.ok(nexted);
    assert.ok(!('Access-Control-Allow-Origin' in res.headers));
  });
});
