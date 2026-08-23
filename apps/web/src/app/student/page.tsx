'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Play,
  Flame,
  Clock,
  Award,
  Sparkles,
  Layers,
  AlertCircle,
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
        // Fallback presets if backend is offline
        setPresets([
          {
            id: 'neet-ss-oncopath-mock',
            title: 'NEET-SS Oncopathology Grand Mock',
            type: 'MOCK',
            question_count: 50,
            duration_seconds: 3000,
            marking_scheme_id: 'NEET_4_1',
            description: 'Comprehensive 50-MCQ timed mock exam covering Neoplasia, IHC, and Super-Specialty Pathology.',
            tags: ['NEET-SS', 'Oncopathology', 'High Yield'],
          },
          {
            id: 'neet-pg-pathology-sprint',
            title: 'NEET-PG Pathology High-Yield Sprint',
            type: 'MOCK',
            question_count: 30,
            duration_seconds: 1800,
            marking_scheme_id: 'NEET_4_1',
            description: 'Rapid 30-MCQ test covering high-frequency General and Systemic Pathology topics.',
            tags: ['NEET-PG', 'Sprint', 'Robbins Focus'],
          },
          {
            id: 'daily-dose-pathology',
            title: 'Daily Pathology Dose (10 MCQs)',
            type: 'DAILY_DOSE',
            question_count: 10,
            duration_seconds: 600,
            marking_scheme_id: 'NEET_4_1',
            description: 'Quick daily 10-minute diagnostic drill to maintain spaced-repetition mastery.',
            tags: ['Daily Dose', 'Spaced Repetition'],
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
      });

      // 2. Start attempt
      const attemptRes = await assessmentsApi.startAttempt(createRes.assessment_id);

      // 3. Navigate to active exam runner
      router.push(`/student/exam/${attemptRes.attempt_id}`);
    } catch (err: any) {
      console.error('Error launching assessment:', err);
      setError(err?.message || 'Failed to generate assessment attempt. Ensure backend server is active.');
      setLaunchingId(null);
    }
  };

  return (
    <div className="container max-w-6xl px-4 sm:px-8 py-10">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-8 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
              Student Assessment Portal
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Timed Mock Exams & Topic Mastery
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Select a 1-click exam preset below or launch a custom blueprint from the 15,500+ Pathology question bank.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl glass-card border border-amber-500/30 text-amber-400 text-sm font-semibold">
            <Flame className="h-4 w-4 fill-amber-400" />
            <span>Streak: 7 Days</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-6 p-4 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive flex items-center gap-3 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 1-Click Presets Grid */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-sky-400" />
            <span>1-Click Exam Presets</span>
          </h2>
          <span className="text-xs text-muted-foreground">Instant Blueprint Generation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {presets.map((preset) => {
            const isLaunching = launchingId === preset.id;
            return (
              <Card
                key={preset.id}
                className="glass-card hover:border-sky-500/40 transition-all flex flex-col justify-between p-6"
              >
                <div>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {preset.tags?.map((t, i) => (
                      <Badge key={i} variant="secondary" className="text-[11px]">
                        {t}
                      </Badge>
                    ))}
                  </div>

                  <h3 className="text-lg font-bold text-white mb-2 leading-snug">{preset.title}</h3>
                  <p className="text-slate-300 text-xs leading-relaxed mb-4">{preset.description}</p>

                  <div className="flex items-center gap-4 text-xs text-slate-400 py-3 border-y border-white/[0.06] mb-4">
                    <div className="flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-sky-400" />
                      <span>{preset.question_count} MCQs</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-indigo-400" />
                      <span>{Math.round(preset.duration_seconds / 60)} Mins</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Award className="h-3.5 w-3.5 text-emerald-400" />
                      <span>+4 / -1</span>
                    </div>
                  </div>
                </div>

                <Button
                  variant="gradient"
                  className="w-full gap-2"
                  disabled={isLaunching}
                  onClick={() => handleLaunchPreset(preset)}
                >
                  <Play className="h-4 w-4 fill-white" />
                  <span>{isLaunching ? 'Generating Test...' : 'Start Exam Now'}</span>
                </Button>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
