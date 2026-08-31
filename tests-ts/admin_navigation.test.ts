import { describe, expect, test } from 'bun:test';
import {
  adminNavigationGroups,
  filterAdminNavigation,
  normalizeAdminTheme,
  resolveAdminTheme,
} from '../apps/web/src/lib/admin-navigation';

describe('admin navigation', () => {
  test('shows every group when the search is empty', () => {
    expect(filterAdminNavigation(adminNavigationGroups, '')).toEqual(adminNavigationGroups);
  });

  test('finds a menu by label, description, or keyword', () => {
    expect(filterAdminNavigation(adminNavigationGroups, 'question')[0]?.items[0]?.id).toBe('questions');
    expect(filterAdminNavigation(adminNavigationGroups, 'permissions')[0]?.items[0]?.id).toBe('users');
    expect(filterAdminNavigation(adminNavigationGroups, 'taxonomy')[0]?.items[0]?.id).toBe('ontology');
  });

  test('removes empty groups for an unmatched search', () => {
    expect(filterAdminNavigation(adminNavigationGroups, 'not-a-real-menu')).toEqual([]);
  });
});

describe('admin theme preference', () => {
  test('normalizes unknown stored values to system', () => {
    expect(normalizeAdminTheme('sepia')).toBe('system');
    expect(normalizeAdminTheme(null)).toBe('system');
  });

  test('resolves system theme and preserves explicit choices', () => {
    expect(resolveAdminTheme('system', true)).toBe('dark');
    expect(resolveAdminTheme('system', false)).toBe('light');
    expect(resolveAdminTheme('light', true)).toBe('light');
    expect(resolveAdminTheme('dark', false)).toBe('dark');
  });
});
