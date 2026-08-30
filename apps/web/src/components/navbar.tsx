'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Stethoscope,
  BookOpen,
  ShieldCheck,
  Award,
  Flame,
  LogOut,
  Sliders,
  Sparkles,
  ChevronDown,
  FolderTree,
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';
import { AuthModal } from './auth/auth-modal';

export function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const links = [
    { href: '/', label: 'Overview', icon: Stethoscope },
    { href: '/pathology', label: 'Pathology Map', icon: FolderTree },
    { href: '/student', label: 'Student Hub', icon: BookOpen },
    { href: '/admin', label: 'Question Bank (Admin)', icon: ShieldCheck },
  ];

  const openAuth = (mode: 'login' | 'register') => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-slate-950/85 backdrop-blur-xl">
        <div className="container flex h-16 items-center justify-between px-4 sm:px-8">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 shadow-md shadow-sky-500/20 group-hover:scale-105 transition-transform">
              <Stethoscope className="h-5 w-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                DocEdge <span className="text-xs font-semibold px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">AI</span>
              </span>
              <span className="text-[10px] text-muted-foreground tracking-wider uppercase">Medical Intelligence</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {links.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-white/[0.08] text-white shadow-sm'
                      : 'text-muted-foreground hover:text-white hover:bg-white/[0.04]'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2.5 p-1.5 pr-3 rounded-full bg-white/[0.05] border border-white/10 hover:bg-white/[0.1] transition-all"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xs">
                    {user.avatar_url ? (
                      <img src={user.avatar_url} alt={user.name} className="w-full h-full rounded-full object-cover" />
                    ) : (
                      user.name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div className="hidden sm:flex flex-col text-left">
                    <span className="text-xs font-bold text-white leading-none truncate max-w-[120px]">{user.name}</span>
                    <span className="text-[10px] text-sky-400 font-semibold">{user.target_exam || 'NEET-SS'}</span>
                  </div>
                  {user.current_streak && user.current_streak > 0 ? (
                    <Badge variant="verified" className="text-[10px] px-1.5 py-0 flex items-center gap-1 bg-amber-500/20 text-amber-300 border-amber-500/30">
                      <Flame className="h-3 w-3 text-amber-400 fill-amber-400" />
                      <span>{user.current_streak}</span>
                    </Badge>
                  ) : null}
                  <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                </button>

                {/* User Dropdown */}
                {dropdownOpen && (
                  <div
                    className="absolute right-0 mt-2 w-56 rounded-2xl border border-slate-700/80 p-2 shadow-2xl bg-slate-900 text-white z-50 animate-fade-in"
                    onMouseLeave={() => setDropdownOpen(false)}
                  >
                    <div className="p-2.5 border-b border-white/10 mb-1">
                      <p className="text-xs font-bold text-white truncate">{user.name}</p>
                      <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
                      <Badge variant="outline" className="mt-1.5 text-[10px] text-sky-300">
                        {user.residency_stage ? `${user.residency_stage} • ${user.target_exam}` : user.target_exam}
                      </Badge>
                    </div>

                    <Link
                      href="/onboarding"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                    >
                      <Sliders className="h-4 w-4 text-sky-400" />
                      <span>Exam Target & Profile</span>
                    </Link>

                    <Link
                      href="/student"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                    >
                      <Award className="h-4 w-4 text-indigo-400" />
                      <span>Student Dashboard</span>
                    </Link>

                    <button
                      type="button"
                      onClick={() => {
                        setDropdownOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition-colors mt-1 border-t border-white/10"
                    >
                      <LogOut className="h-4 w-4" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openAuth('login')}
                  className="text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/[0.05]"
                >
                  Sign In
                </Button>
                <Button
                  variant="gradient"
                  size="sm"
                  onClick={() => openAuth('register')}
                  className="text-xs font-semibold gap-1.5"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Join Free</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Global Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        initialMode={authModalMode}
        onClose={() => setAuthModalOpen(false)}
      />
    </>
  );
}
