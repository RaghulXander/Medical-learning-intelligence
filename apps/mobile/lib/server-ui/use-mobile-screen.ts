import { useCallback, useEffect, useMemo, useState } from 'react';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { mobileUiApi } from '@medical/api-client';
import {
  MobileScreenDocument,
  UserProfile,
  mobileScreenDocumentSchema,
} from '@medical/shared';
import bundledHome from '../../content/home-screen.json';
import { AppStorage } from '../storage/app-storage';

interface CachedScreen {
  storedAt: number;
  document: MobileScreenDocument;
}

function versionParts(value: string): number[] {
  return value.split('.').map((part) => Number(part) || 0);
}

function isCompatible(current: string, minimum: string): boolean {
  const left = versionParts(current);
  const right = versionParts(minimum);
  for (let index = 0; index < 3; index += 1) {
    if ((left[index] ?? 0) > (right[index] ?? 0)) return true;
    if ((left[index] ?? 0) < (right[index] ?? 0)) return false;
  }
  return true;
}

function localVisibility(document: MobileScreenDocument, user: UserProfile | null): MobileScreenDocument {
  const platform = Platform.OS === 'ios' ? 'IOS' : 'ANDROID';
  return {
    ...document,
    widgets: document.widgets
      .filter((widget) => widget.enabled)
      .filter((widget) => widget.platforms.includes('ALL') || widget.platforms.includes(platform))
      .filter((widget) => {
        if (widget.audience === 'AUTHENTICATED') return Boolean(user);
        if (widget.audience === 'FREE') return Boolean(user && !user.is_subscribed);
        if (widget.audience === 'SUBSCRIBED') return Boolean(user?.is_subscribed);
        return true;
      })
      .sort((left, right) => left.order - right.order),
  };
}

export function useMobileScreen(user: UserProfile | null) {
  const fallback = useMemo(
    () => localVisibility(mobileScreenDocumentSchema.parse(bundledHome), user),
    [user]
  );
  const [document, setDocument] = useState<MobileScreenDocument>(fallback);
  const [source, setSource] = useState<'remote' | 'cache' | 'bundled'>('bundled');
  const appVersion = Constants.expoConfig?.version ?? '1.0.0';
  const platform = Platform.OS === 'ios' ? 'IOS' as const : 'ANDROID' as const;
  const cacheKey = `docedge_mobile_ui_home_${user?.id ?? 'guest'}_${user?.is_subscribed ? 'subscribed' : 'free'}_${platform}`;

  const refresh = useCallback(async () => {
    try {
      const response = await mobileUiApi.getScreen('home', platform, appVersion);
      const remote = mobileScreenDocumentSchema.parse(response.document);
      if (!isCompatible(appVersion, remote.minimumAppVersion)) throw new Error('Remote layout requires a newer application build');
      const visible = localVisibility(remote, user);
      setDocument(visible);
      setSource('remote');
      try {
        await AppStorage.setItem(cacheKey, JSON.stringify({ storedAt: Date.now(), document: visible } satisfies CachedScreen));
      } catch {
        // A valid remote document remains usable even when device cache storage is unavailable.
      }
    } catch {
      try {
        const stored = await AppStorage.getItem(cacheKey);
        if (stored) {
          const cached = JSON.parse(stored) as CachedScreen;
          const validated = mobileScreenDocumentSchema.parse(cached.document);
          if (Date.now() - cached.storedAt <= validated.cacheTtlSeconds * 1000) {
            setDocument(localVisibility(validated, user));
            setSource('cache');
            return;
          }
        }
      } catch {
        // Invalid or unavailable cache falls through to the bundled document.
      }
      setDocument(fallback);
      setSource('bundled');
    }
  }, [appVersion, cacheKey, fallback, platform, user]);

  useEffect(() => {
    setDocument(fallback);
    void refresh();
  }, [fallback, refresh]);

  return { document, source, refresh };
}
