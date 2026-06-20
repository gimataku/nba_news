import { useState, useCallback } from 'react';

export function useAuth() {
  const [token, setToken] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const login = useCallback(async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error('ログインに失敗しました');
    const data = await res.json();
    setToken(data.access_token);
    setIsAuthenticated(true);
    return data.access_token;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setIsAuthenticated(false);
  }, []);

  return { token, isAuthenticated, login, logout };
}
