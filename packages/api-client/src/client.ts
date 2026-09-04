/**
 * packages/api-client/src/client.ts
 *
 * Universal isomorphic HTTP client for Web & React Native.
 */

export interface ApiClientConfig {
  baseUrl?: string;
  getToken?: () => string | null | Promise<string | null>;
  getGuestToken?: () => string | null | Promise<string | null>;
  onUnauthorized?: () => string | null | Promise<string | null>;
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
  private getGuestToken?: () => string | null | Promise<string | null>;
  private onUnauthorized?: () => string | null | Promise<string | null>;
  private unauthorizedRefresh: Promise<string | null> | null = null;

  constructor(config?: ApiClientConfig) {
    const runtimeProcess = (
      globalThis as typeof globalThis & {
        process?: { env?: Record<string, string | undefined> };
      }
    ).process;
    const expoApiUrl = runtimeProcess?.env?.EXPO_PUBLIC_API_URL;

    if (config?.baseUrl !== undefined) {
      this.baseUrl = config.baseUrl;
    } else if (expoApiUrl) {
      // Expo embeds EXPO_PUBLIC_* values in the native bundle at build time.
      // Check this before `window`: React Native also exposes a window global.
      this.baseUrl = expoApiUrl.replace(/\/$/, '');
    } else if (typeof window !== 'undefined') {
      // In browser: use relative path so Next.js proxy rewrite handles it smoothly with zero CORS or IPv6 issues
      this.baseUrl = '';
    } else {
      // In Node / SSR / React Native: use local backend server URL
      this.baseUrl =
        (runtimeProcess?.env?.API_URL || runtimeProcess?.env?.NEXT_PUBLIC_API_URL) ||
        'http://127.0.0.1:8000';
    }
    this.getToken = config?.getToken;
    this.getGuestToken = config?.getGuestToken;
    this.onUnauthorized = config?.onUnauthorized;
  }

  public setBaseUrl(url: string) {
    this.baseUrl = url;
  }

  public setTokenGetter(getter?: () => string | null | Promise<string | null>) {
    this.getToken = getter;
  }

  public setGuestTokenGetter(getter?: () => string | null | Promise<string | null>) {
    this.getGuestToken = getter;
  }

  public setUnauthorizedHandler(
    handler?: () => string | null | Promise<string | null>
  ) {
    this.onUnauthorized = handler;
  }

  public async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.requestWithAuthRetry<T>(path, options, true);
  }

  private async refreshAfterUnauthorized(): Promise<string | null> {
    if (!this.onUnauthorized) return null;
    if (!this.unauthorizedRefresh) {
      this.unauthorizedRefresh = Promise.resolve(this.onUnauthorized()).finally(() => {
        this.unauthorizedRefresh = null;
      });
    }
    return this.unauthorizedRefresh;
  }

  private async requestWithAuthRetry<T>(
    path: string,
    options: RequestInit,
    allowAuthRetry: boolean
  ): Promise<T> {
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
    if (!headers['Authorization'] && this.getGuestToken) {
      const guestToken = await this.getGuestToken();
      if (guestToken) {
        headers['X-Guest-Session-Token'] = guestToken;
      }
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Access tokens are deliberately short-lived. Refresh once and replay the
    // request; never recurse when the refresh endpoint itself rejects a token.
    if (
      response.status === 401 &&
      allowAuthRetry &&
      Boolean(headers['Authorization']) &&
      path !== '/api/auth/refresh'
    ) {
      const refreshedToken = await this.refreshAfterUnauthorized();
      if (refreshedToken) {
        return this.requestWithAuthRetry<T>(path, options, false);
      }
    }

    if (response.status === 204 || response.status === 304) {
      return {} as T;
    }

    if (!response.ok) {
      let errorData: any;
      try {
        const text = await response.text();
        try {
          errorData = JSON.parse(text);
        } catch {
          errorData = text;
        }
      } catch {
        errorData = response.statusText;
      }
      throw new ApiError(response.status, response.statusText, errorData);
    }

    return (await response.json()) as T;
  }
}

export const defaultClient = new MedicalApiClient();

export function setAuthTokenGetter(getter: () => string | null | Promise<string | null>) {
  defaultClient.setTokenGetter(getter);
}

export function setGuestTokenGetter(getter: () => string | null | Promise<string | null>) {
  defaultClient.setGuestTokenGetter(getter);
}

export function setUnauthorizedHandler(
  handler?: () => string | null | Promise<string | null>
) {
  defaultClient.setUnauthorizedHandler(handler);
}
