/**
 * apps/mobile/app/(auth)/_layout.tsx
 *
 * Auth Stack Navigator layout.
 */

import React from 'react';
import { Stack } from 'expo-router';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#020617' },
      }}
    />
  );
}
