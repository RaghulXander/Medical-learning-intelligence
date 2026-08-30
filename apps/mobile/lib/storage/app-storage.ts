import AsyncStorage from '@react-native-async-storage/async-storage';

/** Persistent storage for non-secret application data such as validated UI documents. */
export const AppStorage = {
  setItem(key: string, value: string): Promise<void> {
    return AsyncStorage.setItem(key, value);
  },

  getItem(key: string): Promise<string | null> {
    return AsyncStorage.getItem(key);
  },

  removeItem(key: string): Promise<void> {
    return AsyncStorage.removeItem(key);
  },
};
