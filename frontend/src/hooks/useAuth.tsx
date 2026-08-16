import { createContext, useContext, useMemo, useState } from 'react';
import { login as loginRequest, register as registerRequest } from '../services/api';

interface AuthContextValue {
  token: string | null;
  username: string | null;
  role: string | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(() => localStorage.getItem('docutrust_token'));
  const [username, setUsername] = useState(() => localStorage.getItem('docutrust_user'));
  const [role, setRole] = useState(() => localStorage.getItem('docutrust_role'));
  const applySession = (result: { access_token: string; username: string; role: string }) => {
    localStorage.setItem('docutrust_token', result.access_token);
    localStorage.setItem('docutrust_user', result.username);
    localStorage.setItem('docutrust_role', result.role);
    setToken(result.access_token);
    setUsername(result.username);
    setRole(result.role);
  };
  const value = useMemo<AuthContextValue>(() => ({
    token,
    username,
    role,
    isAdmin: role === 'admin',
    isAuthenticated: Boolean(token),
    async login(user, password) { applySession(await loginRequest(user, password)); },
    async register(user, password) { applySession(await registerRequest(user, password)); },
    logout() {
      localStorage.removeItem('docutrust_token');
      localStorage.removeItem('docutrust_user');
      localStorage.removeItem('docutrust_role');
      setToken(null); setUsername(null); setRole(null);
    },
  }), [token, username, role]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error('useAuth must be used inside AuthProvider'); return context; }
