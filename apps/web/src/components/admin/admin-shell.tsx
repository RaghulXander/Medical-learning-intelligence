'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import {
  BarChart3,
  BookOpenText,
  ChevronRight,
  ExternalLink,
  FileCheck2,
  LayoutDashboard,
  Menu,
  Monitor,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  Smartphone,
  Sun,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import {
  AdminNavigationItem,
  AdminThemePreference,
  adminNavigationGroups,
  filterAdminNavigation,
  normalizeAdminTheme,
  resolveAdminTheme,
} from '@/lib/admin-navigation';
import { cn } from '@/lib/utils';

const THEME_STORAGE_KEY = 'docedge_admin_theme';
const SIDEBAR_STORAGE_KEY = 'docedge_admin_sidebar_collapsed';

const navigationIcons = {
  overview: BarChart3,
  questions: FileCheck2,
  users: Users,
  'landing-content': LayoutDashboard,
  'native-layout': Smartphone,
  ontology: BookOpenText,
} as const;

function viewFromSearchParams(searchParams: URLSearchParams): string {
  const view = searchParams.get('view');
  return view === 'users' || view === 'stats' ? view : 'questions';
}

function itemIsActive(item: AdminNavigationItem, pathname: string, activeView: string): boolean {
  if (item.id === 'questions') {
    return pathname.startsWith('/admin/questions') || (pathname === '/admin' && activeView === 'questions');
  }
  if (item.id === 'users') return pathname === '/admin' && activeView === 'users';
  if (item.id === 'overview') return pathname === '/admin' && activeView === 'stats';
  return pathname === item.href;
}

function currentPage(pathname: string, activeView: string): { title: string; description: string } {
  if (pathname.startsWith('/admin/questions/')) {
    return { title: 'Question editor', description: 'Review content, metadata, and evidence' };
  }
  if (pathname === '/admin/content') {
    return { title: 'Landing page', description: 'Manage the public website experience' };
  }
  if (pathname === '/admin/mobile-layout') {
    return { title: 'Native home', description: 'Compose the mobile application layout' };
  }
  if (activeView === 'users') {
    return { title: 'User governance', description: 'Control roles, permissions, and access' };
  }
  if (activeView === 'stats') {
    return { title: 'Overview', description: 'Monitor platform activity and content health' };
  }
  return { title: 'Question bank', description: 'Curate and approve pathology questions' };
}

