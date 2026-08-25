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
  Grid,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { assessmentsApi } from '@medical/api-client';
import { AttemptReview, ReviewQuestionItem } from '@medical/shared';
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
  const [mobilePaletteOpen, setMobilePaletteOpen] = useState(false);

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
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="animate-spin h-12 w-12 border-4 border-sky-500 border-t-transparent rounded-full mb-4" />
        <h2 className="text-xl font-bold text-white">Loading Question Review & Evidence...</h2>
        <p className="text-xs text-slate-400 mt-1">Retrieving authoritative citations and explanations...</p>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-xl font-bold text-white">Review Unavailable</h2>
        <p className="text-sm text-slate-400 mt-2">{error || 'Could not load review.'}</p>
        <Button className="mt-6 rounded-2xl" onClick={() => router.push('/student')}>
          Return to Student Hub
        </Button>
      </div>
    );
  }

  const allQuestions = review.review_questions || [];

  const filteredQuestions = allQuestions.filter((q) => {
    if (filter === 'INCORRECT') return q.is_correct === false;
    if (filter === 'CORRECT') return q.is_correct === true;
    if (filter === 'MARKED') return q.marked_for_review;
    return true;
  });

  const currentQ: ReviewQuestionItem | undefined = filteredQuestions[currentIndex] || allQuestions[0];

  // Helper to normalize options
  const getOptionsList = (options: Record<string, string> | any[]): Array<{ key: string; text: string }> => {
    if (Array.isArray(options)) {
      return options.map((opt) => ({
        key: opt.key || opt.option_key || '',
        text: opt.text || opt.option_text || '',
      }));
    }
    if (typeof options === 'object' && options !== null) {
      return Object.entries(options).map(([key, text]) => ({
        key,
        text: String(text),
      }));
    }
    return [];
  };

  const optionsList = currentQ ? getOptionsList(currentQ.options) : [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 pb-20">
      {/* Top Header */}
      <div className="sticky top-0 z-30 border-b border-white/[0.08] bg-slate-950/80 backdrop-blur-xl px-4 sm:px-8 py-4">
        <div className="container max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href={`/student/results/${attemptId}`}>
              <Button variant="outline" size="sm" className="rounded-xl border-white/10 text-slate-300 gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                <span className="hidden sm:inline">Scorecard</span>
              </Button>
            </Link>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-white tracking-tight">
                {review.title} — Review
              </h1>
              <div className="text-xs text-slate-400">
                Score: <strong className="text-white">{review.score}</strong> / {review.max_score} ({review.percentage.toFixed(1)}%)
              </div>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1 p-1 rounded-2xl bg-white/[0.04] border border-white/[0.08] text-xs overflow-x-auto">
            {(['ALL', 'INCORRECT', 'CORRECT', 'MARKED'] as const).map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f);
                  setCurrentIndex(0);
                }}
                className={cn(
                  'px-3 py-1.5 rounded-xl font-bold transition-all whitespace-nowrap cursor-pointer',
                  filter === f
                    ? 'bg-sky-500 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                {f === 'ALL' && `All (${allQuestions.length})`}
                {f === 'INCORRECT' &&
                  `Incorrect (${allQuestions.filter((q) => q.is_correct === false).length})`}
                {f === 'CORRECT' &&
                  `Correct (${allQuestions.filter((q) => q.is_correct === true).length})`}
                {f === 'MARKED' &&
                  `Marked (${allQuestions.filter((q) => q.marked_for_review).length})`}
              </button>
            ))}

            {/* Mobile Grid Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setMobilePaletteOpen(true)}
              className="lg:hidden h-8 px-2.5 rounded-xl text-sky-400"
            >
              <Grid className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="container max-w-7xl mx-auto px-4 py-6">
        {currentQ ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left 3 Columns: Active Review MCQ & Citations */}
            <div className="lg:col-span-3 space-y-6">
              <Card className="glass-card p-5 sm:p-8 rounded-3xl shadow-xl">
                {/* Meta Bar */}
                <div className="flex items-center justify-between gap-3 pb-3 mb-4 border-b border-white/[0.08] flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-white text-base">
                      Question {currentQ.sequence}
                    </span>
                    {currentQ.primary_topic_id && (
                      <Badge variant="secondary" className="text-xs">
                        {currentQ.primary_topic_id.replace('TOPIC-', '')}
                      </Badge>
                    )}
                  </div>

                  <div>
                    {currentQ.is_correct === true ? (
                      <Badge variant="success" className="gap-1 text-xs">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Correct (+4)</span>
                      </Badge>
                    ) : currentQ.selected_answer ? (
                      <Badge variant="destructive" className="gap-1 text-xs">
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Incorrect (-1)</span>
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1 text-xs text-slate-400">
                        <span>Unanswered (0)</span>
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Stem */}
                <div className="text-base sm:text-lg font-medium text-slate-100 leading-relaxed whitespace-pre-wrap mb-6">
                  {currentQ.stem}
                </div>

                {/* Options List */}
                <div className="space-y-3 mb-8">
                  {optionsList.map((opt) => {
                    const isCorrectAnswer = opt.key === currentQ.correct_answer;
                    const isUserChoice = opt.key === currentQ.selected_answer;

                    let cardClass = 'bg-white/[0.02] border-white/[0.08] text-slate-300';
                    if (isCorrectAnswer) {
                      cardClass = 'bg-emerald-500/15 border-emerald-500/50 text-white font-medium shadow-sm ring-1 ring-emerald-500/30';
                    } else if (isUserChoice && currentQ.is_correct === false) {
                      cardClass = 'bg-red-500/15 border-red-500/50 text-red-200';
                    }

                    return (
                      <div
                        key={opt.key}
                        className={cn(
                          'p-4 rounded-2xl border flex items-start gap-3.5 text-sm sm:text-base transition-all',
                          cardClass
                        )}
                      >
                        <div
                          className={cn(
                            'h-7 w-7 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0',
                            isCorrectAnswer
                              ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20'
                              : isUserChoice
                              ? 'bg-red-500 text-white'
                              : 'bg-white/10 text-slate-400'
                          )}
                        >
                          {opt.key}
                        </div>

                        <div className="flex-1 pt-0.5">{opt.text}</div>

                        {isCorrectAnswer && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 px-2 py-0.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30">
                            Ground Truth
                          </span>
                        )}

                        {isUserChoice && !isCorrectAnswer && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-red-400 px-2 py-0.5 rounded-lg bg-red-500/20 border border-red-500/30">
                            Your Choice
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Clinical & Pathological Explanation */}
                {currentQ.explanation && (
                  <div className="p-5 sm:p-6 rounded-2xl bg-sky-950/30 border border-sky-500/20 mb-6">
                    <h4 className="text-xs font-extrabold uppercase tracking-wider text-sky-400 flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-sky-400" />
                      <span>Clinical & Pathological Rationale</span>
                    </h4>
                    <div className="text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                      {currentQ.explanation}
                    </div>
                  </div>
                )}

                {/* Authoritative Citations & Provenance */}
                {currentQ.citations && currentQ.citations.length > 0 && (
                  <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/[0.08]">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-3">
                      <BookOpen className="h-4 w-4 text-indigo-400" />
                      <span>Authoritative Textbook Evidence</span>
                    </h4>
                    <div className="space-y-3">
                      {currentQ.citations.map((c, i) => (
                        <div key={i} className="text-xs p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
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
                            <div className="mt-2 text-slate-300 italic bg-white/[0.02] p-2.5 rounded-lg border-l-2 border-indigo-500">
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
              <div className="flex items-center justify-between gap-2">
                <Button
                  variant="outline"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  className="rounded-2xl border-white/10 gap-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Prev Question</span>
                </Button>

                <span className="text-xs text-slate-400 font-mono">
                  {currentIndex + 1} / {filteredQuestions.length}
                </span>

                <Button
                  variant="gradient"
                  disabled={currentIndex === filteredQuestions.length - 1}
                  onClick={() => setCurrentIndex((prev) => Math.min(filteredQuestions.length - 1, prev + 1))}
                  className="rounded-2xl gap-2 font-bold px-6"
                >
                  <span>Next Question</span>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Right 1 Column: Question Matrix (Desktop) */}
            <div className="hidden lg:block lg:col-span-1">
              <Card className="glass-card p-5 rounded-3xl sticky top-24">
                <h3 className="font-bold text-white text-sm mb-3">Questions in Review</h3>
                <div className="grid grid-cols-5 gap-2 max-h-[500px] overflow-y-auto pr-1">
                  {filteredQuestions.map((q, idx) => {
                    const isCurrent = idx === currentIndex;
                    let badgeClass = 'bg-white/5 text-slate-400 border-white/10';
                    if (q.is_correct === true) {
                      badgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold';
                    } else if (q.selected_answer) {
                      badgeClass = 'bg-red-500/20 text-red-300 border-red-500/40 font-bold';
                    }

                    return (
                      <button
                        key={q.question_id}
                        onClick={() => setCurrentIndex(idx)}
                        className={cn(
                          'h-9 rounded-xl border text-xs font-bold flex items-center justify-center transition-all cursor-pointer',
                          badgeClass,
                          isCurrent && 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-105'
                        )}
                      >
                        {q.sequence}
                      </button>
                    );
                  })}
                </div>
              </Card>
            </div>
          </div>
        ) : (
          <div className="text-center py-20 text-slate-400 text-sm">
            No questions match the selected filter.
          </div>
        )}
      </div>

      {/* Mobile Question Palette Drawer */}
      {mobilePaletteOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border-t border-white/15 p-5 rounded-t-3xl max-h-[75vh] overflow-y-auto animate-in slide-in-from-bottom">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-base">Select Question</h3>
              <button
                onClick={() => setMobilePaletteOpen(false)}
                className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center text-slate-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-5 gap-2 pb-4">
              {filteredQuestions.map((q, idx) => {
                const isCurrent = idx === currentIndex;
                let badgeClass = 'bg-white/5 text-slate-400 border-white/10';
                if (q.is_correct === true) {
                  badgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold';
                } else if (q.selected_answer) {
                  badgeClass = 'bg-red-500/20 text-red-300 border-red-500/40 font-bold';
                }

                return (
                  <button
                    key={q.question_id}
                    onClick={() => {
                      setCurrentIndex(idx);
                      setMobilePaletteOpen(false);
                    }}
                    className={cn(
                      'h-10 rounded-xl border text-xs font-bold flex items-center justify-center transition-all cursor-pointer',
                      badgeClass,
                      isCurrent && 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-105'
                    )}
                  >
                    {q.sequence}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
