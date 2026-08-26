/**
 * packages/api-client/src/admin.ts
 *
 * Admin, User Governance & RBAC API client.
 */

import { MedicalApiClient, defaultClient } from './client';
import { ListUsersResponse } from '@medical/shared';

export class AdminApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  public async listUsers(params?: {
    search?: string;
    role?: string;
    page?: number;
    limit?: number;
  }): Promise<ListUsersResponse> {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.role) qs.set('role', params.role);
    if (params?.page) qs.set('page', String(params.page));
    if (params?.limit) qs.set('limit', String(params.limit));
    const queryStr = qs.toString() ? `?${qs.toString()}` : '';

    return this.client.request<ListUsersResponse>(`/api/admin/users${queryStr}`, {
      method: 'GET',
    });
  }

  public async updateUserRole(
    userId: string,
    role: string
  ): Promise<{ success: boolean; user_id: string; email: string; new_role: string }> {
    return this.client.request(`/api/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  public async updateUserSubscription(
    userId: string,
    isSubscribed: boolean
  ): Promise<{ success: boolean; user_id: string; email: string; is_subscribed: boolean }> {
    return this.client.request(`/api/admin/users/${userId}/subscription`, {
      method: 'PATCH',
      body: JSON.stringify({ is_subscribed: isSubscribed }),
    });
  }

  public async getStats(): Promise<{
    total_users: number;
    total_questions: number;
    total_attempts: number;
    questions_by_status: Record<string, number>;
    users_by_role: Record<string, number>;
  }> {
    return this.client.request('/api/admin/stats', {
      method: 'GET',
    });
  }
}

export const adminApi = new AdminApi();
