/**
 * packages/api-client/src/client.ts
 *
 * Universal isomorphic HTTP client for Web & React Native.
 */

export interface ApiClientConfig {
  baseUrl?: string;
  getToken?: () => string | null | Promise<string | null>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: any
  ) {
    super(
      typeof data?.detail === 'string'
        ? data.detail
        : `API Error ${status}: ${statusText}`
    );
    this.name = 'ApiError';
  }
}

export class MedicalApiClient {
  private baseUrl: string;
  private getToken?: () => string | null | Promise<string | null>;

  constructor(config?: ApiClientConfig) {
    if (config?.baseUrl !== undefined) {
      this.baseUrl = config.baseUrl;
    } else if (typeof window !== 'undefined') {
      // In browser: use relative path so Next.js proxy rewrite handles it smoothly with zero CORS or IPv6 issues
      this.baseUrl = '';
    } else {
      // In Node / SSR / React Native: use local backend server URL
      this.baseUrl =
        (typeof process !== 'undefined' && (process.env?.API_URL || process.env?.NEXT_PUBLIC_API_URL)) ||
        'http://127.0.0.1:8000';
    }
    this.getToken = config?.getToken;
  }

  public setBaseUrl(url: string) {
    this.baseUrl = url;
  }

  public setTokenGetter(getter?: () => string | null | Promise<string | null>) {
    this.getToken = getter;
  }

  public async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.getToken) {
      const token = await this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = await response.text();
      }
      throw new ApiError(response.status, response.statusText, errorData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  }
}

export const defaultClient = new MedicalApiClient();

export function setAuthTokenGetter(getter: () => string | null | Promise<string | null>) {
  defaultClient.setTokenGetter(getter);
}

