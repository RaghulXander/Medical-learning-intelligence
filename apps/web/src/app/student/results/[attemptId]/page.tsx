'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import confetti from 'canvas-confetti';
import {
  Clock,
  RotateCcw,
  BookOpen,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { assessmentsApi } from '@medical/api-client';
import { AttemptResults } from '@medical/shared';
import { formatTime } from '@/lib/utils';

export default function ExamResultsPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = params?.attemptId as string;

  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<AttemptResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResults() {
      try {
        setLoading(true);
        const data = await assessmentsApi.getResults(attemptId);
        setResults(data);

        // Fire celebration confetti if score > 50%
        if (data.percentage >= 50) {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
          });
        }
      } catch (err: any) {
        console.error('Failed to load exam results:', err);
        setError(err?.message || 'Unable to retrieve exam scorecard.');
      } finally {
        setLoading(false);
      }
    }

    if (attemptId) {
      loadResults();
    }
  }, [attemptId]);

  if (loading) {
    return (
      <div className="container max-w-4xl py-24 text-center">
        <div className="animate-spin h-10 w-10 border-4 border-sky-500 border-t-transparent rounded-full mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white">Computing Scorecard...</h2>
        <p className="text-sm text-slate-400 mt-1">Evaluating diagnostic performance and topic accuracy...</p>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="container max-w-md py-24 text-center">
        <h2 className="text-xl font-bold text-white">Results Not Found</h2>
        <p className="text-sm text-slate-400 mt-2">{error || 'Could not find scorecard for this attempt.'}</p>
        <Button className="mt-6" onClick={() => router.push('/student')}>
          Back to Student Hub
        </Button>
      </div>
    );
  }

  return (
    <div className="container max-w-5xl px-4 sm:px-8 py-10">
      {/* Top Banner */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <Badge variant="verified" className="mb-3">
          Assessment Complete
        </Badge>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Performance Diagnostic Scorecard
        </h1>
        <p className="text-muted-foreground text-sm mt-2">
          Review your NEET marking score (+4 / -1), question accuracy, and subject breakdown below.
        </p>
      </div>

      {/* Main Scorecard Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {/* Score Tile */}
        <Card className="glass-card p-6 border-sky-500/30 text-center flex flex-col justify-between">
          <div className="text-xs font-semibold text-sky-400 uppercase tracking-wider mb-2">Final Score</div>
          <div className="text-4xl font-extrabold text-white">
            {results.score}{' '}
            <span className="text-base font-normal text-muted-foreground">/ {results.max_score}</span>
          </div>
          <div className="text-xs text-slate-400 mt-2 font-medium">
            {results.percentage.toFixed(1)}% Marks Achieved
          </div>
        </Card>

        {/* Accuracy */}
        <Card className="glass-card p-6 text-center flex flex-col justify-between">
          <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">Accuracy</div>
          <div className="text-4xl font-extrabold text-emerald-400">
            {results.accuracy.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-2 font-medium">
            {results.correct_count} of {results.answered_questions} Correct
          </div>
        </Card>

        {/* Correct vs Incorrect */}
        <Card className="glass-card p-6 flex flex-col justify-between">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Response Split</div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-emerald-400 font-semibold">
              <span>Correct (+4)</span>
              <span>{results.correct_count}</span>
            </div>
            <div className="flex justify-between text-red-400 font-semibold">
              <span>Incorrect (-1)</span>
              <span>{results.incorrect_count}</span>
            </div>
            <div className="flex justify-between text-slate-400 font-semibold">
              <span>Unanswered (0)</span>
              <span>{results.unanswered_count}</span>
            </div>
          </div>
        </Card>

        {/* Time Spent */}
        <Card className="glass-card p-6 text-center flex flex-col justify-between">
          <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">Time Spent</div>
          <div className="text-3xl font-extrabold text-white flex items-center justify-center gap-1.5">
            <Clock className="h-5 w-5 text-indigo-400" />
            <span>{formatTime(results.time_spent_seconds)}</span>
          </div>
          <div className="text-xs text-slate-400 mt-2 font-medium">
            ~{(results.time_spent_seconds / Math.max(1, results.total_questions)).toFixed(0)}s per question
          </div>
        </Card>
      </div>

      {/* Topic Accuracy Breakdown */}
      <Card className="glass-card p-6 mb-8">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="h-5 w-5 text-sky-400" />
          <span>Topic-Wise Mastery Breakdown</span>
        </h3>

        {results.topic_breakdown && results.topic_breakdown.length > 0 ? (
          <div className="space-y-4">
            {results.topic_breakdown.map((t, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="font-semibold text-white">{t.topic_name}</span>
                  <span className="text-xs font-medium text-slate-300">
                    {t.correct}/{t.total} ({t.accuracy.toFixed(0)}%)
                  </span>
                </div>
                <Progress value={t.accuracy} className="h-2" />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Standard general pathology distribution tested.</p>
        )}
      </Card>

      {/* Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-6 rounded-2xl glass-panel border border-white/15">
        <div>
          <h4 className="text-base font-bold text-white">Review Detailed Explanations & Citations</h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Inspect ground truth rationale and authoritative references (Robbins, WHO Blue Books).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/student">
            <Button variant="outline" className="gap-2 border-white/15">
              <RotateCcw className="h-4 w-4" />
              <span>Practice Another Test</span>
            </Button>
          </Link>

          <Link href={`/student/review/${attemptId}`}>
            <Button variant="gradient" className="gap-2">
              <BookOpen className="h-4 w-4" />
              <span>Open Detailed Review</span>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
