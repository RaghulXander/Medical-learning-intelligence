import type { ConfigContext, ExpoConfig } from 'expo/config';
import appJson from './app.json';

const IOS_CLIENT_SUFFIX = '.apps.googleusercontent.com';

function googleIosUrlScheme(clientId: string | undefined): string | null {
  const normalized = clientId?.trim() ?? '';
  if (!normalized.endsWith(IOS_CLIENT_SUFFIX)) return null;
  return `com.googleusercontent.apps.${normalized.slice(0, -IOS_CLIENT_SUFFIX.length)}`;
}

export default ({ config }: ConfigContext): ExpoConfig => {
  const base = appJson.expo as ExpoConfig;
  const plugins = [...(base.plugins ?? [])];
  const iosUrlScheme = googleIosUrlScheme(process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID);

  // The native package is autolinked on Android. Its Expo plugin adds the iOS
  // callback scheme when an iOS OAuth client is configured for that EAS environment.
  if (iosUrlScheme) {
    plugins.push([
      '@react-native-google-signin/google-signin',
      { iosUrlScheme },
    ]);
  }

  return {
    ...config,
    ...base,
    plugins,
  };
};