function ThemeControl({
  preference,
  onChange,
}: {
  preference: AdminThemePreference;
  onChange: (preference: AdminThemePreference) => void;
}) {
  const options = [
    { value: 'light' as const, label: 'Light', icon: Sun },
    { value: 'dark' as const, label: 'Dark', icon: Moon },
    { value: 'system' as const, label: 'System', icon: Monitor },
  ];

  return (
    <div className="flex items-center rounded-xl border border-border bg-muted/40 p-1" aria-label="Admin color theme">
      {options.map((option) => {
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            title={`${option.label} theme`}
            aria-label={`${option.label} theme`}
            aria-pressed={preference === option.value}
            onClick={() => onChange(option.value)}
            className={cn(
              'grid h-7 w-7 place-items-center rounded-lg text-muted-foreground transition-colors',
              preference === option.value
                ? 'bg-card text-foreground shadow-sm'
                : 'hover:bg-card/60 hover:text-foreground'
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        );
      })}
    </div>
  );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [navigationSearch, setNavigationSearch] = useState('');
  const [themePreference, setThemePreference] = useState<AdminThemePreference>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark');

  const activeView = viewFromSearchParams(searchParams);
  const page = currentPage(pathname, activeView);
  const filteredGroups = useMemo(
    () => filterAdminNavigation(adminNavigationGroups, navigationSearch),
    [navigationSearch]
  );

  useEffect(() => {
    setThemePreference(normalizeAdminTheme(localStorage.getItem(THEME_STORAGE_KEY)));
    setCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true');
  }, []);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const updateResolvedTheme = () => {
      setResolvedTheme(resolveAdminTheme(themePreference, media.matches));
    };
    updateResolvedTheme();
    media.addEventListener('change', updateResolvedTheme);
    return () => media.removeEventListener('change', updateResolvedTheme);
  }, [themePreference]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname, searchParams]);

  const updateTheme = (preference: AdminThemePreference) => {
    setThemePreference(preference);
    localStorage.setItem(THEME_STORAGE_KEY, preference);
  };

  const updateCollapsed = (nextCollapsed: boolean) => {
    setCollapsed(nextCollapsed);
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(nextCollapsed));
  };

  const hasAdminAccess = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';

  const sidebar = (isMobile: boolean) => (
    <div className="flex h-full flex-col bg-card text-card-foreground">
      <div className={cn('flex h-16 items-center border-b border-border px-4', collapsed && !isMobile ? 'justify-center px-2' : 'gap-3')}>
        <Link href="/admin?view=stats" className="flex min-w-0 items-center gap-3" aria-label="DocEdge admin overview">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20">
            <ShieldCheck className="h-5 w-5" />
          </span>
          {(!collapsed || isMobile) && (
            <span className="min-w-0">
              <span className="block truncate text-sm font-extrabold tracking-tight">DocEdge Admin</span>
              <span className="block truncate text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Governance workspace</span>
            </span>
          )}
        </Link>
        {isMobile && (
          <button type="button" className="ml-auto rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {(!collapsed || isMobile) && (
        <div className="px-3 pt-4">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <span className="sr-only">Find admin menu</span>
            <input
              type="search"
              value={navigationSearch}
              onChange={(event) => setNavigationSearch(event.target.value)}
              placeholder="Find a menu…"
              className="h-9 w-full rounded-xl border border-border bg-background/70 pl-9 pr-3 text-xs text-foreground outline-none placeholder:text-muted-foreground focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
            />
          </label>
        </div>
      )}

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4" aria-label="Admin navigation">
        {filteredGroups.length === 0 && (!collapsed || isMobile) ? (
          <div className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
            No menu matches “{navigationSearch}”.
          </div>
        ) : (
          <div className="space-y-5">
            {filteredGroups.map((group) => (
              <div key={group.label}>
                {(!collapsed || isMobile) && (
                  <p className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground/80">
                    {group.label}
                  </p>
                )}
                <div className="space-y-1">
                  {group.items.map((item) => {
                    const Icon = navigationIcons[item.id as keyof typeof navigationIcons] ?? LayoutDashboard;
                    const isActive = itemIsActive(item, pathname, activeView);
                    return (
                      <Link
                        key={item.id}
                        href={item.href}
                        title={collapsed && !isMobile ? item.label : undefined}
                        aria-current={isActive ? 'page' : undefined}
                        className={cn(
                          'group flex min-h-10 items-center rounded-xl text-sm transition-colors',
                          collapsed && !isMobile ? 'justify-center px-2' : 'gap-3 px-3',
                          isActive
                            ? 'bg-sky-500/12 font-semibold text-sky-500 ring-1 ring-inset ring-sky-500/20'
                            : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        {(!collapsed || isMobile) && <span className="truncate">{item.label}</span>}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </nav>

      <div className="border-t border-border p-3">
        <Link
          href="/"
          title={collapsed && !isMobile ? 'View public site' : undefined}
          className={cn(
            'flex h-10 items-center rounded-xl text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground',
            collapsed && !isMobile ? 'justify-center px-2' : 'gap-3 px-3'
          )}
        >
          <ExternalLink className="h-4 w-4 shrink-0" />
          {(!collapsed || isMobile) && <span>View public site</span>}
        </Link>
      </div>
    </div>
  );

  if (authLoading || !hasAdminAccess) {
    return (
      <div className={cn('admin-workspace min-h-screen bg-background text-foreground', resolvedTheme === 'light' ? 'admin-theme-light' : 'admin-theme-dark')}>
        {children}
      </div>
    );
  }

  return (
    <div className={cn('admin-workspace min-h-screen bg-background text-foreground', resolvedTheme === 'light' ? 'admin-theme-light' : 'admin-theme-dark')}>
      <aside className={cn('fixed inset-y-0 left-0 z-40 hidden border-r border-border shadow-sm transition-[width] duration-200 lg:block', collapsed ? 'w-[76px]' : 'w-72')}>
        {sidebar(false)}
        <button
          type="button"
          onClick={() => updateCollapsed(!collapsed)}
          className="absolute -right-3 top-20 grid h-7 w-7 place-items-center rounded-full border border-border bg-card text-muted-foreground shadow-sm hover:text-foreground"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
        </button>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" />
          <aside className="relative h-full w-[min(88vw,320px)] border-r border-border shadow-2xl">{sidebar(true)}</aside>
        </div>
      )}

      <div className={cn('min-w-0 transition-[padding] duration-200', collapsed ? 'lg:pl-[76px]' : 'lg:pl-72')}>
        <header className="sticky top-0 z-30 flex min-h-16 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6">
          <button type="button" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open admin navigation">
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
              <span>Admin</span>
              <ChevronRight className="h-3 w-3" />
              {pathname.startsWith('/admin/questions/') && (
                <>
                  <Link href="/admin?view=questions" className="hover:text-foreground">Question bank</Link>
                  <ChevronRight className="h-3 w-3" />
                </>
              )}
              <span className="truncate text-foreground/80">{page.title}</span>
            </div>
            <div className="mt-0.5 flex min-w-0 items-baseline gap-2">
              <h1 className="truncate text-base font-extrabold tracking-tight sm:text-lg">{page.title}</h1>
              <p className="hidden truncate text-xs text-muted-foreground md:block">{page.description}</p>
            </div>
          </div>

          <ThemeControl preference={themePreference} onChange={updateTheme} />
          <div className="hidden items-center gap-2 border-l border-border pl-3 sm:flex">
            <div className="grid h-8 w-8 place-items-center rounded-full bg-sky-500/15 text-xs font-bold text-sky-500">
              {(user?.name || user?.email || 'A').charAt(0).toUpperCase()}
            </div>
            <div className="hidden max-w-36 leading-tight xl:block">
              <p className="truncate text-xs font-semibold">{user?.name || user?.email || 'Administrator'}</p>
              <p className="truncate text-[10px] uppercase tracking-wide text-muted-foreground">{user?.role?.replace('_', ' ') || 'Admin'}</p>
            </div>
          </div>
        </header>

        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}
