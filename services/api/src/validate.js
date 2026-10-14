'use strict';

/** Pure input validators (no dependencies). Each returns a string error or null. */

function validateEmail(email) {
  if (typeof email !== 'string' || email.trim() === '') return 'email is required';
  if (email.length > 254) return 'email is too long';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return 'email is invalid';
  return null;
}

function validatePassword(password) {
  if (typeof password !== 'string' || password === '') return 'password is required';
  if (password.length < 8) return 'password must be at least 8 characters';
  if (password.length > 128) return 'password is too long';
  return null;
}

function validateName(name) {
  if (name === undefined) return null;
  if (typeof name !== 'string' || name.trim() === '') return 'name must be a non-empty string';
  if (name.trim().length > 100) return 'name is too long';
  return null;
}

function validateMovieId(movieId) {
  const id = typeof movieId === 'string' ? Number(movieId) : movieId;
  if (!Number.isInteger(id) || id <= 0) return 'movieId must be a positive integer';
  return null;
}

function validateScore(score) {
  if (typeof score !== 'string' && typeof score !== 'number') return 'score is required';
  const n = Number(score);
  if (!Number.isFinite(n) || !Number.isInteger(n)) return 'score must be an integer';
  if (n < 1 || n > 10) return 'score must be between 1 and 10';
  return null;
}

function validateReview(review) {
  if (review === undefined) return null;
  if (typeof review !== 'string') return 'review must be a string';
  if (review.length > 2000) return 'review is too long';
  return null;
}

module.exports = {
  validateEmail,
  validatePassword,
  validateName,
  validateMovieId,
  validateScore,
  validateReview,
};
