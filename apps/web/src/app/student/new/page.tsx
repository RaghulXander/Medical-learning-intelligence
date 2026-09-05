'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Sliders,
  Play,
  ArrowLeft,
  Clock,
  AlertCircle,
  BrainCircuit,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { assessmentsApi, questionsApi, TopicCountItem } from '@medical/api-client';
import { cn } from '@/lib/utils';

function BlueprintGeneratorContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const initialTopic = searchParams.get('topic') || 'ALL';
  const initialCount = parseInt(searchParams.get('count') || '30', 10);
  const initialTitle = searchParams.get('title') || '';

  const [title, setTitle] = useState(initialTitle || 'Custom Pathology Blueprint Test');
  const [selectedTopic, setSelectedTopic] = useState(initialTopic);
  const [questionCount, setQuestionCount] = useState(initialCount);
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [markingScheme, setMarkingScheme] = useState('NEET_4_1');
  const [difficulty, setDifficulty] = useState<'ALL' | 'easy' | 'medium' | 'hard'>('ALL');
  const [mode, setMode] = useState<'TIMED' | 'PRACTICE'>('TIMED');

  const [topics, setTopics] = useState<TopicCountItem[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync duration with question count by default (1 min per question)
  useEffect(() => {
    setDurationMinutes(questionCount);
  }, [questionCount]);

  useEffect(() => {
    async function loadTopics() {
      try {
        setLoadingTopics(true);
        const data = await questionsApi.listTopics();
        setTopics(data);
      } catch (err) {
        console.warn('Could not load topics list:', err);
      } finally {
        setLoadingTopics(false);
      }
    }
    loadTopics();
  }, []);

  const handleGenerateAndStart = async () => {
    try {
      setGenerating(true);
      setError(null);

      const durationSeconds = mode === 'PRACTICE' ? 7200 : durationMinutes * 60;

      // Construct blueprint
      const blueprint: Record<string, any> = {};
      if (selectedTopic !== 'ALL') {
        blueprint.topic_id = selectedTopic;
      }
      if (difficulty !== 'ALL') {
        blueprint.difficulty = difficulty;
      }

      // 1. Create Assessment
      const assessment = await assessmentsApi.createAssessment({
        title: title.trim() || 'Custom Blueprint Practice',
        type: selectedTopic !== 'ALL' ? 'TOPIC' : 'CUSTOM',
        question_count: questionCount,
        duration_seconds: durationSeconds,
        marking_scheme_id: markingScheme,
        blueprint,
      });

      // 2. Start Attempt
      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id);

      // 3. Route directly to runner
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err: any) {
      console.error('Failed to create custom assessment:', err);
      setError(err?.message || 'Failed to generate test. Please adjust question count or topic filter.');
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 pb-20">
      {/* Top Header */}
      <div className="border-b border-white/[0.08] bg-slate-950/80 backdrop-blur-xl sticky top-0 z-30 px-4 sm:px-8 py-4">
        <div className="container max-w-5xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/student">
              <Button variant="outline" size="sm" className="rounded-xl border-white/10 text-slate-300 gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                <span className="hidden sm:inline">Back</span>
              </Button>
            </Link>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <Sliders className="h-5 w-5 text-sky-400" />
                <span>Universal Blueprint Generator</span>
              </h1>
            </div>
          </div>

          <Badge variant="outline" className="hidden sm:flex border-sky-500/30 text-sky-400 bg-sky-500/10 text-xs">
            Dynamic Sampling
          </Badge>
        </div>
      </div>

      <div className="container max-w-4xl mx-auto px-4 sm:px-8 pt-6 sm:pt-8 space-y-6">
        {error && (
          <div className="p-4 rounded-2xl bg-destructive/15 border border-destructive/30 text-destructive flex items-center gap-3 text-sm">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Blueprint Configuration Card */}
        <Card className="glass-card p-6 sm:p-8 rounded-3xl space-y-6">
          {/* Test Title */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-2">
              Assessment Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-3 rounded-2xl bg-white/[0.04] border border-white/[0.1] text-white text-base font-medium placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
              placeholder="e.g., General Pathology & Lymphoma Drill"
            />
          </div>

          {/* Mode Switcher */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-2">
              Testing Mode
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMode('TIMED')}
                className={cn(
                  'p-4 rounded-2xl border text-left transition-all cursor-pointer',
                  mode === 'TIMED'
                    ? 'bg-sky-500/20 border-sky-400 text-white shadow-lg shadow-sky-500/10'
                    : 'bg-white/[0.02] border-white/[0.08] text-slate-300 hover:bg-white/[0.05]'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-sm text-white">Timed Mock Simulation</span>
                  <Clock className="h-4 w-4 text-sky-400" />
                </div>
                <p className="text-xs text-slate-400">Strict countdown timer, Prometric conditions (+4 / -1).</p>
              </button>

              <button
                type="button"
                onClick={() => setMode('PRACTICE')}
                className={cn(
                  'p-4 rounded-2xl border text-left transition-all cursor-pointer',
                  mode === 'PRACTICE'
                    ? 'bg-purple-500/20 border-purple-400 text-white shadow-lg shadow-purple-500/10'
                    : 'bg-white/[0.02] border-white/[0.08] text-slate-300 hover:bg-white/[0.05]'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-sm text-white">Tutor / Practice Mode</span>
                  <BrainCircuit className="h-4 w-4 text-purple-400" />
                </div>
                <p className="text-xs text-slate-400">Untimed relaxed pace, zero penalty exploration.</p>
              </button>
            </div>
          </div>

          {/* Topic Scope */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Target Topic Scope
              </label>
              <span className="text-xs text-slate-500">
                {topics.length > 0 ? `${topics.length} Topics Available` : 'Loading...'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
              <button
                type="button"
                onClick={() => setSelectedTopic('ALL')}
                className={cn(
                  'p-3 rounded-xl border text-left text-xs font-semibold flex items-center justify-between transition-all cursor-pointer',
                  selectedTopic === 'ALL'
                    ? 'bg-sky-500 text-white border-sky-400 shadow-sm'
                    : 'bg-white/[0.02] border-white/[0.08] text-slate-300 hover:bg-white/[0.05]'
                )}
              >
                <span>Full Comprehensive Pathology Mix</span>
                <Badge variant="secondary" className="text-[10px]">15,500+ MCQs</Badge>
              </button>

              {topics.map((t) => (
                <button
                  key={t.name}
                  type="button"
                  onClick={() => setSelectedTopic(t.name)}
                  className={cn(
                    'p-3 rounded-xl border text-left text-xs font-medium flex items-center justify-between transition-all cursor-pointer',
                    selectedTopic === t.name
                      ? 'bg-sky-500 text-white border-sky-400 shadow-sm font-semibold'
                      : 'bg-white/[0.02] border-white/[0.08] text-slate-300 hover:bg-white/[0.05]'
                  )}
                >
                  <span className="truncate pr-2">{t.name}</span>
                  <span className="text-[11px] text-slate-400">{t.count} Qs</span>
                </button>
              ))}
            </div>
          </div>

          {/* Question Count Selection */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Number of Questions
              </label>
              <span className="text-sm font-bold text-sky-400">{questionCount} MCQs</span>
            </div>

            <div className="grid grid-cols-4 gap-2 mb-3">
              {[10, 25, 50, 100].map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => setQuestionCount(count)}
                  className={cn(
                    'py-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer',
                    questionCount === count
                      ? 'bg-sky-500 text-white border-sky-400 shadow-sm'
                      : 'bg-white/[0.02] border-white/[0.08] text-slate-300 hover:bg-white/[0.05]'
                  )}
                >
                  {count} Qs
                </button>
              ))}
            </div>
          </div>

          {/* Marking Scheme & Difficulty Mix */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Marking Scheme */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Marking Scheme
              </label>
              <select
                value={markingScheme}
                onChange={(e) => setMarkingScheme(e.target.value)}
                className="w-full px-4 py-3 rounded-2xl bg-slate-900 border border-white/[0.1] text-white text-sm focus:outline-none focus:border-sky-500 cursor-pointer"
              >
                <option value="NEET_4_1">NEET Standard (+4 / -1, 25% penalty)</option>
                <option value="INICET_1_033">INI-CET Standard (+1 / -0.33, 33.3% penalty)</option>
                <option value="PROPORTIONAL_1_025">Proportional (+1 / -0.25)</option>
                <option value="ZERO_PENALTY">Zero Penalty / Practice (+1 / 0)</option>
              </select>
            </div>

            {/* Difficulty */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Difficulty Focus
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as any)}
                className="w-full px-4 py-3 rounded-2xl bg-slate-900 border border-white/[0.1] text-white text-sm focus:outline-none focus:border-sky-500 cursor-pointer"
              >
                <option value="ALL">Balanced High-Yield Mix</option>
                <option value="easy">Foundational (Easy)</option>
                <option value="medium">Standard Clinical (Medium)</option>
                <option value="hard">Advanced PG/SS Vignettes (Hard)</option>
                <option value="very_hard">Super-Specialty Consultant / DM (Very Hard)</option>
              </select>
            </div>
          </div>

          {/* Launch Action */}
          <div className="pt-4 border-t border-white/[0.08]">
            <Button
              variant="gradient"
              size="lg"
              className="w-full py-6 rounded-2xl font-bold text-base gap-2.5 shadow-xl shadow-sky-500/25 active:scale-95 transition-transform"
              disabled={generating || loadingTopics}
              onClick={handleGenerateAndStart}
            >
              {generating ? (
                <>
                  <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                  <span>Freezing Blueprint Questions...</span>
                </>
              ) : (
                <>
                  <Play className="h-5 w-5 fill-white" />
                  <span>Generate Blueprint & Start Test</span>
                </>
              )}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function BlueprintGeneratorPage() {
  return (
    <Suspense fallback={<div className="container max-w-4xl py-24 text-center text-white">Loading Blueprint Generator...</div>}>
      <BlueprintGeneratorContent />
    </Suspense>
  );
}
