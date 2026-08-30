'use client';

import Link from 'next/link';
import {
  BookOpen,
  BrainCircuit,
  Microscope,
  Play,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import type { LandingPageDocument, LandingSection } from '@/lib/cms/schema';

const featureIcons = {
  microscope: Microscope,
  zap: Zap,
  'shield-check': ShieldCheck,
  'brain-circuit': BrainCircuit,
  'book-open': BookOpen,
};

interface LandingPageRendererProps {
  document: LandingPageDocument;
  isAuthenticated: boolean;
  diagnosticLoading: boolean;
  onStartDiagnostic: (questionCount: number, durationMinutes: number) => void;
}

function isVisible(section: LandingSection, isAuthenticated: boolean): boolean {
  if (!section.enabled) return false;
  if (section.audience === 'GUEST') return !isAuthenticated;
  if (section.audience === 'AUTHENTICATED') return isAuthenticated;
  return true;
}

export function LandingPageRenderer({
  document,
  isAuthenticated,
  diagnosticLoading,
  onStartDiagnostic,
}: LandingPageRendererProps) {
  const sections = [...document.sections]
    .filter((section) => isVisible(section, isAuthenticated))
    .sort((left, right) => left.order - right.order);

  return (
    <>
      {sections.map((section) => {
        switch (section.type) {
          case 'hero':
            return (
              <section key={section.id} className="container px-4 sm:px-8 pt-20 pb-10 text-center max-w-5xl mx-auto relative z-10">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full glass-card border border-sky-500/30 text-sky-300 text-xs font-semibold mb-6">
                  <Sparkles className="h-3.5 w-3.5 text-sky-400" />
                  <span>{section.props.eyebrow}</span>
                </div>
                <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
                  {section.props.title}<br />
                  <span className="bg-gradient-to-r from-sky-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
                    {section.props.highlight}
                  </span>
                </h1>
                <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
                  {section.props.description}
                </p>
                <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
                  <Button
                    variant="gradient"
                    size="lg"
                    disabled={diagnosticLoading}
                    onClick={() => onStartDiagnostic(5, 5)}
                    className="gap-2.5 text-base px-8 h-12 shadow-lg shadow-sky-500/25 font-bold"
                  >
                    <Play className="h-5 w-5 fill-current" />
                    {diagnosticLoading ? 'Launching...' : section.props.primaryAction.label}
                  </Button>
                  {section.props.secondaryAction && (
                    <Link href={section.props.secondaryAction.action === 'OPEN_STUDENT_HUB' ? '/student' : '/signup'}>
                      <Button variant="outline" size="lg" className="gap-2 text-base px-6 h-12 border-white/15 bg-white/5 hover:bg-white/10 text-white">
                        <BookOpen className="h-5 w-5 text-sky-400" />
                        {section.props.secondaryAction.label}
                      </Button>
                    </Link>
                  )}
                </div>
              </section>
            );
          case 'diagnostic_cta':
            return (
              <section key={section.id} className="container px-4 sm:px-8 pb-8 max-w-4xl mx-auto relative z-10">
                <div className="p-4 sm:p-6 rounded-2xl glass-card border border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 bg-gradient-to-r from-sky-950/40 via-indigo-950/30 to-slate-900/60">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="verified" className="text-[10px]">{section.props.badge}</Badge>
                      <span className="text-xs text-slate-400">• {section.props.durationMinutes} Mins • {section.props.questionCount} Questions</span>
                    </div>
                    <h2 className="text-sm sm:text-base font-bold text-white">{section.props.title}</h2>
                    <p className="text-xs text-slate-400">{section.props.description}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={diagnosticLoading}
                    onClick={() => onStartDiagnostic(section.props.questionCount, section.props.durationMinutes)}
                    className="shrink-0 gap-1.5 border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {section.props.actionLabel}
                  </Button>
                </div>
              </section>
            );
          case 'stats':
            return (
              <section key={section.id} className="container px-4 sm:px-8 py-10 max-w-5xl mx-auto relative z-10">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-white/[0.08] pt-10">
                  {section.props.items.map((item) => (
                    <div key={`${item.label}-${item.value}`} className="p-4 rounded-xl glass-card text-center">
                      <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">{item.value}</div>
                      <div className="text-xs sm:text-sm text-slate-400 mt-1 font-medium">{item.label}</div>
                    </div>
                  ))}
                </div>
              </section>
            );
          case 'feature_grid':
            return (
              <section key={section.id} className="container px-4 sm:px-8 py-16 max-w-6xl mx-auto relative z-10">
                <div className="text-center mb-12">
                  <Badge variant="verified" className="mb-3">{section.props.badge}</Badge>
                  <h2 className="text-3xl font-bold text-white tracking-tight">{section.props.title}</h2>
                  <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">{section.props.description}</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {section.props.items.map((item) => {
                    const Icon = featureIcons[item.icon];
                    return (
                      <Card key={`${item.title}-${item.tag}`} className="glass-card hover:border-sky-500/40 transition-colors p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div className="h-12 w-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                            <Icon className="h-6 w-6" />
                          </div>
                          <Badge variant="secondary">{item.tag}</Badge>
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">{item.title}</h3>
                        <p className="text-slate-300 text-sm leading-relaxed">{item.description}</p>
                      </Card>
                    );
                  })}
                </div>
              </section>
            );
          case 'content_block':
            return (
              <section key={section.id} className="container px-4 sm:px-8 py-12 max-w-4xl mx-auto relative z-10 text-center">
                <h2 className="text-3xl font-bold text-white">{section.props.title}</h2>
                <p className="mt-4 text-slate-300 whitespace-pre-line">{section.props.body}</p>
              </section>
            );
          case 'contact_cta':
            return (
              <section key={section.id} className="container px-4 sm:px-8 py-12 max-w-4xl mx-auto relative z-10">
                <Card className="glass-card p-8 text-center">
                  <h2 className="text-2xl font-bold text-white">{section.props.title}</h2>
                  <p className="mt-2 mb-5 text-slate-300">{section.props.description}</p>
                  <a href={`mailto:${section.props.email}`}>
                    <Button variant="gradient">{section.props.actionLabel}</Button>
                  </a>
                </Card>
              </section>
            );
        }
      })}
    </>
  );
}
