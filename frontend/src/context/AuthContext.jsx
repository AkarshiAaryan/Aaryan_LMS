import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('guardslm_token') || null);
  const [loading, setLoading] = useState(true);

  // Load user profile on startup if token is present
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('guardslm_token');
      if (storedToken) {
        try {
          const res = await api.get('/auth/me');
          setUser(res.data);
          setToken(storedToken);
        } catch (err) {
          console.error("Token verification failed:", err);
          localStorage.removeItem('guardslm_token');
          localStorage.removeItem('guardslm_user');
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    const { access_token, user: userData } = res.data;
    localStorage.setItem('guardslm_token', access_token);
    localStorage.setItem('guardslm_user', JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('guardslm_token');
      localStorage.removeItem('guardslm_user');
      setUser(null);
      setToken(null);
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isProfessor: user?.role === 'professor' || user?.role === 'teacher',
    isTeacher: user?.role === 'professor' || user?.role === 'teacher',
    isTA: user?.role === 'ta',
    isStaff: user?.role === 'admin' || user?.role === 'professor' || user?.role === 'teacher' || user?.role === 'ta',
    isStudent: user?.role === 'student',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
