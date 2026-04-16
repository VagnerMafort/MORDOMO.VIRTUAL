import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);
const API = process.env.REACT_APP_BACKEND_URL + '/api';

function getStoredTokens() {
  return {
    access: localStorage.getItem('nc_access_token'),
    refresh: localStorage.getItem('nc_refresh_token'),
  };
}

function storeTokens(access, refresh) {
  localStorage.setItem('nc_access_token', access);
  if (refresh) localStorage.setItem('nc_refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('nc_access_token');
  localStorage.removeItem('nc_refresh_token');
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = not auth
  const [loading, setLoading] = useState(true);

  const api = useMemo(() => {
    const instance = axios.create({ baseURL: API });

    instance.interceptors.request.use(config => {
      const token = localStorage.getItem('nc_access_token');
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });

    instance.interceptors.response.use(
      res => res,
      async err => {
        const orig = err.config;
        if (err.response?.status === 401 && !orig._retry && !orig.url?.includes('/auth/')) {
          orig._retry = true;
          const refresh = localStorage.getItem('nc_refresh_token');
          if (refresh) {
            try {
              const { data } = await axios.post(`${API}/auth/refresh`, { refresh_token: refresh });
              storeTokens(data.access_token, null);
              orig.headers.Authorization = `Bearer ${data.access_token}`;
              return instance(orig);
            } catch {
              clearTokens();
            }
          }
        }
        return Promise.reject(err);
      }
    );

    return instance;
  }, []);

  const checkAuth = useCallback(async () => {
    const { access } = getStoredTokens();
    if (!access) { setUser(false); setLoading(false); return; }
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch {
      clearTokens();
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await axios.post(`${API}/auth/login`, { email, password });
    storeTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    return data.user;
  };

  const register = async (email, password, name) => {
    const { data } = await axios.post(`${API}/auth/register`, { email, password, name });
    storeTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post('/auth/logout'); } catch {}
    clearTokens();
    setUser(false);
  };

  const getToken = () => localStorage.getItem('nc_access_token');

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, api, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
