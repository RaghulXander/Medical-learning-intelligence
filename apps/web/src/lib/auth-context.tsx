'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserProfile, AuthSessionResponse } from '@medical/shared';
import {
  authApi,
  setAuthTokenGetter,
  setGuestTokenGetter,
  setUnauthorizedHandler,
} from '@medical/api-client';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  guestSessionToken: string | null;
  login: (email: string, password: string) => Promise<AuthSessionResponse>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    target_exam?: string;
    residency_stage?: string;
    medical_college?: string;
  }) => Promise<AuthSessionResponse>;
  googleSignIn: (idToken: string) => Promise<AuthSessionResponse>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  updateProfile: (profile: Partial<UserProfile>) => void;
  getOrCreateGuestSession: () => Promise<string>;
  mergeGuestSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [guestSessionToken, setGuestSessionToken] = useState<string | null>(null);

  // Initialize auth & client token provider
  useEffect(() => {
    // Register token getter on isomorphic API client
    setAuthTokenGetter(() =>
      typeof window !== 'undefined' ? localStorage.getItem('docedge_access_token') : null
    );
    setGuestTokenGetter(() =>
      typeof window !== 'undefined' ? localStorage.getItem('docedge_guest_token') : null
    );
    setUnauthorizedHandler(async () => {
      const refreshToken = localStorage.getItem('docedge_refresh_token');
      if (!refreshToken) return null;

      try {
        const refreshed = await authApi.refreshToken(refreshToken);
        localStorage.setItem('docedge_access_token', refreshed.access_token);
        localStorage.setItem('docedge_refresh_token', refreshed.refresh_token);
        return refreshed.access_token;
      } catch (err) {
        console.warn('Session refresh failed:', err);
        localStorage.removeItem('docedge_access_token');
        localStorage.removeItem('docedge_refresh_token');
        setUser(null);
        return null;
      }
    });

    // Load guest token from storage if present
    if (typeof window !== 'undefined') {
      const storedGuest = localStorage.getItem('docedge_guest_token');
      if (storedGuest) {
        setGuestSessionToken(storedGuest);
      }
    }

    async function loadUser() {
      try {
        const token = localStorage.getItem('docedge_access_token');
        if (token) {
          const profile = await authApi.getMe();
          setUser(profile);
        }
      } catch (err) {
        console.warn('Session expired or unauthenticated:', err);
        localStorage.removeItem('docedge_access_token');
        localStorage.removeItem('docedge_refresh_token');
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    void loadUser();

    return () => setUnauthorizedHandler(undefined);
  }, []);

  const saveTokens = (access: string, refresh: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('docedge_access_token', access);
      localStorage.setItem('docedge_refresh_token', refresh);
    }
  };

  const getOrCreateGuestSession = async (): Promise<string> => {
    if (guestSessionToken) return guestSessionToken;
    try {
      const res = await authApi.createGuestSession();
      setGuestSessionToken(res.guest_session_token);
      if (typeof window !== 'undefined') {
        localStorage.setItem('docedge_guest_token', res.guest_session_token);
      }
      return res.guest_session_token;
    } catch (err) {
      console.error('Failed to create guest session:', err);
      return '';
    }
  };

  const mergeGuestSession = async () => {
    const token = guestSessionToken || (typeof window !== 'undefined' ? localStorage.getItem('docedge_guest_token') : null);
    if (!token) return;

    try {
      await authApi.mergeGuestSession(token);
      setGuestSessionToken(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('docedge_guest_token');
      }
    } catch (err) {
      console.warn('Guest merge notice:', err);
    }
  };

  const login = async (email: string, password: string): Promise<AuthSessionResponse> => {
    const res = await authApi.login({ email, password });
    saveTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    await mergeGuestSession();
    return res;
  };

  const register = async (payload: {
    email: string;
    password: string;
    name: string;
    target_exam?: string;
    residency_stage?: string;
    medical_college?: string;
  }): Promise<AuthSessionResponse> => {
    const res = await authApi.register(payload);
    saveTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    await mergeGuestSession();
    return res;
  };

  const googleSignIn = async (idToken: string): Promise<AuthSessionResponse> => {
    const res = await authApi.googleSignIn(idToken);
    saveTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    await mergeGuestSession();
    return res;
  };

  const logout = async () => {
    const refresh = typeof window !== 'undefined' ? localStorage.getItem('docedge_refresh_token') : null;
    if (refresh) {
      try {
        await authApi.logout(refresh);
      } catch (err) {
        console.warn('Logout notice:', err);
      }
    }
    if (typeof window !== 'undefined') {
      localStorage.removeItem('docedge_access_token');
      localStorage.removeItem('docedge_refresh_token');
    }
    setUser(null);
  };

  const logoutAll = async () => {
    try {
      await authApi.logoutAll();
    } catch (err) {
      console.warn('Logout all notice:', err);
    }
    if (typeof window !== 'undefined') {
      localStorage.removeItem('docedge_access_token');
      localStorage.removeItem('docedge_refresh_token');
    }
    setUser(null);
  };

  const updateProfile = (profile: Partial<UserProfile>) => {
    // Use the latest context state instead of the value captured by this render.
    // Onboarding can finish while the initial /me request is still settling.
    setUser((currentUser) =>
      currentUser ? { ...currentUser, ...profile } : (profile as UserProfile)
    );
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        guestSessionToken,
        login,
        register,
        googleSignIn,
        logout,
        logoutAll,
        updateProfile,
        getOrCreateGuestSession,
        mergeGuestSession,
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
