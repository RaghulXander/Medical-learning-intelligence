'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Stethoscope, BookOpen, Layers, ShieldCheck, Award } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '@/lib/utils';

export function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Overview', icon: Stethoscope },
    { href: '/student', label: 'Practice & Mocks', icon: BookOpen },
    { href: '/admin', label: 'Question Bank (Admin)', icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-slate-950/80 backdrop-blur-xl">
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

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <Link href="/student">
            <Button variant="gradient" size="sm" className="gap-2">
              <Award className="h-4 w-4" />
              <span>Launch Mock Test</span>
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
