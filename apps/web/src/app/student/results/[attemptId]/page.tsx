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
  TrendingDown,
  Zap,
  CheckCircle2,
  XCircle,
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
  const [remediating, setRemediating] = useState(false);

  useEffect(() => {
    async function loadResults() {
      try {
        setLoading(true);
        const data = await assessmentsApi.getResults(attemptId);
        setResults(data);

        // Fire celebration confetti if score > 50%
        if (data.percentage >= 50) {
          confetti({
            particleCount: 90,
            spread: 75,
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

  // 1-Click Remediation Test Generator
  const handleLaunchRemediation = async () => {
    if (!results || !results.weak_topics || results.weak_topics.length === 0) return;
    try {
      setRemediating(true);
      const targetTopic = results.weak_topics[0] || 'TOPIC-CELL-INJURY';

      const assessment = await assessmentsApi.createAssessment({
        title: `Remediation Drill: ${targetTopic.replace('TOPIC-', '')}`,
        type: 'TOPIC',
        question_count: 15,
        duration_seconds: 900,
        marking_scheme_id: 'NEET_4_1',
        blueprint: { topic_id: targetTopic },
      });

      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err: any) {
      console.error('Failed to launch remediation test:', err);
      alert('Remediation launch error: ' + (err?.message || 'Please try again.'));
      setRemediating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="animate-spin h-12 w-12 border-4 border-sky-500 border-t-transparent rounded-full mb-4" />
        <h2 className="text-xl font-bold text-white">Computing Diagnostic Scorecard...</h2>
        <p className="text-xs text-slate-400 mt-1">Evaluating NEET score metrics and topic accuracies...</p>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-xl font-bold text-white">Results Unavailable</h2>
        <p className="text-sm text-slate-400 mt-2">{error || 'Could not find scorecard for this session.'}</p>
        <Button className="mt-6 rounded-2xl" onClick={() => router.push('/student')}>
          Back to Student Hub
        </Button>
      </div>
    );
  }

  const hasWeakTopics = results.weak_topics && results.weak_topics.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 pb-20">
      {/* Top Banner */}
      <div className="border-b border-white/[0.08] bg-slate-950/80 backdrop-blur-xl px-4 sm:px-8 py-6">
        <div className="container max-w-5xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="verified" className="text-xs">
                Assessment Complete
              </Badge>
              <span className="text-xs font-mono text-slate-400">
                {results.marking_scheme?.name || 'NEET Standard'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Diagnostic Performance Scorecard
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">{results.title}</p>
          </div>

          <div className="flex items-center gap-2">
            <Link href={`/student/review/${attemptId}`}>
              <Button variant="gradient" size="sm" className="rounded-xl font-bold gap-1.5 shadow-lg shadow-sky-500/20">
                <BookOpen className="h-4 w-4" />
                <span>Question Review</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="container max-w-5xl mx-auto px-4 sm:px-8 pt-6 sm:pt-8 space-y-6">
        {/* 1-Click Remediation Banner if Weak Topics Identified */}
        {hasWeakTopics && (
          <div className="p-5 sm:p-6 rounded-3xl bg-gradient-to-r from-purple-950/60 via-indigo-950/40 to-slate-900/80 border border-purple-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl shadow-purple-500/5 animate-in fade-in">
            <div className="flex items-start gap-3.5">
              <div className="h-10 w-10 rounded-2xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center flex-shrink-0">
                <Zap className="h-5 w-5 text-purple-400 fill-purple-400" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-white">Targeted Remediation Recommendation</h3>
                <p className="text-xs text-slate-300 mt-0.5 max-w-xl leading-relaxed">
                  You scored below 50% in{' '}
                  <strong className="text-purple-300">
                    {results.weak_topics.map((t) => t.replace('TOPIC-', '')).join(', ')}
                  </strong>
                  . Launch an instant 15-MCQ drill to cement high-yield diagnostic criteria.
                </p>
              </div>
            </div>

            <Button
              variant="gradient"
              className="rounded-2xl font-bold text-xs gap-2 px-5 py-5 shadow-lg shadow-purple-500/25 active:scale-95 transition-transform"
              disabled={remediating}
              onClick={handleLaunchRemediation}
            >
              {remediating ? 'Creating Drill...' : 'Launch 15-MCQ Drill →'}
            </Button>
          </div>
        )}

        {/* Main Score & Metric Tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          {/* Score Tile */}
          <Card className="glass-card p-5 sm:p-6 text-center rounded-3xl flex flex-col justify-between border-sky-500/30">
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-sky-400 mb-1">
              Final Marks
            </div>
            <div className="text-3xl sm:text-4xl font-black text-white">
              {results.score}
              <span className="text-sm sm:text-base font-normal text-slate-400 ml-1">/ {results.max_score}</span>
            </div>
            <div className="text-[11px] font-semibold text-slate-400 mt-2">
              {results.percentage.toFixed(1)}% Marks Achieved
            </div>
          </Card>

          {/* Accuracy Tile */}
          <Card className="glass-card p-5 sm:p-6 text-center rounded-3xl flex flex-col justify-between border-emerald-500/30">
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-400 mb-1">
              Accuracy
            </div>
            <div className="text-3xl sm:text-4xl font-black text-emerald-400">
              {results.accuracy.toFixed(1)}%
            </div>
            <div className="text-[11px] font-semibold text-slate-400 mt-2">
              {results.correct_count} of {results.attempted_count} Correct
            </div>
          </Card>

          {/* Negative Marks Lost */}
          <Card className="glass-card p-5 sm:p-6 text-center rounded-3xl flex flex-col justify-between border-rose-500/30">
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-rose-400 mb-1">
              Negative Lost
            </div>
            <div className="text-3xl sm:text-4xl font-black text-rose-400 flex items-center justify-center gap-1">
              <TrendingDown className="h-5 w-5" />
              <span>-{results.negative_marks_lost}</span>
            </div>
            <div className="text-[11px] font-semibold text-slate-400 mt-2">
              {results.incorrect_count} Wrong Attempts
            </div>
          </Card>

          {/* Speed Velocity */}
          <Card className="glass-card p-5 sm:p-6 text-center rounded-3xl flex flex-col justify-between">
            <div className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-400 mb-1">
              Velocity
            </div>
            <div className="text-3xl sm:text-4xl font-black text-white flex items-center justify-center gap-1.5">
              <Clock className="h-5 w-5 text-indigo-400" />
              <span>{results.avg_seconds_per_question}s</span>
            </div>
            <div className="text-[11px] font-semibold text-slate-400 mt-2">
              Total Time: {formatTime(results.time_spent_seconds)}
            </div>
          </Card>
        </div>

        {/* Response Split Breakdown */}
        <Card className="glass-card p-6 sm:p-8 rounded-3xl">
          <h3 className="text-base font-bold text-white mb-4">Response Distribution</h3>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25">
              <div className="text-xs text-emerald-300 font-bold flex items-center justify-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Correct (+4)</span>
              </div>
              <div className="text-2xl font-black text-white mt-1">{results.correct_count}</div>
            </div>

            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/25">
              <div className="text-xs text-rose-300 font-bold flex items-center justify-center gap-1">
                <XCircle className="h-3.5 w-3.5" />
                <span>Incorrect (-1)</span>
              </div>
              <div className="text-2xl font-black text-white mt-1">{results.incorrect_count}</div>
            </div>

            <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-xs text-slate-400 font-bold">Unanswered (0)</div>
              <div className="text-2xl font-black text-slate-300 mt-1">{results.unanswered_count}</div>
            </div>
          </div>
        </Card>

        {/* Topic-Wise Mastery Progress */}
        <Card className="glass-card p-6 sm:p-8 rounded-3xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-sky-400" />
              <h3 className="text-base sm:text-lg font-bold text-white">Topic-Wise Mastery Analytics</h3>
            </div>
            <span className="text-xs text-slate-400">Diagnostic Granularity</span>
          </div>

          <div className="space-y-4">
            {results.topic_breakdown && results.topic_breakdown.length > 0 ? (
              results.topic_breakdown.map((t, idx) => {
                const acc = t.accuracy;
                let statusBadge = (
                  <Badge variant="success" className="text-[10px]">
                    Mastered ({acc.toFixed(0)}%)
                  </Badge>
                );
                if (acc < 50) {
                  statusBadge = (
                    <Badge variant="destructive" className="text-[10px]">
                      Needs Focus ({acc.toFixed(0)}%)
                    </Badge>
                  );
                } else if (acc < 75) {
                  statusBadge = (
                    <Badge variant="warning" className="text-[10px]">
                      Moderate ({acc.toFixed(0)}%)
                    </Badge>
                  );
                }

                return (
                  <div key={idx} className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="flex items-center justify-between text-xs sm:text-sm mb-2 gap-2">
                      <span className="font-bold text-white truncate">{t.topic}</span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-slate-400 text-xs">
                          {t.correct}/{t.total} Qs
                        </span>
                        {statusBadge}
                      </div>
                    </div>
                    <Progress value={acc} className="h-2.5 rounded-full" />
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">Comprehensive general pathology mix tested.</p>
            )}
          </div>
        </Card>

        {/* Action Footer Navigation */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-3xl glass-panel border border-white/15">
          <div>
            <h4 className="text-base font-extrabold text-white">Deep Question Review</h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect ground truth rationale and authoritative textbook citations (Robbins, WHO Blue Books).
            </p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Link href="/student" className="flex-1 sm:flex-initial">
              <Button variant="outline" className="w-full rounded-2xl border-white/15 gap-2">
                <RotateCcw className="h-4 w-4" />
                <span>Practice Hub</span>
              </Button>
            </Link>

            <Link href={`/student/review/${attemptId}`} className="flex-1 sm:flex-initial">
              <Button variant="gradient" className="w-full rounded-2xl font-bold gap-2 shadow-lg shadow-sky-500/20">
                <BookOpen className="h-4 w-4" />
                <span>Open Full Review</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
