'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  CheckCircle2,
  XCircle,
  BookOpen,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { assessmentsApi } from '@medical/api-client';
import { AttemptReview } from '@medical/shared';
import { cn } from '@/lib/utils';

export default function ExamReviewPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = params?.attemptId as string;

  const [loading, setLoading] = useState(true);
  const [review, setReview] = useState<AttemptReview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<'ALL' | 'INCORRECT' | 'CORRECT' | 'MARKED'>('ALL');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    async function loadReview() {
      try {
        setLoading(true);
        const data = await assessmentsApi.getReview(attemptId);
        setReview(data);
      } catch (err: any) {
        console.error('Failed to load exam review:', err);
        setError(err?.message || 'Unable to retrieve question review.');
      } finally {
        setLoading(false);
      }
    }

    if (attemptId) {
      loadReview();
    }
  }, [attemptId]);

  if (loading) {
    return (
      <div className="container max-w-4xl py-24 text-center">
        <div className="animate-spin h-10 w-10 border-4 border-sky-500 border-t-transparent rounded-full mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white">Loading Question Review & Evidence...</h2>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="container max-w-md py-24 text-center">
        <h2 className="text-xl font-bold text-white">Review Unavailable</h2>
        <p className="text-sm text-slate-400 mt-2">{error || 'Could not load review.'}</p>
        <Button className="mt-6" onClick={() => router.push('/student')}>
          Return to Student Hub
        </Button>
      </div>
    );
  }

  const filteredQuestions = review.questions.filter((q) => {
    if (filter === 'INCORRECT') return !q.is_correct && q.user_selected_answer !== null;
    if (filter === 'CORRECT') return q.is_correct;
    if (filter === 'MARKED') return q.is_marked_for_review;
    return true;
  });

  const currentQ = filteredQuestions[currentIndex] || review.questions[0];

  return (
    <div className="container max-w-6xl px-4 sm:px-8 py-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/[0.08] mb-6">
        <div className="flex items-center gap-3">
          <Link href={`/student/results/${attemptId}`}>
            <Button variant="outline" size="sm" className="gap-1.5 border-white/10 text-slate-300">
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Scorecard</span>
            </Button>
          </Link>
          <h1 className="text-xl font-bold text-white tracking-tight">
            {review.title} — Detailed Question Review
          </h1>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs">
          {(['ALL', 'INCORRECT', 'CORRECT', 'MARKED'] as const).map((f) => (
            <button
              key={f}
              onClick={() => {
                setFilter(f);
                setCurrentIndex(0);
              }}
              className={cn(
                'px-3 py-1.5 rounded-lg font-medium transition-colors',
                filter === f
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              {f === 'ALL' && `All (${review.questions.length})`}
              {f === 'INCORRECT' &&
                `Incorrect (${review.questions.filter((q) => !q.is_correct && q.user_selected_answer !== null).length})`}
              {f === 'CORRECT' &&
                `Correct (${review.questions.filter((q) => q.is_correct).length})`}
              {f === 'MARKED' &&
                `Marked (${review.questions.filter((q) => q.is_marked_for_review).length})`}
            </button>
          ))}
        </div>
      </div>

      {currentQ ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Question + Explanation Column */}
          <div className="lg:col-span-3 space-y-6">
            <Card className="glass-card p-6 sm:p-8">
              {/* Question Meta */}
              <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-base">
                    Question {currentQ.item_order}
                  </span>
                  {currentQ.topic_name && (
                    <Badge variant="secondary" className="text-xs">
                      {currentQ.topic_name}
                    </Badge>
                  )}
                </div>

                <div>
                  {currentQ.is_correct ? (
                    <Badge variant="success" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>Correct (+4)</span>
                    </Badge>
                  ) : currentQ.user_selected_answer ? (
                    <Badge variant="destructive" className="gap-1">
                      <XCircle className="h-3 w-3" />
                      <span>Incorrect (-1)</span>
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="gap-1 text-slate-400">
                      <span>Unanswered (0)</span>
                    </Badge>
                  )}
                </div>
              </div>

              {/* Stem */}
              <div className="text-base sm:text-lg font-medium text-slate-100 leading-relaxed whitespace-pre-wrap mb-6">
                {currentQ.stem}
              </div>

              {/* Options Breakdown */}
              <div className="space-y-3 mb-8">
                {currentQ.options.map((opt) => {
                  const isCorrectAnswer = opt.key === currentQ.correct_answer;
                  const isUserSelection = opt.key === currentQ.user_selected_answer;

                  let borderClass = 'bg-white/[0.02] border-white/[0.08] text-slate-300';
                  if (isCorrectAnswer) {
                    borderClass = 'bg-emerald-500/15 border-emerald-500/50 text-white font-medium';
                  } else if (isUserSelection && !currentQ.is_correct) {
                    borderClass = 'bg-red-500/15 border-red-500/50 text-red-200';
                  }

                  return (
                    <div
                      key={opt.key}
                      className={cn(
                        'p-4 rounded-xl border flex items-start gap-3.5 text-sm sm:text-base transition-all',
                        borderClass
                      )}
                    >
                      <div
                        className={cn(
                          'h-7 w-7 rounded-lg flex items-center justify-center font-bold text-xs flex-shrink-0',
                          isCorrectAnswer
                            ? 'bg-emerald-500 text-white shadow-sm'
                            : isUserSelection
                            ? 'bg-red-500 text-white'
                            : 'bg-white/10 text-slate-400'
                        )}
                      >
                        {opt.key}
                      </div>
                      <div className="flex-1 pt-0.5">{opt.text}</div>
                      {isCorrectAnswer && (
                        <span className="text-xs font-semibold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/20">
                          Ground Truth
                        </span>
                      )}
                      {isUserSelection && !isCorrectAnswer && (
                        <span className="text-xs font-semibold text-red-400 px-2 py-0.5 rounded bg-red-500/20">
                          Your Choice
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Comprehensive Medical Explanation */}
              {currentQ.explanation && (
                <div className="p-5 rounded-2xl bg-sky-950/30 border border-sky-500/20 mb-6">
                  <h4 className="text-sm font-bold text-sky-300 flex items-center gap-2 mb-2">
                    <Sparkles className="h-4 w-4 text-sky-400" />
                    <span>Clinical & Pathological Explanation</span>
                  </h4>
                  <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                    {currentQ.explanation}
                  </div>
                </div>
              )}

              {/* Authoritative Citations & Provenance */}
              {currentQ.citations && currentQ.citations.length > 0 && (
                <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.08]">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-3">
                    <BookOpen className="h-4 w-4 text-indigo-400" />
                    <span>Authoritative Textbook Citations</span>
                  </h4>
                  <div className="space-y-3">
                    {currentQ.citations.map((c, i) => (
                      <div key={i} className="text-xs p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-white">{c.source_title}</span>
                          <Badge
                            variant={c.verification_status === 'HUMAN_VERIFIED' ? 'verified' : 'suggested'}
                            className="text-[10px]"
                          >
                            {c.verification_status}
                          </Badge>
                        </div>
                        {c.chapter && <div className="text-slate-300">Chapter: {c.chapter}</div>}
                        {c.page_range && <div className="text-slate-400">Pages: {c.page_range}</div>}
                        {c.evidence_text && (
                          <div className="mt-2 text-slate-300 italic bg-white/[0.02] p-2 rounded border-l-2 border-indigo-500">
                            &quot;{c.evidence_text}&quot;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            {/* Prev / Next Review Controls */}
            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                className="gap-2 border-white/10"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous Question</span>
              </Button>

              <span className="text-xs text-muted-foreground">
                Showing {currentIndex + 1} of {filteredQuestions.length}
              </span>

              <Button
                variant="gradient"
                disabled={currentIndex === filteredQuestions.length - 1}
                onClick={() => setCurrentIndex((prev) => Math.min(filteredQuestions.length - 1, prev + 1))}
                className="gap-2"
              >
                <span>Next Question</span>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Right Column: Question Navigator List */}
          <div className="lg:col-span-1">
            <Card className="glass-card p-5">
              <h3 className="font-bold text-white text-sm mb-3">Questions in Review</h3>
              <div className="grid grid-cols-5 gap-2 max-h-[500px] overflow-y-auto pr-1">
                {filteredQuestions.map((q, idx) => {
                  const isCurrent = idx === currentIndex;
                  let badgeColor = 'bg-white/5 text-slate-400 border-white/10';
                  if (q.is_correct) {
                    badgeColor = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
                  } else if (q.user_selected_answer) {
                    badgeColor = 'bg-red-500/20 text-red-300 border-red-500/40';
                  }

                  return (
                    <button
                      key={q.question_id}
                      onClick={() => setCurrentIndex(idx)}
                      className={cn(
                        'h-9 rounded-lg border text-xs font-semibold flex items-center justify-center transition-all',
                        badgeColor,
                        isCurrent && 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-105'
                      )}
                    >
                      {q.item_order}
                    </button>
                  );
                })}
              </div>
            </Card>
          </div>
        </div>
      ) : (
        <div className="text-center py-16 text-slate-400">
          No questions match the selected filter.
        </div>
      )}
    </div>
  );
}
