/**
 * packages/api-client/src/auth.ts
 *
 * Authentication, Session & Identity API endpoints.
 */

import { MedicalApiClient, defaultClient } from './client';
import {
  AuthSessionResponse,
  GuestSessionResponse,
  MergeGuestResponse,
  PasswordEntropyResult,
  UserProfile,
} from '@medical/shared';

export class AuthApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  public async createGuestSession(): Promise<GuestSessionResponse> {
    return this.client.request<GuestSessionResponse>('/api/auth/guest-session', {
      method: 'POST',
    });
  }

  public async googleSignIn(idToken: string): Promise<AuthSessionResponse> {
    return this.client.request<AuthSessionResponse>('/api/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken }),
    });
  }

  public async register(payload: {
    email: string;
    password: string;
    name: string;
    target_exam?: string;
    residency_stage?: string;
    medical_college?: string;
  }): Promise<AuthSessionResponse> {
    return this.client.request<AuthSessionResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async login(payload: { email: string; password: string }): Promise<AuthSessionResponse> {
    return this.client.request<AuthSessionResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async refreshToken(refreshToken: string): Promise<{ access_token: string; refresh_token: string; token_type: string }> {
    return this.client.request('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  public async logout(refreshToken: string): Promise<{ success: boolean; message: string }> {
    return this.client.request('/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  public async logoutAll(): Promise<{ success: boolean; revoked_sessions_count: number }> {
    return this.client.request('/api/auth/logout-all', {
      method: 'POST',
    });
  }

  public async setPassword(password: string): Promise<{ success: boolean; message: string }> {
    return this.client.request('/api/auth/set-password', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  public async generatePassword(length: number = 20): Promise<{ password: string; entropy: PasswordEntropyResult }> {
    return this.client.request(`/api/auth/generate-password?length=${length}`, {
      method: 'GET',
    });
  }

  public async evaluatePassword(password: string): Promise<PasswordEntropyResult> {
    return this.client.request<PasswordEntropyResult>('/api/auth/evaluate-password', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  public async getMe(): Promise<UserProfile> {
    return this.client.request<UserProfile>('/api/auth/me', {
      method: 'GET',
    });
  }

  public async mergeGuestSession(guestSessionToken: string): Promise<MergeGuestResponse> {
    return this.client.request<MergeGuestResponse>('/api/auth/merge-guest', {
      method: 'POST',
      body: JSON.stringify({ guest_session_token: guestSessionToken }),
    });
  }

  public async deleteAccount(): Promise<{ success: boolean; message: string }> {
    return this.client.request<{ success: boolean; message: string }>('/api/auth/me', {
      method: 'DELETE',
    });
  }
}

export const authApi = new AuthApi();
