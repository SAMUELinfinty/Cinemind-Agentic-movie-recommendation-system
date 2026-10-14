const BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:5000').replace(/\/$/, '');

let token = null;
export const setToken = (t) => {
  token = t;
};
export const getToken = () => token;

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function request(path, { method = 'GET', body, auth = false, timeoutMs = 30000 } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the CineMind server');
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    throw new ApiError(res.status, 'bad_response', 'Unexpected server response');
  }
  if (!res.ok) {
    const err = data?.error ?? {};
    throw new ApiError(res.status, err.code ?? 'request_failed', err.message ?? 'Something went wrong');
  }
  return data;
}
