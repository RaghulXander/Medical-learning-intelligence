import type { MobileScreenDocument, MobileScreenResponse } from '@medical/shared';
import { MedicalApiClient, defaultClient } from './client';

export class MobileUiApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  async getScreen(
    screenKey: 'home',
    platform: 'IOS' | 'ANDROID',
    appVersion: string
  ): Promise<MobileScreenResponse> {
    const query = new URLSearchParams({ platform, app_version: appVersion });
    return this.client.request(`/api/mobile-ui/screens/${screenKey}?${query.toString()}`);
  }

  async getScreenForEditing(screenKey: 'home'): Promise<{ version: number | null; document: MobileScreenDocument; source: 'database' | 'bundled' }> {
    return this.client.request(`/api/mobile-ui/admin/screens/${screenKey}`);
  }

  async publishScreen(
    screenKey: 'home',
    document: MobileScreenDocument,
    expectedVersion: number | null,
    notes?: string
  ): Promise<{ success: true; version: number; document: MobileScreenDocument }> {
    return this.client.request(`/api/mobile-ui/admin/screens/${screenKey}`, {
      method: 'PUT',
      body: JSON.stringify({ document, expectedVersion, notes }),
    });
  }

  async getHistory(screenKey: 'home'): Promise<{ items: Array<{ version: number; is_active: boolean; published_by?: string; published_at: string }> }> {
    return this.client.request(`/api/mobile-ui/admin/screens/${screenKey}/history`);
  }
}

export const mobileUiApi = new MobileUiApi();
