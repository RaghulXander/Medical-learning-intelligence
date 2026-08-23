'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Clock,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Send,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { assessmentsApi } from '@medical/api-client';
import { SanitizedQuestion, HeartbeatQuestionResponse } from '@medical/shared';
import { formatTime, cn } from '@/lib/utils';

export default function ExamRunnerPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = params?.attemptId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [questions, setQuestions] = useState<SanitizedQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(3000);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // User state map: question_id -> { selected_answer, marked_for_review, time_spent_seconds }
  const [userResponses, setUserResponses] = useState<
    Record<string, { selected_answer: string | null; marked_for_review: boolean; time_spent_seconds: number }>
  >({});

  const [submitting, setSubmitting] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  // Timer reference
  useEffect(() => {
    async function loadAttempt() {
      try {
        setLoading(true);
        const data = await assessmentsApi.getAttemptState(attemptId);
        setQuestions(data.questions || []);
        setDurationSeconds(data.duration_seconds || 3000);
        setElapsedSeconds(data.elapsed_seconds || 0);

        // Prepopulate responses if resuming
        const initMap: Record<string, any> = {};
        (data.questions || []).forEach((q: any) => {
          initMap[q.question_id] = {
            selected_answer: null,
            marked_for_review: false,
            time_spent_seconds: 0,
          };
        });

        (data.responses || []).forEach((r: any) => {
          if (initMap[r.question_id]) {
            initMap[r.question_id].selected_answer = r.selected_answer;
            initMap[r.question_id].marked_for_review = r.marked_for_review;
            initMap[r.question_id].time_spent_seconds = r.time_spent_seconds || 0;
          }
        });

        setUserResponses(initMap);
      } catch (err: any) {
        console.error('Failed to load attempt state:', err);
        setError(err?.message || 'Could not load exam session.');
      } finally {
        setLoading(false);
      }
    }

    if (attemptId) {
      loadAttempt();
    }
  }, [attemptId]);

  // Countdown timer effect
  useEffect(() => {
    if (loading || submitting) return;

    const timer = setInterval(() => {
      setElapsedSeconds((prev) => {
        const next = prev + 1;
        if (next >= durationSeconds) {
          clearInterval(timer);
          handleSubmitExam();
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [loading, submitting, durationSeconds]);

  // Periodic heartbeat sync
  useEffect(() => {
    if (loading || submitting || !attemptId) return;

    const heartbeatInterval = setInterval(async () => {
      try {
        const responsesList: HeartbeatQuestionResponse[] = Object.entries(userResponses).map(
          ([qid, val]) => ({
            question_id: qid,
            selected_answer: val.selected_answer,
            marked_for_review: val.marked_for_review,
            time_spent_seconds: val.time_spent_seconds,
          })
        );
        await assessmentsApi.recordHeartbeat(attemptId, {
          responses: responsesList,
          elapsed_seconds: elapsedSeconds,
        });
      } catch (err) {
        console.warn('Heartbeat background sync failed:', err);
      }
    }, 15000);

    return () => clearInterval(heartbeatInterval);
  }, [attemptId, userResponses, elapsedSeconds, loading, submitting]);

  const currentQ = questions[currentIndex];
  const currentResp = currentQ ? userResponses[currentQ.question_id] : null;

  const handleSelectOption = (key: string) => {
    if (!currentQ) return;
    setUserResponses((prev) => ({
      ...prev,
      [currentQ.question_id]: {
        ...prev[currentQ.question_id],
        selected_answer: key,
      },
    }));
  };

  const handleToggleMarkReview = () => {
    if (!currentQ) return;
    setUserResponses((prev) => ({
      ...prev,
      [currentQ.question_id]: {
        ...prev[currentQ.question_id],
        marked_for_review: !prev[currentQ.question_id]?.marked_for_review,
      },
    }));
  };

  const handleClearAnswer = () => {
    if (!currentQ) return;
    setUserResponses((prev) => ({
      ...prev,
      [currentQ.question_id]: {
        ...prev[currentQ.question_id],
        selected_answer: null,
      },
    }));
  };

  const handleSubmitExam = async () => {
    try {
      setSubmitting(true);
      const responsesList: HeartbeatQuestionResponse[] = Object.entries(userResponses).map(
        ([qid, val]) => ({
          question_id: qid,
          selected_answer: val.selected_answer,
          marked_for_review: val.marked_for_review,
          time_spent_seconds: val.time_spent_seconds,
        })
      );

      await assessmentsApi.submitAttempt(attemptId, {
        responses: responsesList,
        final_elapsed_seconds: elapsedSeconds,
      });

      router.push(`/student/results/${attemptId}`);
    } catch (err: any) {
      console.error('Failed to submit exam:', err);
      alert('Submission error: ' + (err?.message || 'Please retry.'));
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container max-w-4xl py-24 text-center">
        <div className="animate-spin h-10 w-10 border-4 border-sky-500 border-t-transparent rounded-full mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white">Initializing Exam Runner...</h2>
        <p className="text-sm text-slate-400 mt-1">Freezing question snapshot and starting timer...</p>
      </div>
    );
  }

  if (error || !currentQ) {
    return (
      <div className="container max-w-md py-24 text-center">
        <AlertTriangle className="h-12 w-12 text-amber-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white">Exam Session Unavailable</h2>
        <p className="text-sm text-slate-400 mt-2">{error || 'No questions found for this attempt.'}</p>
        <Button className="mt-6" onClick={() => router.push('/student')}>
          Return to Student Hub
        </Button>
      </div>
    );
  }

  const remainingSeconds = Math.max(0, durationSeconds - elapsedSeconds);
  const isTimeCritical = remainingSeconds < 300; // < 5 mins

  // Computed counts
  const totalCount = questions.length;
  const answeredCount = Object.values(userResponses).filter((r) => r.selected_answer !== null).length;
  const markedCount = Object.values(userResponses).filter((r) => r.marked_for_review).length;

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col bg-slate-950">
      {/* Top Runner Bar */}
      <div className="sticky top-16 z-40 border-b border-white/[0.08] bg-slate-950/95 backdrop-blur-md px-4 py-3">
        <div className="container max-w-7xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-bold text-white text-base">
              Question {currentIndex + 1}{' '}
              <span className="text-xs font-normal text-muted-foreground">of {totalCount}</span>
            </span>
            {currentQ.topic_name && (
              <Badge variant="secondary" className="hidden sm:inline-flex text-xs">
                {currentQ.topic_name}
              </Badge>
            )}
          </div>

          {/* Center Timer */}
          <div
            className={cn(
              'flex items-center gap-2 px-4 py-1.5 rounded-xl font-mono text-sm font-bold border transition-colors',
              isTimeCritical
                ? 'bg-red-500/20 border-red-500/40 text-red-300 animate-pulse'
                : 'bg-white/5 border-white/10 text-white'
            )}
          >
            <Clock className="h-4 w-4 text-sky-400" />
            <span>{formatTime(remainingSeconds)}</span>
          </div>

          {/* Submit Action */}
          <Button
            variant="destructive"
            size="sm"
            className="gap-1.5 bg-red-600 hover:bg-red-700 font-semibold"
            onClick={() => setShowSubmitModal(true)}
          >
            <Send className="h-3.5 w-3.5" />
            <span>End Test</span>
          </Button>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="container max-w-7xl px-4 py-6 flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left 3 Columns: Active Question & Stem */}
        <div className="lg:col-span-3 flex flex-col justify-between">
          <Card className="glass-card p-6 sm:p-8 flex-1 flex flex-col justify-between mb-6">
            <div>
              {/* Question Stem */}
              <div className="text-base sm:text-lg font-medium text-slate-100 leading-relaxed whitespace-pre-wrap mb-8">
                {currentQ.stem}
              </div>

              {/* Options List */}
              <div className="space-y-3">
                {currentQ.options.map((opt) => {
                  const isSelected = currentResp?.selected_answer === opt.key;
                  return (
                    <button
                      key={opt.key}
                      onClick={() => handleSelectOption(opt.key)}
                      className={cn(
                        'w-full p-4 rounded-xl border text-left flex items-start gap-3.5 transition-all text-sm sm:text-base font-normal',
                        isSelected
                          ? 'bg-sky-500/20 border-sky-400 text-white shadow-lg shadow-sky-500/10 ring-1 ring-sky-400'
                          : 'bg-white/[0.03] border-white/[0.08] text-slate-200 hover:bg-white/[0.07] hover:border-white/20'
                      )}
                    >
                      <div
                        className={cn(
                          'h-7 w-7 rounded-lg flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors',
                          isSelected
                            ? 'bg-sky-500 text-white shadow-sm'
                            : 'bg-white/10 text-slate-300'
                        )}
                      >
                        {opt.key}
                      </div>
                      <div className="flex-1 pt-0.5">{opt.text}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Bottom Actions for current question */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-6 mt-8 border-t border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleToggleMarkReview}
                  className={cn(
                    'gap-1.5 text-xs',
                    currentResp?.marked_for_review
                      ? 'border-amber-500/50 bg-amber-500/20 text-amber-300'
                      : 'border-white/10 text-slate-300'
                  )}
                >
                  <Bookmark className="h-3.5 w-3.5" />
                  <span>{currentResp?.marked_for_review ? 'Marked for Review' : 'Mark for Review'}</span>
                </Button>

                {currentResp?.selected_answer && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearAnswer}
                    className="text-xs text-slate-400 hover:text-white gap-1"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Clear Answer</span>
                  </Button>
                )}
              </div>

              {/* Prev / Next Navigation */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  className="gap-1 border-white/10"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Previous</span>
                </Button>

                <Button
                  variant="gradient"
                  size="sm"
                  disabled={currentIndex === totalCount - 1}
                  onClick={() => setCurrentIndex((prev) => Math.min(totalCount - 1, prev + 1))}
                  className="gap-1 px-5"
                >
                  <span>Next</span>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Right 1 Column: Question Matrix Palette */}
        <div className="lg:col-span-1">
          <Card className="glass-card p-5 h-full flex flex-col justify-between">
            <div>
              <h3 className="font-bold text-white text-sm mb-3">Question Palette</h3>

              {/* Status Summary */}
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 mb-4 pb-4 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-sm bg-sky-500" />
                  <span>Answered ({answeredCount})</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-sm bg-amber-500" />
                  <span>Marked ({markedCount})</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-sm bg-white/10" />
                  <span>Unanswered ({totalCount - answeredCount})</span>
                </div>
              </div>

              {/* Palette Grid */}
              <div className="grid grid-cols-5 gap-2 max-h-[380px] overflow-y-auto pr-1">
                {questions.map((q, idx) => {
                  const resp = userResponses[q.question_id];
                  const isCurrent = idx === currentIndex;
                  const isAnswered = resp?.selected_answer !== null;
                  const isMarked = resp?.marked_for_review;

                  let colorClass = 'bg-white/5 text-slate-400 hover:bg-white/10 border-white/10';
                  if (isMarked) {
                    colorClass = 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold';
                  } else if (isAnswered) {
                    colorClass = 'bg-sky-500 text-white border-sky-400 font-bold';
                  }

                  return (
                    <button
                      key={q.question_id}
                      onClick={() => setCurrentIndex(idx)}
                      className={cn(
                        'h-9 rounded-lg border text-xs font-semibold flex items-center justify-center transition-all',
                        colorClass,
                        isCurrent && 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-105'
                      )}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quick Submit */}
            <div className="pt-4 mt-4 border-t border-white/[0.08]">
              <Button
                variant="gradient"
                className="w-full"
                onClick={() => setShowSubmitModal(true)}
              >
                Submit Assessment
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-white/15 animate-in fade-in zoom-in-95">
            <h3 className="text-xl font-bold text-white mb-2">Submit Mock Assessment?</h3>
            <p className="text-sm text-slate-300 mb-6">
              You have answered <strong className="text-sky-400">{answeredCount}</strong> of{' '}
              <strong>{totalCount}</strong> questions ({totalCount - answeredCount} unanswered). Once submitted, your score and detailed topic breakdown will be generated immediately.
            </p>

            <div className="flex items-center justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
              >
                Continue Test
              </Button>
              <Button
                variant="destructive"
                onClick={handleSubmitExam}
                disabled={submitting}
                className="bg-red-600 hover:bg-red-700"
              >
                {submitting ? 'Submitting...' : 'Confirm Submission'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
