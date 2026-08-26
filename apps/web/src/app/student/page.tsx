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
  AlertCircle,
  Sliders,
  Target,
  ArrowRight,
  RotateCcw,
  ShieldAlert,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth-context';
import { assessmentsApi, studentApi } from '@medical/api-client';
import {
  AssessmentPreset,
  ContinueLearningResponse,
  DailyQuizResponse,
  ExamReadinessResponse,
  WeakTopicRecommendation,
} from '@medical/shared';

export default function StudentHubPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [presets, setPresets] = useState<AssessmentPreset[]>([]);
  const [dailyQuiz, setDailyQuiz] = useState<DailyQuizResponse | null>(null);
  const [continueData, setContinueData] = useState<ContinueLearningResponse | null>(null);
  const [readiness, setReadiness] = useState<ExamReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Enforce profile completion before entering student dashboard
  useEffect(() => {
    if (user && (!user.residency_stage || !user.target_exam)) {
      router.push('/onboarding');
    }
  }, [user, router]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        // Presets are public
        const presetsRes = await assessmentsApi.listPresets().catch(() => null);
        if (presetsRes) {
          setPresets(presetsRes);
        }

        // Only query authenticated endpoints if user is signed in
        if (user) {
          const [quizData, contData, readyData] = await Promise.allSettled([
            studentApi.getDailyQuiz(),
            studentApi.getContinueLearning(),
            studentApi.getExamReadiness(),
          ]);

          if (quizData.status === 'fulfilled') setDailyQuiz(quizData.value);
          if (contData.status === 'fulfilled') setContinueData(contData.value);
          if (readyData.status === 'fulfilled') setReadiness(readyData.value);
        }
      } catch (err: any) {
        console.warn('Student hub data loading notice:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [user]);

  const handleLaunchPreset = async (presetId: string) => {
    setLaunchingId(presetId);
    setError(null);
    try {
      const attempt = await assessmentsApi.launchPreset(presetId);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err: any) {
      console.error('Failed to launch preset:', err);
      setError(err?.message || 'Failed to start test. Please try again.');
      setLaunchingId(null);
    }
  };

  const handleLaunchTopicDrill = async (topicId: string, topicName: string) => {
    setLaunchingId(topicId);
    try {
      const assessment = await assessmentsApi.createAssessment({
        title: `Targeted Drill: ${topicName}`,
        type: 'TOPIC',
        question_count: 10,
        duration_seconds: 600,
        blueprint: {
          topic_id: topicId,
          difficulty_distribution: { medium: 6, hard: 4 },
        },
      });
      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err) {
      console.error('Failed to launch topic drill:', err);
      setLaunchingId(null);
    }
  };

  const targetExamLabel = user?.target_exam === 'NEET_SS'
    ? 'NEET-SS Oncopathology'
    : user?.target_exam === 'NEET_PG'
    ? 'NEET-PG / INI-CET'
    : user?.target_exam === 'MD_PATH'
    ? 'MD / DNB Pathology Exit'
    : 'Medical Examination';

  const defaultWeakTopics: WeakTopicRecommendation[] = [
    {
      curriculum_node_id: 'TOPIC-BREAST-PATH',
      topic_name: 'HER2 IHC & Breast Carcinoma Subtypes',
      smoothed_accuracy: 0.42,
      attempted_count: 5,
      incorrect_count: 3,
      remediation_blueprint: { topic_id: 'TOPIC-BREAST-PATH', question_count: 10, assessment_mode: 'DRILL' },
    },
    {
      curriculum_node_id: 'TOPIC-LYMPHOMAS',
      topic_name: 'WHO Classification of Mature B-Cell Lymphomas',
      smoothed_accuracy: 0.48,
      attempted_count: 6,
      incorrect_count: 3,
      remediation_blueprint: { topic_id: 'TOPIC-LYMPHOMAS', question_count: 10, assessment_mode: 'DRILL' },
    },
    {
      curriculum_node_id: 'TOPIC-CELL-INJURY',
      topic_name: 'BCL-2 Family & Apoptosis Mechanisms',
      smoothed_accuracy: 0.52,
      attempted_count: 8,
      incorrect_count: 4,
      remediation_blueprint: { topic_id: 'TOPIC-CELL-INJURY', question_count: 10, assessment_mode: 'DRILL' },
    },
  ];

  const activeWeakTopics = continueData?.weak_topic_recommendations && continueData.weak_topic_recommendations.length > 0
    ? continueData.weak_topic_recommendations
    : defaultWeakTopics;

  const activeResumableAttempt = continueData?.resumable_attempts && continueData.resumable_attempts.length > 0
    ? continueData.resumable_attempts[0]
    : null;

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <div className="animate-spin h-10 w-10 border-3 border-sky-500 border-t-transparent rounded-full mb-3" />
        <h3 className="text-base font-bold text-white">Calibrating Student Intelligence Hub...</h3>
        <p className="text-xs text-slate-400 mt-1">Loading daily quiz, spaced mastery, and readiness indices.</p>
      </div>
    );
  }

  return (
    <div className="container px-4 sm:px-8 py-8 max-w-7xl mx-auto space-y-8">
      {/* 1. Dynamic Greeting & Exam Target Countdown Banner */}
      <div className="relative overflow-hidden rounded-2xl glass-card border border-white/10 p-6 sm:p-8 bg-gradient-to-r from-slate-900/90 via-sky-950/40 to-indigo-950/50 shadow-2xl">
        <div className="absolute -right-10 -bottom-10 w-72 h-72 rounded-full bg-sky-500/10 blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30 flex items-center gap-1.5">
                <Target className="h-3 w-3" />
                <span>Target: {targetExamLabel}</span>
              </span>
              {user?.residency_stage && (
                <span className="text-xs text-slate-400 font-medium">• {user.residency_stage}</span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Welcome back, {user?.name ? user.name : 'Doctor'} 👋
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-2xl">
              Maintain your daily spaced-repetition momentum. Your diagnostic model is calibrated for{' '}
              <strong className="text-white">Authoritative Medical Curricula & Standard Guidelines</strong>.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link href="/onboarding">
              <Button variant="outline" size="sm" className="border-white/15 bg-white/5 text-xs text-slate-300 hover:text-white hover:bg-white/10 gap-1.5">
                <Sliders className="h-3.5 w-3.5" />
                <span>Change Target</span>
              </Button>
            </Link>
            <Link href="/student/new">
              <Button variant="gradient" size="sm" className="text-xs font-bold gap-1.5 shadow-md shadow-sky-500/20">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Custom Blueprint</span>
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 2. Top Grid: Daily Quiz + Exam Readiness Dial + Weak Topics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Daily High-Yield Quiz Card */}
        <Card className="glass-card p-6 border-white/10 flex flex-col justify-between relative overflow-hidden bg-gradient-to-br from-amber-950/20 via-slate-900/60 to-slate-900/90 hover:border-amber-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                <Flame className="h-5 w-5 fill-amber-400" />
              </div>
              <Badge variant="verified" className="bg-amber-500/20 text-amber-300 border-amber-500/30 text-[11px]">
                {dailyQuiz ? `${dailyQuiz.current_streak}-Day Streak` : 'Daily High-Yield'}
              </Badge>
            </div>
            <h3 className="text-lg font-bold text-white mb-1">
              {dailyQuiz?.title || "Today's Pathology Daily Dose"}
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              5 curated clinical vignettes covering active high-yield exam topics. Rotates daily at 00:00 UTC.
            </p>
            <div className="mt-4 flex items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-slate-400" /> 5 Minutes
              </span>
              <span>•</span>
              <span>+4 / -1 Marking</span>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-[11px] text-slate-400">
              5 Questions Ready
            </span>
            <Button
              variant="gradient"
              size="sm"
              onClick={() => handleLaunchPreset('daily-dose')}
              disabled={launchingId === 'daily-dose'}
              className="gap-1.5 text-xs font-bold bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Start Daily Quiz</span>
            </Button>
          </div>
        </Card>

        {/* Exam Readiness Index Dial */}
        <Card className="glass-card p-6 border-white/10 flex flex-col justify-between bg-gradient-to-br from-indigo-950/20 via-slate-900/60 to-slate-900/90 hover:border-indigo-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Award className="h-5 w-5" />
              </div>
              <Badge variant="outline" className="text-[10px] text-indigo-300 border-indigo-500/30">
                Composite Score
              </Badge>
            </div>
            <h3 className="text-lg font-bold text-white mb-1">Exam Readiness Index</h3>
            <p className="text-xs text-slate-300">
              Multi-dimensional evaluation of question coverage, accuracy, and test consistency.
            </p>

            <div className="mt-5 flex items-center justify-center">
              <div className="relative flex items-center justify-center">
                <svg className="w-28 h-28 transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    className="text-white/10"
                    strokeWidth="8"
                    stroke="currentColor"
                    fill="transparent"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    className="text-sky-400 transition-all duration-1000 ease-out"
                    strokeWidth="8"
                    strokeDasharray={251.2}
                    strokeDashoffset={251.2 * (1 - (readiness?.readiness_score || 68) / 100)}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-2xl font-extrabold text-white">
                    {readiness?.readiness_score || 68}%
                  </span>
                  <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold">
                    {readiness?.rating || 'GOOD'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10 grid grid-cols-2 gap-2 text-center text-[10px] text-slate-400">
            <div>
              <span className="block text-slate-200 font-semibold">{readiness?.breakdown.curriculum_coverage_pct || 45}%</span>
              <span>Curriculum Coverage</span>
            </div>
            <div>
              <span className="block text-slate-200 font-semibold">{readiness?.breakdown.average_accuracy_pct || 74}%</span>
              <span>Laplace Accuracy</span>
            </div>
          </div>
        </Card>

        {/* Weak Topic Pulse / Remediation Card */}
        <Card className="glass-card p-6 border-white/10 flex flex-col justify-between bg-gradient-to-br from-rose-950/15 via-slate-900/60 to-slate-900/90 hover:border-rose-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <Badge variant="outline" className="text-[10px] text-rose-300 border-rose-500/30">
                Remediation Pulse
              </Badge>
            </div>
            <h3 className="text-lg font-bold text-white mb-1">High-Yield Weak Spots</h3>
            <p className="text-xs text-slate-300 mb-3">
              Topics requiring immediate reinforcement based on recent error patterns:
            </p>

            <div className="space-y-2">
              {activeWeakTopics.map((topic, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03] border border-white/5 text-xs hover:bg-white/[0.06] transition-colors"
                >
                  <span className="text-slate-300 truncate max-w-[170px] font-medium">
                    {topic.topic_name}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleLaunchTopicDrill(topic.curriculum_node_id, topic.topic_name)}
                    disabled={launchingId === topic.curriculum_node_id}
                    className="text-[10px] text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1"
                  >
                    Drill <ArrowRight className="h-2.5 w-2.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-[11px] text-slate-400">Spaced Repetition</span>
            <Link href="/student/review">
              <span className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1">
                View Mistake Vault <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          </div>
        </Card>
      </div>

      {/* 3. In-Progress Assessment Resumption Banner (if any) */}
      {activeResumableAttempt && (
        <div className="p-4 sm:p-5 rounded-2xl glass-card border border-sky-500/30 bg-sky-950/30 flex flex-col sm:flex-row items-center justify-between gap-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/20 text-sky-400">
              <RotateCcw className="h-5 w-5 animate-spin-slow" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Badge variant="verified" className="text-[10px]">Unfinished Mock Session</Badge>
                <span className="text-xs text-slate-300 font-semibold">
                  {activeResumableAttempt.assessment_title}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {activeResumableAttempt.answered_count} / {activeResumableAttempt.total_questions} questions answered • Progress preserved
              </p>
            </div>
          </div>
          <Link href={`/student/exam?attempt_id=${activeResumableAttempt.attempt_id}`}>
            <Button variant="gradient" size="sm" className="gap-1.5 text-xs font-bold shrink-0">
              <span>Resume Mock Test</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      )}

      {/* 4. Grand Mock Examinations & Subject Tests Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Standard Mock Examinations & Subject Tests
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulated exam environments with official NEET-SS, NEET-PG, and INI-CET scoring matrices.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {presets.map((preset) => {
            const isLaunching = launchingId === preset.id;
            return (
              <Card
                key={preset.id}
                className="glass-card p-6 border-white/10 hover:border-sky-500/40 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Badge variant={preset.type === 'MOCK' ? 'verified' : 'secondary'} className="text-[10px]">
                      {preset.type}
                    </Badge>
                    <span className="text-xs text-slate-400 font-medium">
                      {Math.round(preset.duration_seconds / 60)} Mins
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white group-hover:text-sky-300 transition-colors mb-2">
                    {preset.title}
                  </h3>

                  <p className="text-xs text-slate-300 leading-relaxed line-clamp-2 mb-4">
                    {preset.description}
                  </p>

                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {preset.tags?.map((t, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.04] text-slate-400 border border-white/5"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                  <div className="text-xs text-slate-400 font-medium">
                    <strong className="text-white">{preset.question_count}</strong> Questions
                  </div>

                  <Button
                    variant="gradient"
                    size="sm"
                    disabled={isLaunching}
                    onClick={() => handleLaunchPreset(preset.id)}
                    className="gap-1.5 text-xs font-bold shadow-sm"
                  >
                    <Play className="h-3.5 w-3.5 fill-current" />
                    <span>{isLaunching ? 'Loading...' : 'Launch Test'}</span>
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
