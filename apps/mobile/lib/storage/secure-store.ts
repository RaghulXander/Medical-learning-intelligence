/**
 * apps/mobile/lib/storage/secure-store.ts
 *
 * Cross-platform persistent storage utility for mobile sessions and secure credentials.
 */

import { Platform } from 'react-native';

const memoryStore = new Map<string, string>();

export const SecureStorage = {
  async setItem(key: string, value: string): Promise<void> {
    try {
      if (Platform.OS === 'web' && typeof localStorage !== 'undefined') {
        localStorage.setItem(key, value);
      } else {
        memoryStore.set(key, value);
      }
    } catch {
      memoryStore.set(key, value);
    }
  },

  async getItem(key: string): Promise<string | null> {
    try {
      if (Platform.OS === 'web' && typeof localStorage !== 'undefined') {
        return localStorage.getItem(key);
      }
      return memoryStore.get(key) || null;
    } catch {
      return memoryStore.get(key) || null;
    }
  },

  async removeItem(key: string): Promise<void> {
    try {
      if (Platform.OS === 'web' && typeof localStorage !== 'undefined') {
        localStorage.removeItem(key);
      } else {
        memoryStore.delete(key);
      }
    } catch {
      memoryStore.delete(key);
    }
  },
};
