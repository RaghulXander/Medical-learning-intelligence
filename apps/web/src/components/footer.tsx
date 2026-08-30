import React from 'react';
import Link from 'next/link';
import { Shield, Sparkles } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-white/[0.08] bg-slate-950 py-10 text-muted-foreground text-sm">
      <div className="container px-4 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-sky-400" />
          <span className="font-semibold text-white">DocEdge Medical Intelligence</span>
          <span>• 15,000+ Curated Medical Questions</span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-slate-400">
          <Link href="/pathology" className="font-semibold text-sky-400 hover:text-sky-300">
            Browse Pathology Map
          </Link>
          <span className="hidden sm:inline">•</span>
          <span className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            Evidence-backed with Standard Peer-Reviewed Medical Literature & Guidelines.
          </span>
        </div>
      </div>
    </footer>
  );
}
