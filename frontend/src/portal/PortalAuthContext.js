import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const PortalAuthContext = createContext(null);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const PortalAuthProvider = ({ children }) => {
  const [customer, setCustomer] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('portal_token'));
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async (t) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCustomer(data);
      } else {
        localStorage.removeItem('portal_token');
        setToken(null);
        setCustomer(null);
      }
    } catch {
      setCustomer(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) fetchMe(token);
    else setLoading(false);
  }, [token, fetchMe]);

  const login = async (email, password) => {
    const res = await fetch(`${BACKEND_URL}/api/portal/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { throw new Error(text || 'Login failed'); }
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    localStorage.setItem('portal_token', data.token);
    setToken(data.token);
    setCustomer({ customer_id: data.customer_id, name: data.name, email: data.email });
    return data;
  };

  const register = async (name, email, password) => {
    const res = await fetch(`${BACKEND_URL}/api/portal/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { throw new Error(text || 'Registration failed'); }
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    localStorage.setItem('portal_token', data.token);
    setToken(data.token);
    setCustomer({ customer_id: data.customer_id, name: data.name, email: data.email });
    return data;
  };

  const logout = () => {
    const t = localStorage.getItem('portal_token');
    if (t) {
      fetch(`${BACKEND_URL}/api/portal/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${t}` },
      }).catch(() => {});
    }
    localStorage.removeItem('portal_token');
    setToken(null);
    setCustomer(null);
  };

  return (
    <PortalAuthContext.Provider value={{ customer, token, loading, login, register, logout }}>
      {children}
    </PortalAuthContext.Provider>
  );
};

export const usePortalAuth = () => useContext(PortalAuthContext);
