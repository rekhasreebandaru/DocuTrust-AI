import { createContext, useContext, useMemo, useState } from 'react';
import { login as loginRequest } from '../services/api';

interface AuthContextValue { token: string | null; username: string | null; isAuthenticated: boolean; login: (username: string, password: string) => Promise<void>; logout: () => void; }
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(() => localStorage.getItem('docutrust_token'));
  const [username, setUsername] = useState(() => localStorage.getItem('docutrust_user'));
  const value = useMemo<AuthContextValue>(() => ({ token, username, isAuthenticated: Boolean(token), async login(user, password) { const result = await loginRequest(user, password); localStorage.setItem('docutrust_token', result.access_token); localStorage.setItem('docutrust_user', result.username); setToken(result.access_token); setUsername(result.username); }, logout() { localStorage.removeItem('docutrust_token'); localStorage.removeItem('docutrust_user'); setToken(null); setUsername(null); } }), [token, username]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error('useAuth must be used inside AuthProvider'); return context; }
