import { MedicalApiClient, defaultClient } from './client';

export interface CmsLandingPageResponse {
  document: unknown;
  sha: string | null;
  source: 'github' | 'local';
}

export interface CmsPublishResponse {
  success: boolean;
  document: unknown;
  commit_sha: string | null;
  commit_url: string | null;
  content_sha: string | null;
}

export interface CmsHistoryItem {
  sha: string;
  url: string | null;
  message: string;
  created_at: string | null;
}

export class CmsApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  getLandingPage(): Promise<CmsLandingPageResponse> {
    return this.client.request('/api/cms/landing-page');
  }

  validateLandingPage(document: unknown): Promise<{ valid: true; section_count: number }> {
    return this.client.request('/api/cms/landing-page/validate', {
      method: 'POST',
      body: JSON.stringify(document),
    });
  }

  publishLandingPage(document: unknown, baseSha: string | null, message?: string): Promise<CmsPublishResponse> {
    return this.client.request('/api/cms/landing-page/publish', {
      method: 'PUT',
      body: JSON.stringify({ document, baseSha, message }),
    });
  }

  getHistory(limit = 20): Promise<{ items: CmsHistoryItem[] }> {
    return this.client.request(`/api/cms/landing-page/history?limit=${limit}`);
  }
}

export const cmsApi = new CmsApi();
