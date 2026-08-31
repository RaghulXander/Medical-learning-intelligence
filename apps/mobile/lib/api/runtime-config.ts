import { defaultClient } from '@medical/api-client';

export interface MobileRuntimeConfig {
  apiUrl: string | null;
  error: string | null;
}

function normalizeApiUrl(value: string | undefined): MobileRuntimeConfig {
  const apiUrl = value?.trim().replace(/\/+$/, '') ?? '';

  if (!apiUrl) {
    return {
      apiUrl: null,
      error:
        'This build does not contain EXPO_PUBLIC_API_URL. Configure it in the Expo preview/production environment and create a new build.',
    };
  }

  if (!/^https?:\/\/[^\s/$.?#].[^\s]*$/i.test(apiUrl)) {
    return {
      apiUrl: null,
      error: 'EXPO_PUBLIC_API_URL is not a valid absolute HTTP(S) URL.',
    };
  }

  if (!__DEV__ && !apiUrl.startsWith('https://')) {
    return {
      apiUrl: null,
      error: 'Installed builds require an HTTPS EXPO_PUBLIC_API_URL.',
    };
  }

  return { apiUrl, error: null };
}

// Expo only substitutes EXPO_PUBLIC values referenced directly with dot
// notation in application source. Do not move this access into a dependency or
// replace it with dynamic property lookup.
export const mobileRuntimeConfig = normalizeApiUrl(process.env.EXPO_PUBLIC_API_URL);

if (mobileRuntimeConfig.apiUrl) {
  defaultClient.setBaseUrl(mobileRuntimeConfig.apiUrl);
}

