import { request, setToken } from './client.js';

export const authApi = {
  async register({ email, password, name }) {
    const data = await request('/api/auth/register', { method: 'POST', body: { email, password, name } });
    setToken(data.token);
    return data;
  },
  async login({ email, password }) {
    const data = await request('/api/auth/login', { method: 'POST', body: { email, password } });
    setToken(data.token);
    return data;
  },
  me() {
    return request('/api/users/me', { auth: true });
  },
  logout() {
    setToken(null);
  },
};
