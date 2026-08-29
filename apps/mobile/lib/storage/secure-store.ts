/**
 * apps/mobile/lib/storage/secure-store.ts
 *
 * Cross-platform persistent storage utility for mobile sessions and secure credentials.
 */

import { Platform } from 'react-native';
import * as ExpoSecureStore from 'expo-secure-store';

const memoryStore = new Map<string, string>();

function getWebStorage(): Storage | null {
  return typeof localStorage === 'undefined' ? null : localStorage;
}

export const SecureStorage = {
  async setItem(key: string, value: string): Promise<void> {
    try {
      if (Platform.OS === 'web') {
        const storage = getWebStorage();
        if (storage) storage.setItem(key, value);
      } else {
        await ExpoSecureStore.setItemAsync(key, value, {
          keychainAccessible: ExpoSecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
        });
      }
    } catch (error) {
      if (Platform.OS !== 'web') throw error;
      memoryStore.set(key, value);
    }
  },

  async getItem(key: string): Promise<string | null> {
    try {
      if (Platform.OS === 'web') {
        return getWebStorage()?.getItem(key) ?? memoryStore.get(key) ?? null;
      }
      return await ExpoSecureStore.getItemAsync(key);
    } catch (error) {
      if (Platform.OS !== 'web') throw error;
      return memoryStore.get(key) || null;
    }
  },

  async removeItem(key: string): Promise<void> {
    try {
      if (Platform.OS === 'web') {
        getWebStorage()?.removeItem(key);
      } else {
        await ExpoSecureStore.deleteItemAsync(key);
      }
    } catch (error) {
      if (Platform.OS !== 'web') throw error;
      memoryStore.delete(key);
    }
  },
};
