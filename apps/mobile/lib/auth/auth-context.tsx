/**
 * apps/mobile/lib/auth/auth-context.tsx
 *
 * Mobile Authentication Context & Session Management Provider.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { UserProfile, AuthSessionResponse } from '@medical/shared';
import { authApi, setAuthTokenGetter, setUnauthorizedHandler } from '@medical/api-client';
import { SecureStorage } from '../storage/secure-store';

const TOKEN_KEY = 'docedge_mobile_token';
const REFRESH_KEY = 'docedge_mobile_refresh_token';
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

  // Register unauthorized 401 automatic token refresh handler on api-client
  useEffect(() => {
    setUnauthorizedHandler(async () => {
      const storedRefresh = await SecureStorage.getItem(REFRESH_KEY);
      if (!storedRefresh) return null;

      try {
        const refreshed = await authApi.refreshToken(storedRefresh);
        setToken(refreshed.access_token);
        await SecureStorage.setItem(TOKEN_KEY, refreshed.access_token);
        await SecureStorage.setItem(REFRESH_KEY, refreshed.refresh_token);
        return refreshed.access_token;
      } catch (err) {
        console.warn('Mobile token refresh failed:', err);
        setToken(null);
        setUser(null);
        await SecureStorage.removeItem(TOKEN_KEY);
        await SecureStorage.removeItem(REFRESH_KEY);
        await SecureStorage.removeItem(USER_KEY);
        return null;
      }
    });

    return () => {
      setUnauthorizedHandler(undefined);
    };
  }, []);

  // Hydrate session from secure storage on startup
  useEffect(() => {
    async function hydrate() {
      try {
        const storedToken = await SecureStorage.getItem(TOKEN_KEY);
        const storedRefresh = await SecureStorage.getItem(REFRESH_KEY);
        const storedUser = await SecureStorage.getItem(USER_KEY);

        if (storedUser) {
          try {
            setUser(JSON.parse(storedUser));
          } catch {}
        }

        if (storedToken) {
          setToken(storedToken);
          try {
            const freshUser = await authApi.getMe();
            setUser(freshUser);
            await SecureStorage.setItem(USER_KEY, JSON.stringify(freshUser));
          } catch (err: any) {
            // If access token expired, attempt direct silent refresh
            if (storedRefresh) {
              try {
                const refreshed = await authApi.refreshToken(storedRefresh);
                setToken(refreshed.access_token);
                await SecureStorage.setItem(TOKEN_KEY, refreshed.access_token);
                await SecureStorage.setItem(REFRESH_KEY, refreshed.refresh_token);
                const freshUser = await authApi.getMe();
                setUser(freshUser);
                await SecureStorage.setItem(USER_KEY, JSON.stringify(freshUser));
              } catch (refreshErr) {
                console.warn('Hydration token refresh expired:', refreshErr);
              }
            }
          }
        } else if (storedRefresh) {
          // No access token cached, but refresh token exists: rotate immediately
          try {
            const refreshed = await authApi.refreshToken(storedRefresh);
            setToken(refreshed.access_token);
            await SecureStorage.setItem(TOKEN_KEY, refreshed.access_token);
            await SecureStorage.setItem(REFRESH_KEY, refreshed.refresh_token);
            const freshUser = await authApi.getMe();
            setUser(freshUser);
            await SecureStorage.setItem(USER_KEY, JSON.stringify(freshUser));
          } catch (err) {
            console.warn('Initial refresh token bootstrap failed:', err);
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

  const saveSession = async (accessToken: string, refreshToken: string, userData: UserProfile) => {
    setToken(accessToken);
    setUser(userData);
    await SecureStorage.setItem(TOKEN_KEY, accessToken);
    await SecureStorage.setItem(REFRESH_KEY, refreshToken);
    await SecureStorage.setItem(USER_KEY, JSON.stringify(userData));
  };

  const login = async (email: string, pass: string) => {
    const res = await authApi.login({ email, password: pass });
    await saveSession(res.access_token, res.refresh_token, res.user);
    return res;
  };

  const register = async (payload: RegisterPayload) => {
    const res = await authApi.register(payload);
    await saveSession(res.access_token, res.refresh_token, res.user);
    return res;
  };

  const googleSignIn = async (tokenOrEmail: string) => {
    const res = await authApi.googleSignIn(tokenOrEmail);
    await saveSession(res.access_token, res.refresh_token, res.user);
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
    try {
      const storedRefresh = await SecureStorage.getItem(REFRESH_KEY);
      if (storedRefresh) {
        await authApi.logout(storedRefresh).catch(() => {});
      }
    } catch {}

    try {
      const { GoogleSignin } = await import('@react-native-google-signin/google-signin');
      await GoogleSignin.signOut().catch(() => {});
    } catch {}

    setToken(null);
    setUser(null);
    await SecureStorage.removeItem(TOKEN_KEY);
    await SecureStorage.removeItem(REFRESH_KEY);
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
