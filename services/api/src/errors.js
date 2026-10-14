'use strict';

/**
 * Consistent error responses: { error: { code, message } }.
 * Never include stacks, secrets, or driver internals in responses.
 */

function errorBody(code, message) {
  return { error: { code, message } };
}

function sendError(res, status, code, message) {
  return res.status(status).json(errorBody(code, message));
}

function validationError(res, message) {
  return sendError(res, 400, 'validation_error', message);
}

function unauthorized(res, message = 'Authentication required') {
  return sendError(res, 401, 'unauthorized', message);
}

function forbidden(res, message = 'Forbidden') {
  return sendError(res, 403, 'forbidden', message);
}

function notFound(res, message = 'Not found') {
  return sendError(res, 404, 'not_found', message);
}

function conflict(res, message) {
  return sendError(res, 409, 'conflict', message);
}

function internalError(res) {
  return sendError(res, 500, 'internal_error', 'Something went wrong');
}

module.exports = {
  errorBody,
  sendError,
  validationError,
  unauthorized,
  forbidden,
  notFound,
  conflict,
  internalError,
};
