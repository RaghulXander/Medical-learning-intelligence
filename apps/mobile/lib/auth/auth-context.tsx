/**
 * apps/mobile/lib/auth/auth-context.tsx
 *
 * Mobile Authentication Context & Session Management Provider.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { UserProfile, AuthSessionResponse } from '@medical/shared';
import { authApi, setAuthTokenGetter } from '@medical/api-client';
import { SecureStorage } from '../storage/secure-store';

const TOKEN_KEY = 'docedge_mobile_token';
const USER_KEY = 'docedge_mobile_user';

interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  target_exam?: string;
  residency_stage?: string;
  medical_college?: string;
  primary_speciality?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<AuthSessionResponse>;
  register: (payload: RegisterPayload) => Promise<AuthSessionResponse>;
  googleSignIn: (tokenOrEmail: string) => Promise<AuthSessionResponse>;
  updateProfile: (updated: Partial<UserProfile>) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Hook global api-client token getter
  useEffect(() => {
    setAuthTokenGetter(() => token);
  }, [token]);

  // Hydrate session from secure storage on startup
  useEffect(() => {
    async function hydrate() {
      try {
        const storedToken = await SecureStorage.getItem(TOKEN_KEY);
        const storedUser = await SecureStorage.getItem(USER_KEY);

        if (storedToken) {
          setToken(storedToken);
          if (storedUser) {
            setUser(JSON.parse(storedUser));
          }
          // Refresh user profile from backend
          try {
            const freshUser = await authApi.getMe();
            setUser(freshUser);
            await SecureStorage.setItem(USER_KEY, JSON.stringify(freshUser));
          } catch {
            // Use cached profile if offline
          }
        }
      } catch (err) {
        console.warn('Mobile auth hydration notice:', err);
      } finally {
        setIsLoading(false);
      }
    }

    hydrate();
  }, []);

  const saveSession = async (accessToken: string, userData: UserProfile) => {
    setToken(accessToken);
    setUser(userData);
    await SecureStorage.setItem(TOKEN_KEY, accessToken);
    await SecureStorage.setItem(USER_KEY, JSON.stringify(userData));
  };

  const login = async (email: string, pass: string) => {
    const res = await authApi.login({ email, password: pass });
    await saveSession(res.access_token, res.user);
    return res;
  };

  const register = async (payload: RegisterPayload) => {
    const res = await authApi.register(payload);
    await saveSession(res.access_token, res.user);
    return res;
  };

  const googleSignIn = async (tokenOrEmail: string) => {
    const res = await authApi.googleSignIn(tokenOrEmail);
    await saveSession(res.access_token, res.user);
    return res;
  };

  const updateProfile = useCallback(async (updated: Partial<UserProfile>) => {
    setUser((prev: UserProfile | null) => {
      if (!prev) return null;
      const merged = { ...prev, ...updated };
      SecureStorage.setItem(USER_KEY, JSON.stringify(merged)).catch(() => {});
      return merged;
    });
  }, []);

  const logout = async () => {
    setToken(null);
    setUser(null);
    await SecureStorage.removeItem(TOKEN_KEY);
    await SecureStorage.removeItem(USER_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        googleSignIn,
        updateProfile,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
