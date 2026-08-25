'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Play,
  Flame,
  Clock,
  Award,
  Sparkles,
  Layers,
  AlertCircle,
  Sliders,
  CheckCircle2,
  TrendingUp,
  BrainCircuit,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { assessmentsApi } from '@medical/api-client';
import { AssessmentPreset } from '@medical/shared';

export default function StudentHubPage() {
  const router = useRouter();
  const [presets, setPresets] = useState<AssessmentPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPresets() {
      try {
        setLoading(true);
        const data = await assessmentsApi.listPresets();
        setPresets(data);
      } catch (err: any) {
        console.error('Failed to load assessment presets:', err);
        // High-yield fallback presets
        setPresets([
          {
            id: 'neet-ss-mock',
            title: 'NEET-SS Grand Mock Examination',
            type: 'MOCK',
            question_count: 150,
            duration_seconds: 9000,
            marking_scheme_id: 'NEET_4_1',
            description: '150-MCQ Super-Specialty simulation with Part A General Pathology & Part B Oncopathology Core (+4 / -1).',
            tags: ['NEET-SS', 'Oncopathology', 'Super-Specialty'],
            depth_level: 'super_specialty',
          },
          {
            id: 'neet-pg-mock',
            title: 'NEET-PG Comprehensive Mock',
            type: 'MOCK',
            question_count: 200,
            duration_seconds: 12600,
            marking_scheme_id: 'NEET_4_1',
            description: 'Full 200-question mock simulating NEET-PG standard exam conditions with high-yield clinical vignettes.',
            tags: ['NEET-PG', 'Clinical', 'High Yield'],
            depth_level: 'postgraduate',
          },
          {
            id: 'inicet-mock',
            title: 'INI-CET Clinical Mock Test',
            type: 'MOCK',
            question_count: 200,
            duration_seconds: 10800,
            marking_scheme_id: 'INICET_1_033',
            description: '200-question multi-disciplinary vignette mock with AIIMS / INI-CET scoring rules (+1 / -0.33).',
            tags: ['INI-CET', 'AIIMS Style', 'Negative 0.33'],
            depth_level: 'postgraduate',
          },
          {
            id: 'pathology-subject-mastery',
            title: 'Pathology Subject Mastery Test',
            type: 'SUBJECT',
            question_count: 100,
            duration_seconds: 6000,
            marking_scheme_id: 'NEET_4_1',
            description: '100 high-yield questions spanning General, Hematopathology, Systemic, and Diagnostic IHC.',
            tags: ['Subject Mastery', 'Robbins Focus'],
          },
          {
            id: 'daily-dose',
            title: 'Daily Rapid Fire (Daily Dose)',
            type: 'DAILY',
            question_count: 10,
            duration_seconds: 600,
            marking_scheme_id: 'NEET_4_1',
            description: '10 high-yield daily diagnostic questions to maintain spaced-repetition retention.',
            tags: ['Daily Dose', 'Spaced Repetition', '10 Mins'],
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    loadPresets();
  }, []);

  const handleLaunchPreset = async (preset: AssessmentPreset) => {
    try {
      setLaunchingId(preset.id);
      setError(null);

      // 1. Create assessment via backend
      const createRes = await assessmentsApi.createAssessment({
        title: preset.title,
        type: preset.type,
        question_count: preset.question_count,
        duration_seconds: preset.duration_seconds,
        marking_scheme_id: preset.marking_scheme_id,
        sections: preset.sections,
      });

      // 2. Start attempt
      const attemptRes = await assessmentsApi.startAttempt(createRes.assessment_id);

      // 3. Navigate to active exam runner
      router.push(`/student/exam/${attemptRes.attempt_id}`);
    } catch (err: any) {
      console.error('Error launching assessment:', err);
      setError(err?.message || 'Failed to generate assessment attempt. Ensure backend server is running.');
      setLaunchingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 pb-20">
      {/* Mobile App-Optimized Hero Header */}
      <div className="border-b border-white/[0.08] bg-slate-950/70 backdrop-blur-xl sticky top-0 z-30 px-4 sm:px-8 py-4 sm:py-6">
        <div className="container max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-[11px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center gap-1">
                <BrainCircuit className="h-3 w-3" />
                Medical Exam Platform
              </span>
              <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                15,500+ Questions Verified
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Pathology Assessment & Mock Exams
            </h1>
            <p className="text-slate-300 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
              Standard Prometric simulation with +4 / -1 NEET marking, zero answer leaks, instant diagnostic scorecard, and deep textbook citations.
            </p>
          </div>

          {/* Quick Metrics / Streak Widget */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <div className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-2xl bg-gradient-to-r from-amber-500/15 to-orange-500/15 border border-amber-500/30 text-amber-300 text-xs sm:text-sm font-bold shadow-lg shadow-amber-500/5">
              <Flame className="h-4 w-4 fill-amber-400 text-amber-400 animate-pulse" />
              <span>7-Day Streak</span>
            </div>
            <div className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-2xl bg-gradient-to-r from-emerald-500/15 to-teal-500/15 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm font-bold">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
              <span>Accuracy: 78.4%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="container max-w-6xl mx-auto px-4 sm:px-8 pt-6 sm:pt-8 space-y-8">
        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-2xl bg-destructive/15 border border-destructive/30 text-destructive flex items-center gap-3 text-sm animate-in fade-in">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Custom Blueprint Generator (BYOT) Spotlight Card */}
        <div className="relative overflow-hidden rounded-3xl border border-sky-500/30 bg-gradient-to-r from-sky-950/60 via-indigo-950/40 to-slate-900/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl shadow-sky-500/10">
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-sky-500/20 blur-3xl pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="max-w-xl">
              <div className="flex items-center gap-2 text-xs font-bold text-sky-400 uppercase tracking-wider mb-2">
                <Sliders className="h-4 w-4" />
                <span>Build Your Own Test (BYOT)</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight mb-2">
                Universal Blueprint Generator
              </h2>
              <p className="text-slate-300 text-xs sm:text-sm leading-relaxed">
                Create a customized practice test targeting specific topics (e.g. Lymphomas, Breast Oncopathology, IHC markers), select question volume (10–100), adjust timer, and choose marking scheme.
              </p>
            </div>

            <div className="flex-shrink-0">
              <Link href="/student/new">
                <Button
                  variant="gradient"
                  size="lg"
                  className="w-full sm:w-auto font-bold px-6 py-6 rounded-2xl gap-2.5 shadow-xl shadow-sky-500/25 active:scale-95 transition-transform"
                >
                  <Sliders className="h-5 w-5" />
                  <span>Customize Blueprint</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* 1-Click Exam Presets Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-sky-400" />
              <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                Standard 1-Click Exam Presets
              </h2>
            </div>
            <span className="text-xs text-slate-400 hidden sm:inline">Instant server-side sampling</span>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-64 rounded-3xl bg-white/[0.03] border border-white/[0.06] animate-pulse p-6" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {presets.map((preset) => {
                const isLaunching = launchingId === preset.id;
                return (
                  <Card
                    key={preset.id}
                    className="glass-card hover:border-sky-500/50 transition-all duration-300 flex flex-col justify-between p-5 sm:p-6 rounded-3xl group shadow-lg hover:shadow-sky-500/10"
                  >
                    <div>
                      {/* Tags */}
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {preset.tags?.map((t, i) => (
                          <Badge
                            key={i}
                            variant="secondary"
                            className="text-[10px] font-semibold px-2 py-0.5 bg-white/[0.06] text-slate-200 border-white/[0.08]"
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>

                      <h3 className="text-base sm:text-lg font-bold text-white mb-2 leading-snug group-hover:text-sky-300 transition-colors">
                        {preset.title}
                      </h3>
                      <p className="text-slate-300 text-xs leading-relaxed mb-4 line-clamp-3">
                        {preset.description}
                      </p>
                    </div>

                    <div>
                      {/* Meta Pill Specs */}
                      <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-300 py-3 border-y border-white/[0.08] mb-4 text-center">
                        <div className="flex flex-col items-center">
                          <span className="text-slate-400 text-[10px]">Volume</span>
                          <span className="font-bold text-white flex items-center gap-1 mt-0.5">
                            <Layers className="h-3 w-3 text-sky-400" />
                            {preset.question_count} Qs
                          </span>
                        </div>
                        <div className="flex flex-col items-center border-x border-white/[0.08]">
                          <span className="text-slate-400 text-[10px]">Duration</span>
                          <span className="font-bold text-white flex items-center gap-1 mt-0.5">
                            <Clock className="h-3 w-3 text-indigo-400" />
                            {Math.round(preset.duration_seconds / 60)}m
                          </span>
                        </div>
                        <div className="flex flex-col items-center">
                          <span className="text-slate-400 text-[10px]">Marking</span>
                          <span className="font-bold text-emerald-400 flex items-center gap-1 mt-0.5">
                            <Award className="h-3 w-3" />
                            {preset.marking_scheme_id === 'INICET_1_033' ? '+1 / -0.33' : '+4 / -1'}
                          </span>
                        </div>
                      </div>

                      {/* Launch Button with Touch Ripple */}
                      <Button
                        variant="gradient"
                        className="w-full py-5 rounded-2xl font-bold gap-2 active:scale-95 transition-transform"
                        disabled={isLaunching}
                        onClick={() => handleLaunchPreset(preset)}
                      >
                        {isLaunching ? (
                          <>
                            <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                            <span>Freezing Snapshot...</span>
                          </>
                        ) : (
                          <>
                            <Play className="h-4 w-4 fill-white" />
                            <span>Start Exam Now</span>
                          </>
                        )}
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* High-Yield Micro Quizzes Section */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-900/40 p-6 sm:p-8 backdrop-blur-md">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-5 w-5 text-amber-400" />
            <h3 className="text-lg font-bold text-white">High-Yield Subtopic Micro-Drills (20 Qs)</h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { title: 'HER2 IHC & FISH Testing', topic: 'TOPIC-BREAST-PATH' },
              { title: 'WHO Lymphoma Subtypes', topic: 'TOPIC-LYMPHOMAS' },
              { title: 'Apoptosis & BCL-2 Pathway', topic: 'TOPIC-CELL-INJURY' },
              { title: 'Tumor Suppressors & P53', topic: 'TOPIC-NEOPLASIA' },
            ].map((drill, idx) => (
              <button
                key={idx}
                onClick={() =>
                  router.push(`/student/new?topic=${encodeURIComponent(drill.topic)}&count=20&title=${encodeURIComponent(drill.title)}`)
                }
                className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] text-left hover:bg-sky-500/10 hover:border-sky-500/30 transition-all cursor-pointer group"
              >
                <div className="text-xs font-bold text-white group-hover:text-sky-300 transition-colors">
                  {drill.title}
                </div>
                <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between">
                  <span>20 MCQs • 20m</span>
                  <span className="text-sky-400 font-semibold">Launch →</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
