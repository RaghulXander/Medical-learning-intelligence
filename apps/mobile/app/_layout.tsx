/**
 * apps/mobile/app/_layout.tsx
 *
 * Root Mobile App Layout with AuthProvider, Theme, and Navigation Guard.
 */

import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { AuthProvider, useAuth } from '../lib/auth/auth-context';
import { isOnboardingComplete } from '@medical/shared';

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
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="light" backgroundColor="#020617" />
        <NavigationGuard />
      </AuthProvider>
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
});
