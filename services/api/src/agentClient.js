'use strict';

/**
 * Internal agent-service client. Express is the only caller of :8001 —
 * the browser never sees the agent URL or the internal key.
 *
 * Every failure (network, timeout, non-200, malformed body) maps to a
 * generic "Agent service unavailable" error so no internal details leak.
 * `fetchImpl` is injectable for tests (defaults to global fetch).
 */

class AgentError extends Error {
  constructor(message = 'Agent service unavailable') {
    super(message);
    this.name = 'AgentError';
  }
}

function agentHeaders(internalKey) {
  return { 'Content-Type': 'application/json', 'X-Internal-Key': internalKey };
}

async function callAgent(
  { baseUrl, internalKey, timeoutMs, fetchImpl },
  { message, limit, userToken },
) {
  const doFetch = fetchImpl ?? globalThis.fetch;
  const body = { message, limit };
  if (userToken) body.user_token = userToken;

  let res;
  try {
    res = await doFetch(`${baseUrl}/chat`, {
      method: 'POST',
      headers: agentHeaders(internalKey),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new AgentError();
  }

  let data;
  try {
    data = await res.json();
  } catch {
    throw new AgentError();
  }
  if (!res || res.status !== 200 || !data || typeof data.response !== 'string') {
    throw new AgentError();
  }
  const movieIds = Array.isArray(data.movie_ids)
    ? data.movie_ids.filter((id) => Number.isInteger(id) && id > 0)
    : [];
  return { response: data.response, movieIds };
}

module.exports = { callAgent, AgentError };
