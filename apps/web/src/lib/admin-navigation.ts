export type AdminThemePreference = 'light' | 'dark' | 'system';

export type AdminNavigationItem = {
  id: string;
  label: string;
  href: string;
  description: string;
  keywords: string[];
};

export type AdminNavigationGroup = {
  label: string;
  items: AdminNavigationItem[];
};

export const adminNavigationGroups: AdminNavigationGroup[] = [
  {
    label: 'Workspace',
    items: [
      {
        id: 'overview',
        label: 'Overview',
        href: '/admin?view=stats',
        description: 'Platform health and key metrics',
        keywords: ['dashboard', 'analytics', 'statistics'],
      },
      {
        id: 'questions',
        label: 'Question bank',
        href: '/admin?view=questions',
        description: 'Review, approve, and edit questions',
        keywords: ['mcq', 'review', 'approval', 'editorial'],
      },
      {
        id: 'users',
        label: 'User governance',
        href: '/admin?view=users',
        description: 'Roles, permissions, and exam access',
        keywords: ['rbac', 'accounts', 'subscription', 'permissions'],
      },
    ],
  },
  {
    label: 'Experience editors',
    items: [
      {
        id: 'landing-content',
        label: 'Landing page',
        href: '/admin/content',
        description: 'Manage public website content',
        keywords: ['cms', 'homepage', 'marketing'],
      },
      {
        id: 'native-layout',
        label: 'Native home',
        href: '/admin/mobile-layout',
        description: 'Compose the mobile home layout',
        keywords: ['mobile', 'widgets', 'app', 'layout'],
      },
    ],
  },
  {
    label: 'Knowledge system',
    items: [
      {
        id: 'ontology',
        label: 'Pathology ontology',
        href: '/pathology',
        description: 'Explore topics, subtopics, and nodes',
        keywords: ['curriculum', 'taxonomy', 'topics', 'nodes'],
      },
    ],
  },
];

export function filterAdminNavigation(
  groups: AdminNavigationGroup[],
  query: string
): AdminNavigationGroup[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return groups;

  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        [item.label, item.description, ...item.keywords]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery)
      ),
    }))
    .filter((group) => group.items.length > 0);
}

export function normalizeAdminTheme(value: string | null): AdminThemePreference {
  return value === 'light' || value === 'dark' || value === 'system' ? value : 'system';
}

export function resolveAdminTheme(
  preference: AdminThemePreference,
  prefersDark: boolean
): 'light' | 'dark' {
  if (preference === 'system') return prefersDark ? 'dark' : 'light';
  return preference;
}
