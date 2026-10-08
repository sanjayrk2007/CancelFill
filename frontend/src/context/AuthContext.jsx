import { useState, useEffect } from 'react';
import { AuthContext } from './AuthContextDef';
import client from '../api/client';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')));

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }

    let isCurrent = true;

    client
      .get('/api/v1/auth/me')
      .then((response) => {
        if (!isCurrent) return;
        setUser(response.data);
        setRole(response.data.role);
      })
      .catch(() => {
        if (!isCurrent) return;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setUser(null);
        setRole(null);
      })
      .finally(() => {
        if (!isCurrent) return;
        setLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const login = async (email, password) => {
    const response = await client.post('/api/v1/auth/login', { email, password });
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);

    const meResponse = await client.get('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    const userData = meResponse.data;
    setUser(userData);
    setRole(userData.role);
    return userData;
  };

  const register = async ({ email, password, name, role: userRole }) => {
    await client.post('/api/v1/auth/register', {
      email,
      password,
      name,
      role: userRole,
    });
    return await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setRole(null);
  };

  const value = {
    user,
    role,
    loading,
    login,
    logout,
    register,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext };
export default AuthProvider;
