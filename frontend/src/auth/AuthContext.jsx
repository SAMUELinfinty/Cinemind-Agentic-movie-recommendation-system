import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/auth.js';
import { ApiError, getToken } from '../api/client.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    authApi
      .me()
      .then((data) => setUser(data.user))
      .catch(() => authApi.logout())
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (creds) => {
    const data = await authApi.login(creds);
    setUser(data.user);
    return data;
  }, []);

  const register = useCallback(async (creds) => {
    const data = await authApi.register(creds);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside provider');
  return ctx;
}

export function useAuthedApi() {
  const { logout } = useAuth();
  return useCallback(
    async (fn) => {
      try {
        return await fn();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) logout();
        throw err;
      }
    },
    [logout],
  );
}
