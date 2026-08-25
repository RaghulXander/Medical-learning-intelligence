'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Clock,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Send,
  AlertTriangle,
  RotateCcw,
  EyeOff,
  Type,
  Grid,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { assessmentsApi } from '@medical/api-client';
import { SanitizedQuestion, HeartbeatQuestionResponse, AttemptSectionInfo } from '@medical/shared';
import { formatTime, cn } from '@/lib/utils';

export default function ExamRunnerPage() {
  const params = useParams();
  const router = useRouter();
  const attemptId = params?.attemptId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [questions, setQuestions] = useState<SanitizedQuestion[]>([]);
  const [sections, setSections] = useState<AttemptSectionInfo[]>([]);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(3000);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // User state map: question_id -> { selected_answer, marked_for_review, time_spent_seconds, struck_options }
  const [userResponses, setUserResponses] = useState<
    Record<
      string,
      {
        selected_answer: string | null;
        marked_for_review: boolean;
        time_spent_seconds: number;
        visited: boolean;
        struck_options: string[];
      }
    >
  >({});

  // Aspirant power tools: Font zoom (1: Normal, 2: Medium, 3: Large)
  const [fontSizeLevel, setFontSizeLevel] = useState<1 | 2 | 3>(1);
  const [strikeModeActive, setStrikeModeActive] = useState(false);

  // Mobile Question Palette Bottom Sheet
  const [mobilePaletteOpen, setMobilePaletteOpen] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  // Load Attempt State
  useEffect(() => {
    async function loadAttempt() {
      try {
        setLoading(true);
        const data = await assessmentsApi.getAttemptState(attemptId);
        const qList = data.questions || [];
        setQuestions(qList);
        setSections(data.sections || []);
        if (data.sections && data.sections.length > 0 && data.sections[0]) {
          setActiveSectionId(data.sections[0].id);
        }
        setDurationSeconds(data.duration_seconds || 3000);
        setElapsedSeconds(data.time_spent_seconds || 0);

        // Prepopulate responses with localStorage merge if available
        const storageKey = `docedge_exam_${attemptId}`;
        let localSaved: Record<string, any> = {};
        try {
          const raw = localStorage.getItem(storageKey);
          if (raw) localSaved = JSON.parse(raw);
        } catch {
          // ignore localStorage error
        }

        const initMap: Record<
          string,
          {
            selected_answer: string | null;
            marked_for_review: boolean;
            time_spent_seconds: number;
            visited: boolean;
            struck_options: string[];
          }
        > = {};

        qList.forEach((q: SanitizedQuestion, idx: number) => {
          const localItem = localSaved[q.question_id];
          initMap[q.question_id] = {
            selected_answer: localItem?.selected_answer ?? q.selected_answer ?? null,
            marked_for_review: localItem?.marked_for_review ?? q.marked_for_review ?? false,
            time_spent_seconds: localItem?.time_spent_seconds ?? 0,
            visited: idx === 0 || localItem?.visited || !!q.selected_answer,
            struck_options: localItem?.struck_options || [],
          };
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

  // Sync to localStorage
  useEffect(() => {
    if (Object.keys(userResponses).length > 0 && attemptId) {
      try {
        localStorage.setItem(`docedge_exam_${attemptId}`, JSON.stringify(userResponses));
      } catch {
        // ignore
      }
    }
  }, [userResponses, attemptId]);

  // Mark current question as visited
  useEffect(() => {
    const q = questions[currentIndex];
    if (q && userResponses[q.question_id] && !userResponses[q.question_id]?.visited) {
      setUserResponses((prev) => {
        const item = prev[q.question_id];
        if (!item) return prev;
        return {
          ...prev,
          [q.question_id]: {
            ...item,
            visited: true,
          },
        };
      });
    }
  }, [currentIndex, questions, userResponses]);

  // Countdown timer
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

  // Periodic heartbeat sync (15s)
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

  // Option list normalized array helper
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

  const handleSelectOption = (key: string) => {
    if (!currentQ) return;
    setUserResponses((prev) => {
      const item = prev[currentQ.question_id];
      if (!item) return prev;
      return {
        ...prev,
        [currentQ.question_id]: {
          ...item,
          selected_answer: key,
          visited: true,
        },
      };
    });
  };

  const handleToggleStrikeOption = (key: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentQ) return;
    setUserResponses((prev) => {
      const item = prev[currentQ.question_id];
      if (!item) return prev;
      const struck = item.struck_options || [];
      const nextStruck = struck.includes(key) ? struck.filter((k) => k !== key) : [...struck, key];
      return {
        ...prev,
        [currentQ.question_id]: {
          ...item,
          struck_options: nextStruck,
        },
      };
    });
  };

  const handleToggleMarkReview = () => {
    if (!currentQ) return;
    setUserResponses((prev) => {
      const item = prev[currentQ.question_id];
      if (!item) return prev;
      return {
        ...prev,
        [currentQ.question_id]: {
          ...item,
          marked_for_review: !item.marked_for_review,
          visited: true,
        },
      };
    });
  };

  const handleClearAnswer = () => {
    if (!currentQ) return;
    setUserResponses((prev) => {
      const item = prev[currentQ.question_id];
      if (!item) return prev;
      return {
        ...prev,
        [currentQ.question_id]: {
          ...item,
          selected_answer: null,
        },
      };
    });
  };

  const handleSubmitExam = useCallback(async () => {
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

      // Clear local storage on submission
      try {
        localStorage.removeItem(`docedge_exam_${attemptId}`);
      } catch {
        // ignore
      }

      router.push(`/student/results/${attemptId}`);
    } catch (err: any) {
      console.error('Failed to submit exam:', err);
      alert('Submission error: ' + (err?.message || 'Please retry.'));
      setSubmitting(false);
    }
  }, [attemptId, elapsedSeconds, userResponses, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="animate-spin h-12 w-12 border-4 border-sky-500 border-t-transparent rounded-full mb-4" />
        <h2 className="text-xl font-black text-white tracking-tight">Initializing Prometric Exam Shell...</h2>
        <p className="text-xs text-slate-400 mt-1.5 max-w-sm">
          Locking questions, configuring +4 / -1 NEET marking parameters, and starting timer...
        </p>
      </div>
    );
  }

  if (error || !currentQ) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="h-14 w-14 text-amber-400 mb-4" />
        <h2 className="text-xl font-bold text-white">Exam Session Unavailable</h2>
        <p className="text-sm text-slate-400 mt-2 max-w-md">{error || 'No questions found for this session.'}</p>
        <Button className="mt-6 rounded-2xl" onClick={() => router.push('/student')}>
          Return to Student Hub
        </Button>
      </div>
    );
  }

  const remainingSeconds = Math.max(0, durationSeconds - elapsedSeconds);
  const isTimeCritical = remainingSeconds < 300; // < 5 mins

  // Prometric 5-state calculations
  const totalCount = questions.length;
  const answeredCount = Object.values(userResponses).filter((r) => r.selected_answer !== null).length;
  const markedOnlyCount = Object.values(userResponses).filter(
    (r) => r.marked_for_review && r.selected_answer === null
  ).length;
  const answeredAndMarkedCount = Object.values(userResponses).filter(
    (r) => r.marked_for_review && r.selected_answer !== null
  ).length;
  const visitedNotAnsweredCount = Object.values(userResponses).filter(
    (r) => r.visited && r.selected_answer === null && !r.marked_for_review
  ).length;
  const unvisitedCount = Math.max(
    0,
    totalCount - (answeredCount + markedOnlyCount + visitedNotAnsweredCount)
  );

  const getPrometricColor = (_idx: number, qid: string) => {
    const resp = userResponses[qid];
    if (!resp || !resp.visited) {
      return 'bg-slate-900/60 border-slate-700 text-slate-400 hover:bg-slate-800'; // ⚪ Not Visited
    }
    if (resp.selected_answer && resp.marked_for_review) {
      return 'bg-purple-500/30 border-purple-400 text-purple-100 font-bold ring-2 ring-emerald-400'; // 🟣🟢 Answered & Marked
    }
    if (resp.selected_answer) {
      return 'bg-emerald-500 border-emerald-400 text-white font-bold shadow-md shadow-emerald-500/20'; // 🟢 Answered
    }
    if (resp.marked_for_review) {
      return 'bg-purple-500/25 border-purple-500 text-purple-200 font-bold'; // 🟣 Marked for Review
    }
    return 'bg-rose-500/20 border-rose-500 text-rose-300 font-bold'; // 🔴 Visited & Not Answered
  };

  const optionsList = getOptionsList(currentQ.options);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 select-none pb-20 lg:pb-0">
      {/* Top Distraction-Free Bar */}
      <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-slate-950/95 backdrop-blur-xl px-4 py-3">
        <div className="container max-w-7xl mx-auto flex items-center justify-between gap-2">
          {/* Question Index & Section Badges */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <span className="font-extrabold text-white text-base sm:text-lg">
              Q{currentIndex + 1}
              <span className="text-xs font-normal text-slate-400 ml-1">of {totalCount}</span>
            </span>

            {/* Font Zoom Tool */}
            <div className="flex items-center p-0.5 rounded-xl bg-white/[0.04] border border-white/[0.08]">
              <button
                onClick={() => setFontSizeLevel((l) => (l === 1 ? 2 : l === 2 ? 3 : 1))}
                className="px-2.5 py-1 rounded-lg text-xs font-bold text-slate-300 hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
                title="Toggle Font Size"
              >
                <Type className="h-3.5 w-3.5" />
                <span>{fontSizeLevel === 1 ? 'A' : fontSizeLevel === 2 ? 'A+' : 'A++'}</span>
              </button>
            </div>

            {/* Strike Mode Toggle */}
            <button
              onClick={() => setStrikeModeActive((s) => !s)}
              className={cn(
                'hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold transition-all border cursor-pointer',
                strikeModeActive
                  ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-sm'
                  : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white'
              )}
            >
              <EyeOff className="h-3.5 w-3.5" />
              <span>Strike Mode</span>
            </button>
          </div>

          {/* Center Sticky Timer */}
          <div
            className={cn(
              'flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-2xl font-mono text-sm sm:text-base font-black border transition-all shadow-md',
              isTimeCritical
                ? 'bg-red-500/20 border-red-500 text-red-300 animate-pulse'
                : 'bg-white/[0.05] border-white/[0.1] text-white'
            )}
          >
            <Clock className={cn('h-4 w-4', isTimeCritical ? 'text-red-400' : 'text-sky-400')} />
            <span>{formatTime(remainingSeconds)}</span>
          </div>

          {/* Palette (Mobile) & End Test Buttons */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMobilePaletteOpen(true)}
              className="lg:hidden h-9 px-3 rounded-xl border-white/15 text-slate-300 gap-1"
            >
              <Grid className="h-4 w-4 text-sky-400" />
              <span className="text-xs">Grid</span>
            </Button>

            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowSubmitModal(true)}
              className="h-9 px-3 sm:px-4 rounded-xl bg-red-600 hover:bg-red-700 font-bold text-xs gap-1.5 shadow-md shadow-red-600/20 active:scale-95 transition-transform"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Submit</span>
            </Button>
          </div>
        </div>

        {/* Section Tabs (if multi-section) */}
        {sections.length > 1 && (
          <div className="container max-w-7xl mx-auto flex items-center gap-2 mt-2 pt-2 border-t border-white/[0.06] overflow-x-auto pb-1">
            {sections.map((sec) => (
              <button
                key={sec.id}
                onClick={() => {
                  setActiveSectionId(sec.id);
                  // Jump to first question in section
                  const firstIdx = questions.findIndex((q) => q.section_id === sec.id);
                  if (firstIdx !== -1) setCurrentIndex(firstIdx);
                }}
                className={cn(
                  'px-3 py-1 rounded-xl text-xs font-bold transition-all whitespace-nowrap border cursor-pointer',
                  activeSectionId === sec.id
                    ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                    : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:text-white'
                )}
              >
                {sec.name} ({sec.question_count} Qs)
              </button>
            ))}
          </div>
        )}
      </header>

      {/* Main Runner Body */}
      <div className="container max-w-7xl mx-auto px-4 py-4 sm:py-6 flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left 3 Columns: Active MCQ Canvas */}
        <div className="lg:col-span-3 flex flex-col justify-between">
          <Card className="glass-card p-5 sm:p-8 rounded-3xl flex-1 flex flex-col justify-between mb-4 sm:mb-6 shadow-xl">
            <div>
              {/* Question Header Meta */}
              <div className="flex items-center justify-between gap-3 pb-3 mb-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-[11px] bg-white/[0.06] text-slate-300">
                    Single Best Answer (+4, -1)
                  </Badge>
                  {currentQ.topic_name && (
                    <Badge variant="outline" className="text-[11px] text-sky-400 border-sky-500/30">
                      {currentQ.topic_name}
                    </Badge>
                  )}
                </div>

                <span className="text-xs font-mono text-slate-500">
                  ID: {currentQ.question_id.slice(0, 8)}
                </span>
              </div>

              {/* Question Stem */}
              <div
                className={cn(
                  'font-medium text-slate-100 leading-relaxed whitespace-pre-wrap mb-6 transition-all',
                  fontSizeLevel === 1 && 'text-base sm:text-lg',
                  fontSizeLevel === 2 && 'text-lg sm:text-xl leading-loose',
                  fontSizeLevel === 3 && 'text-xl sm:text-2xl leading-loose font-semibold'
                )}
              >
                {currentQ.stem}
              </div>

              {/* Options List */}
              <div className="space-y-3">
                {optionsList.map((opt) => {
                  const isSelected = currentResp?.selected_answer === opt.key;
                  const isStruck = currentResp?.struck_options?.includes(opt.key);

                  return (
                    <div
                      key={opt.key}
                      onClick={() => handleSelectOption(opt.key)}
                      className={cn(
                        'w-full p-4 sm:p-4.5 rounded-2xl border text-left flex items-start justify-between gap-3.5 transition-all cursor-pointer select-none active:scale-[0.99]',
                        isSelected
                          ? 'bg-sky-500/20 border-sky-400 text-white shadow-lg shadow-sky-500/10 ring-1 ring-sky-400'
                          : 'bg-white/[0.03] border-white/[0.08] text-slate-200 hover:bg-white/[0.06] hover:border-white/20',
                        isStruck && 'opacity-40 line-through bg-red-950/20 border-red-500/20'
                      )}
                    >
                      <div className="flex items-start gap-3.5 flex-1">
                        {/* Option Key Badge */}
                        <div
                          className={cn(
                            'h-7 w-7 sm:h-8 sm:w-8 rounded-xl flex items-center justify-center font-black text-xs sm:text-sm flex-shrink-0 transition-colors',
                            isSelected
                              ? 'bg-sky-500 text-white shadow-md shadow-sky-500/30'
                              : 'bg-white/10 text-slate-300'
                          )}
                        >
                          {opt.key}
                        </div>

                        {/* Option Text */}
                        <div
                          className={cn(
                            'pt-0.5 sm:pt-1 transition-all',
                            fontSizeLevel === 1 && 'text-sm sm:text-base font-normal',
                            fontSizeLevel === 2 && 'text-base sm:text-lg font-normal',
                            fontSizeLevel === 3 && 'text-lg sm:text-xl font-medium'
                          )}
                        >
                          {opt.text}
                        </div>
                      </div>

                      {/* Strikethrough Distractor Elimination Button */}
                      <button
                        type="button"
                        onClick={(e) => handleToggleStrikeOption(opt.key, e)}
                        className={cn(
                          'p-1.5 rounded-lg border text-xs transition-colors cursor-pointer',
                          isStruck
                            ? 'bg-red-500/30 border-red-500/50 text-red-300'
                            : 'bg-white/[0.04] border-white/[0.08] text-slate-500 hover:text-slate-200'
                        )}
                        title="Eliminate / Cross out option"
                      >
                        <EyeOff className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Desktop Question Action Footer */}
            <div className="hidden lg:flex items-center justify-between gap-3 pt-6 mt-8 border-t border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleToggleMarkReview}
                  className={cn(
                    'rounded-xl text-xs gap-1.5 transition-colors',
                    currentResp?.marked_for_review
                      ? 'border-purple-500 bg-purple-500/25 text-purple-300 font-bold'
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
                    className="rounded-xl text-xs text-slate-400 hover:text-white gap-1"
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
                  className="rounded-xl gap-1 border-white/10"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Previous</span>
                </Button>

                <Button
                  variant="gradient"
                  size="sm"
                  disabled={currentIndex === totalCount - 1}
                  onClick={() => setCurrentIndex((prev) => Math.min(totalCount - 1, prev + 1))}
                  className="rounded-xl gap-1 px-6 font-bold"
                >
                  <span>Next</span>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Right 1 Column: Prometric 5-State Question Palette (Desktop) */}
        <div className="hidden lg:block lg:col-span-1">
          <Card className="glass-card p-5 h-full flex flex-col justify-between rounded-3xl">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-white text-sm">Question Palette</h3>
                <span className="text-[10px] text-slate-400 font-mono">Prometric Grid</span>
              </div>

              {/* 5-State Legend */}
              <div className="space-y-1.5 text-[11px] text-slate-300 mb-4 pb-4 border-b border-white/[0.08]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-md bg-emerald-500" />
                    <span>Answered</span>
                  </div>
                  <span className="font-bold text-white">{answeredCount}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-md bg-rose-500/40 border border-rose-500" />
                    <span>Not Answered</span>
                  </div>
                  <span className="font-bold text-white">{visitedNotAnsweredCount}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-md bg-purple-500/40 border border-purple-400" />
                    <span>Marked for Review</span>
                  </div>
                  <span className="font-bold text-white">{markedOnlyCount}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-md bg-purple-500/40 ring-1 ring-emerald-400" />
                    <span>Answered & Marked</span>
                  </div>
                  <span className="font-bold text-white">{answeredAndMarkedCount}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-md bg-slate-900 border border-slate-700" />
                    <span>Not Visited</span>
                  </div>
                  <span className="font-bold text-white">{unvisitedCount}</span>
                </div>
              </div>

              {/* Grid Matrix */}
              <div className="grid grid-cols-5 gap-2 max-h-[380px] overflow-y-auto pr-1">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentIndex;
                  const colorClass = getPrometricColor(idx, q.question_id);

                  return (
                    <button
                      key={q.question_id}
                      onClick={() => setCurrentIndex(idx)}
                      className={cn(
                        'h-9 rounded-xl border text-xs font-bold flex items-center justify-center transition-all cursor-pointer active:scale-95',
                        colorClass,
                        isCurrent && 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-105 shadow-lg'
                      )}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quick Submit CTA */}
            <div className="pt-4 mt-4 border-t border-white/[0.08]">
              <Button
                variant="gradient"
                className="w-full rounded-2xl font-bold py-5 shadow-lg shadow-sky-500/20 active:scale-95 transition-transform"
                onClick={() => setShowSubmitModal(true)}
              >
                Submit Exam
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Mobile Fixed Bottom Action Bar */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-white/[0.1] bg-slate-950/95 backdrop-blur-xl p-3">
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            className="flex-1 rounded-xl h-11 border-white/15"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            <span>Prev</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleToggleMarkReview}
            className={cn(
              'px-3 rounded-xl h-11 border-white/15',
              currentResp?.marked_for_review && 'bg-purple-500/30 border-purple-400 text-purple-200'
            )}
          >
            <Bookmark className="h-4 w-4" />
          </Button>

          <Button
            variant="gradient"
            size="sm"
            disabled={currentIndex === totalCount - 1}
            onClick={() => setCurrentIndex((prev) => Math.min(totalCount - 1, prev + 1))}
            className="flex-1 rounded-xl h-11 font-bold"
          >
            <span>Next</span>
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>

      {/* Mobile Slide-Up Question Palette Drawer */}
      {mobilePaletteOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border-t border-white/15 p-5 rounded-t-3xl max-h-[80vh] flex flex-col justify-between animate-in slide-in-from-bottom">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Grid className="h-5 w-5 text-sky-400" />
                  <h3 className="font-bold text-white text-base">Question Grid Palette</h3>
                </div>
                <button
                  onClick={() => setMobilePaletteOpen(false)}
                  className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center text-slate-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Palette Grid */}
              <div className="grid grid-cols-5 gap-2 max-h-60 overflow-y-auto pr-1 pb-4">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentIndex;
                  const colorClass = getPrometricColor(idx, q.question_id);

                  return (
                    <button
                      key={q.question_id}
                      onClick={() => {
                        setCurrentIndex(idx);
                        setMobilePaletteOpen(false);
                      }}
                      className={cn(
                        'h-10 rounded-xl border text-xs font-bold flex items-center justify-center transition-all cursor-pointer',
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

            <div className="pt-4 border-t border-white/[0.08]">
              <Button
                variant="destructive"
                className="w-full py-5 rounded-2xl font-bold bg-red-600 hover:bg-red-700"
                onClick={() => {
                  setMobilePaletteOpen(false);
                  setShowSubmitModal(true);
                }}
              >
                End & Submit Exam
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Submit Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in">
          <div className="glass-panel max-w-md w-full p-6 sm:p-8 rounded-3xl border border-white/20 shadow-2xl">
            <h3 className="text-xl font-extrabold text-white mb-2">Submit Assessment?</h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-6">
              You have answered <strong className="text-emerald-400 font-bold">{answeredCount}</strong> of{' '}
              <strong className="text-white">{totalCount}</strong> questions ({totalCount - answeredCount} unanswered). Once submitted, your score and full topic mastery breakdown will be generated immediately.
            </p>

            <div className="flex items-center justify-end gap-3">
              <Button
                variant="outline"
                className="rounded-xl border-white/15"
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
              >
                Resume Test
              </Button>
              <Button
                variant="destructive"
                className="rounded-xl bg-red-600 hover:bg-red-700 font-bold"
                onClick={handleSubmitExam}
                disabled={submitting}
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
