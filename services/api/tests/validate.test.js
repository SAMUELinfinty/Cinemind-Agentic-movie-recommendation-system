'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const {
  validateEmail,
  validatePassword,
  validateName,
  validateMovieId,
  validateScore,
  validateReview,
} = require('../src/validate');
const { errorBody } = require('../src/errors');

describe('validate', () => {
  it('accepts a well-formed email', () => {
    assert.equal(validateEmail('Ada@Example.com'), null);
  });
  it('rejects missing and malformed emails', () => {
    assert.ok(validateEmail(''));
    assert.ok(validateEmail('not-an-email'));
    assert.ok(validateEmail('a@b'));
    assert.ok(validateEmail(null));
  });
  it('requires passwords of at least 8 characters', () => {
    assert.equal(validatePassword('s3cure-pass'), null);
    assert.ok(validatePassword('short'));
    assert.ok(validatePassword(''));
  });
  it('validates optional names', () => {
    assert.equal(validateName(undefined), null);
    assert.equal(validateName('Ada'), null);
    assert.ok(validateName('   '));
  });
  it('validates positive integer movie ids', () => {
    assert.equal(validateMovieId(1115544), null);
    assert.equal(validateMovieId('42'), null);
    assert.ok(validateMovieId(0));
    assert.ok(validateMovieId(-3));
    assert.ok(validateMovieId(1.5));
    assert.ok(validateMovieId('abc'));
  });
  it('validates integer scores 1..10', () => {
    assert.equal(validateScore(1), null);
    assert.equal(validateScore(10), null);
    assert.ok(validateScore(0));
    assert.ok(validateScore(11));
    assert.ok(validateScore(7.5));
    assert.ok(validateScore(undefined));
  });
  it('validates optional reviews', () => {
    assert.equal(validateReview(undefined), null);
    assert.equal(validateReview('loved it'), null);
    assert.ok(validateReview('x'.repeat(2001)));
  });
});

describe('error envelope', () => {
  it('always uses { error: { code, message } } without internals', () => {
    const body = errorBody('validation_error', 'email is invalid');
    assert.deepEqual(body, { error: { code: 'validation_error', message: 'email is invalid' } });
    assert.ok(!('stack' in body) && !JSON.stringify(body).includes('secret'));
  });
});
