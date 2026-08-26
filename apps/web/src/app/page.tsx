'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  BrainCircuit,
  Microscope,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  BookOpenCheck,
  Zap,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth-context';
import { assessmentsApi } from '@medical/api-client';

export default function LandingPage() {
  const router = useRouter();
  const { user, getOrCreateGuestSession } = useAuth();
  const [startingDiagnostic, setStartingDiagnostic] = useState(false);

  const stats = [
    { label: 'Curated Medical MCQs', value: '15,000+' },
    { label: 'Specialty Topics', value: '60+' },
    { label: 'Assessment Presets', value: '1-Click Instant' },
    { label: 'Literature References', value: 'Peer-Reviewed' },
  ];

  const handleLaunchDiagnostic = async () => {
    setStartingDiagnostic(true);
    try {
      if (!user) {
        await getOrCreateGuestSession();
      }
      // Launch 5-question instant rapid diagnostic test
      const res = await assessmentsApi.createAssessment({
        title: '5-Question Rapid Diagnostic Assessment',
        type: 'CUSTOM',
        question_count: 5,
        duration_seconds: 300,
        blueprint: {
          difficulty_distribution: { easy: 1, medium: 3, hard: 1 },
        },
      });

      const attempt = await assessmentsApi.startAttempt(res.assessment_id);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err) {
      console.error('Failed to launch diagnostic:', err);
      router.push('/student');
    } finally {
      setStartingDiagnostic(false);
    }
  };

  const features = [
    {
      icon: Microscope,
      title: 'Standard Medical Curricula & Super-Specialty',
      description:
        'Targeted prep for Super-Specialty (DM/DrNB), Postgraduate (MD/MS/DNB), and PG entrance exams with granular hierarchy from general mechanisms to molecular genetics.',
      tag: 'Curriculum Aligned',
    },
    {
      icon: Zap,
      title: 'Universal Timed Assessment Engine',
      description:
        'Simulate official exam conditions with sub-second heartbeat synchronization, question state persistence, review markers, and negative marking penalty calculation.',
      tag: 'State-Preserving',
    },
    {
      icon: ShieldCheck,
      title: 'Peer-Reviewed Evidence Citations',
      description:
        'Zero hallucinated references. Citations are linked directly to authoritative, standard peer-reviewed literature and international classification guidelines.',
      tag: 'Verified Literature',
    },
    {
      icon: BrainCircuit,
      title: 'Intelligent Learner Modeling',
      description:
        'Laplace-smoothed mastery tracking, discrete recency penalties, and automated weak-topic remediation blueprints.',
      tag: 'Adaptive Spaced Learning',
    },
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] rounded-full bg-sky-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute top-[20%] right-[10%] w-[600px] h-[600px] rounded-full bg-indigo-500/10 blur-[140px] pointer-events-none" />

      {/* Hero Section */}
      <section className="container px-4 sm:px-8 pt-20 pb-16 text-center max-w-5xl mx-auto relative z-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full glass-card border border-sky-500/30 text-sky-300 text-xs font-semibold mb-6 animate-pulse-glow">
          <Sparkles className="h-3.5 w-3.5 text-sky-400" />
          <span>Next-Gen Medical Exam Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Master Medical Exams with <br />
          <span className="bg-gradient-to-r from-sky-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
            Precision Intelligence & Provenance
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed">
          The ultimate timed mock exam engine and curated question bank for{' '}
          <strong className="text-white">Pathology, NEET-PG, NEET-SS, and INI-CET</strong>. Backed by authoritative medical textbooks and real-time diagnostic analytics.
        </p>

        {/* CTA Actions (Guest Diagnostic Funnel + Practice) */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Button
            variant="gradient"
            size="lg"
            disabled={startingDiagnostic}
            onClick={handleLaunchDiagnostic}
            className="gap-2.5 text-base px-8 h-12 shadow-lg shadow-sky-500/25 font-bold"
          >
            <Play className="h-5 w-5 fill-current" />
            <span>{startingDiagnostic ? 'Launching...' : 'Try 5-Question Diagnostic'}</span>
            <Badge variant="verified" className="text-[10px] ml-1 bg-white/20 text-white border-0">
              No Sign-in Required
            </Badge>
          </Button>

          <Link href="/student">
            <Button variant="outline" size="lg" className="gap-2 text-base px-6 h-12 border-white/15 bg-white/5 hover:bg-white/10 text-white">
              <BookOpenCheck className="h-5 w-5 text-sky-400" />
              <span>Explore Student Hub</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* Diagnostic Feature Highlight Card */}
        <div className="mt-12 p-4 sm:p-6 rounded-2xl glass-card border border-white/10 max-w-3xl mx-auto text-left flex flex-col sm:flex-row items-center justify-between gap-4 bg-gradient-to-r from-sky-950/40 via-indigo-950/30 to-slate-900/60">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="verified" className="text-[10px]">Instant Diagnostic Mode</Badge>
              <span className="text-xs text-slate-400">• 5 Mins • High-Yield Diagnostics</span>
            </div>
            <h4 className="text-sm sm:text-base font-bold text-white">
              Benchmark your core medical knowledge & diagnostic accuracy in 5 questions
            </h4>
            <p className="text-xs text-slate-400">
              Zero login friction. Take the test anonymously, inspect detailed clinical rationales, and merge your score anytime.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLaunchDiagnostic}
            className="shrink-0 gap-1.5 border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20"
          >
            <Sparkles className="h-3.5 w-3.5 text-sky-400" />
            <span>Start Test</span>
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-14 pt-10 border-t border-white/[0.08]">
          {stats.map((stat, idx) => (
            <div key={idx} className="p-4 rounded-xl glass-card text-center">
              <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight bg-gradient-to-r from-white to-slate-200 bg-clip-text text-transparent">
                {stat.value}
              </div>
              <div className="text-xs sm:text-sm text-slate-400 mt-1 font-medium">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="container px-4 sm:px-8 py-16 max-w-6xl mx-auto relative z-10">
        <div className="text-center mb-12">
          <Badge variant="verified" className="mb-3">
            Platform Capabilities
          </Badge>
          <h2 className="text-3xl font-bold text-white tracking-tight">
            Engineered specifically for medical residents & competitive aspirants
          </h2>
          <p className="text-muted-foreground mt-2 max-w-2xl mx-auto text-sm sm:text-base">
            From granular blueprint generation to sub-second state recovery, every component is built for serious medical learning.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((f, idx) => {
            const Icon = f.icon;
            return (
              <Card key={idx} className="glass-card hover:border-sky-500/40 transition-colors p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-12 w-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                      <Icon className="h-6 w-6" />
                    </div>
                    <Badge variant="secondary">{f.tag}</Badge>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">{f.title}</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">{f.description}</p>
                </div>
              </Card>
            );
          })}
        </div>
      </section>
    </div>
  );
}
