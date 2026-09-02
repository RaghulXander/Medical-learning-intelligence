/**
 * apps/mobile/app/_layout.tsx
 *
 * Root Mobile App Layout with AuthProvider, Theme, and Navigation Guard.
 */

import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';
import { AuthProvider, useAuth } from '../lib/auth/auth-context';
import { isOnboardingComplete } from '@medical/shared';
import { mobileRuntimeConfig } from '../lib/api/runtime-config';

import { ErrorBoundary as AppErrorBoundary } from '../components/ErrorBoundary';

export { ErrorBoundary } from 'expo-router';

function ConfigurationError({ message }: { message: string }) {
  return (
    <View style={styles.configurationContainer}>
      <Text style={styles.configurationTitle}>Build configuration missing</Text>
      <Text style={styles.configurationMessage}>{message}</Text>
      <Text style={styles.configurationHint}>
        This is a build configuration problem, not an account or phone problem.
      </Text>
    </View>
  );
}

function NavigationGuard() {
  const { user, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';
    const inOnboarding = segments[0] === 'onboarding';

    if (!user) {
      // User is not signed in -> redirect to login if not already there
      if (!inAuthGroup) {
        router.replace('/(auth)/login' as any);
      }
    } else {
      // User is signed in -> check onboarding profile completion
      const isOnboarded = isOnboardingComplete(user);

      if (!isOnboarded && !inOnboarding) {
        router.replace('/onboarding' as any);
      } else if (isOnboarded && (inAuthGroup || inOnboarding)) {
        router.replace('/(tabs)' as any);
      }
    }
  }, [user, isLoading, segments, router]);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#020617' }, // Slate-950
        animation: 'fade',
      }}
    >
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="onboarding" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="mock/builder" options={{ presentation: 'modal' }} />
      <Stack.Screen name="exam/[attemptId]" options={{ gestureEnabled: false }} />
      <Stack.Screen name="results/[attemptId]" options={{ gestureEnabled: false }} />
      <Stack.Screen name="review/[attemptId]" options={{ headerShown: false }} />
    </Stack>
  );
}

export default function RootLayout() {
  if (mobileRuntimeConfig.error) {
    return (
      <SafeAreaProvider>
        <StatusBar style="light" backgroundColor="#020617" />
        <ConfigurationError message={mobileRuntimeConfig.error} />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <AppErrorBoundary>
        <AuthProvider>
          <StatusBar style="light" backgroundColor="#020617" />
          <NavigationGuard />
        </AuthProvider>
      </AppErrorBoundary>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: '#020617',
    alignItems: 'center',
    justifyContent: 'center',
  },
  configurationContainer: {
    flex: 1,
    backgroundColor: '#020617',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 28,
  },
  configurationTitle: {
    color: '#fb7185',
    fontSize: 22,
    fontWeight: '900',
    marginBottom: 12,
    textAlign: 'center',
  },
  configurationMessage: {
    color: '#e2e8f0',
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
  },
  configurationHint: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 14,
    textAlign: 'center',
  },
});
