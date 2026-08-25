'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ShieldAlert,
  BookOpen,
  Zap,
  ArrowLeft,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth-context';
import { studentApi, assessmentsApi } from '@medical/api-client';
import { MistakeReviewResponse } from '@medical/shared';
import { AuthModal } from '@/components/auth/auth-modal';

export default function MistakeReviewVaultPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [mistakesData, setMistakesData] = useState<MistakeReviewResponse | null>(null);
  const [repeatedOnly, setRepeatedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [remediating, setRemediating] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    async function loadMistakes() {
      if (!user) {
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const data = await studentApi.getMistakes({
          repeated_only: repeatedOnly,
        });
        setMistakesData(data);
      } catch (err) {
        console.warn('Failed to load mistakes:', err);
      } finally {
        setLoading(false);
      }
    }

    loadMistakes();
  }, [user, repeatedOnly]);

  const handleLaunchRemediation = async () => {
    if (!mistakesData || mistakesData.mistakes.length === 0) return;
    setRemediating(true);
    try {
      const blueprint = mistakesData.remediation_blueprint || {
        topic_ids: ['TOPIC-BREAST-PATH', 'TOPIC-CELL-INJURY'],
      };

      const assessment = await assessmentsApi.createAssessment({
        title: 'Spaced Mistake Remediation Drill',
        type: 'CUSTOM',
        question_count: Math.min(10, mistakesData.total_mistakes),
        duration_seconds: 600,
        blueprint,
      });

      const attempt = await assessmentsApi.startAttempt(assessment.assessment_id, user ? user.id : undefined);
      router.push(`/student/exam/${attempt.attempt_id}`);
    } catch (err) {
      console.error('Failed to launch mistake remediation:', err);
      setRemediating(false);
    }
  };

  return (
    <div className="container px-4 sm:px-8 py-8 max-w-5xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <Link
            href="/student"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-2 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Student Hub
          </Link>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Smart Mistake Vault
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Review your diagnostic errors with peer-reviewed reference citations and launch targeted spaced-repetition drills.
          </p>
        </div>

        {mistakesData && mistakesData.total_mistakes > 0 && (
          <Button
            variant="gradient"
            size="sm"
            disabled={remediating}
            onClick={handleLaunchRemediation}
            className="gap-2 font-bold shadow-lg shadow-rose-500/20 bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-700 hover:to-amber-700"
          >
            <Zap className="h-4 w-4 fill-current" />
            <span>{remediating ? 'Creating Drill...' : 'Remediate Weak Spots'}</span>
          </Button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setRepeatedOnly(false)}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            !repeatedOnly
              ? 'bg-sky-500/20 border-sky-500 text-sky-300'
              : 'bg-white/[0.03] border-white/10 text-slate-400 hover:text-white'
          }`}
        >
          All Mistakes ({mistakesData?.total_mistakes || 0})
        </button>

        <button
          type="button"
          onClick={() => setRepeatedOnly(true)}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            repeatedOnly
              ? 'bg-rose-500/20 border-rose-500 text-rose-300'
              : 'bg-white/[0.03] border-white/10 text-slate-400 hover:text-white'
          }`}
        >
          Repeated Errors (2+ times)
        </button>
      </div>

      {/* Mistakes List */}
      {!user ? (
        <Card className="glass-card p-12 text-center border-white/10 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mx-auto text-sky-400">
            <BookOpen className="h-7 w-7" />
          </div>
          <h3 className="text-xl font-bold text-white">Sign in to Access Your Mistake Vault</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The Smart Mistake Vault tracks your incorrect diagnostic attempts and creates adaptive spaced-repetition drills to remediate weak spots.
          </p>
          <Button variant="gradient" onClick={() => setAuthModalOpen(true)} className="font-bold">
            Sign In / Create Account
          </Button>
          <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
        </Card>
      ) : loading ? (
        <div className="py-16 text-center">
          <div className="animate-spin h-8 w-8 border-3 border-sky-500 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-xs text-slate-400">Querying error history & reference citations...</p>
        </div>
      ) : !mistakesData || mistakesData.mistakes.length === 0 ? (
        <Card className="glass-card p-12 text-center border-white/10">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4 text-emerald-400">
            <CheckCircle2 className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-bold text-white">Zero Outstanding Mistakes!</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
            You have not logged any repeat errors in this category. Continue taking mock exams to build your comprehensive learner model.
          </p>
          <Link href="/student" className="inline-block mt-6">
            <Button variant="gradient" size="sm">
              Explore Mock Exams
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-4">
          {mistakesData.mistakes.map((m, idx) => (
            <Card
              key={idx}
              className="glass-card p-6 border-white/10 hover:border-white/20 transition-all space-y-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive" className="text-[10px]">
                      {m.error_count} Incorrect Attempts
                    </Badge>
                    {m.primary_topic_id && (
                      <span className="text-xs text-slate-400 font-mono">{m.primary_topic_id}</span>
                    )}
                  </div>
                  <h3 className="text-sm sm:text-base font-bold text-white leading-snug pt-1">
                    {m.stem}
                  </h3>
                </div>
              </div>

              {/* Options Breakdown */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {m.options.map((opt) => {
                  const isCorrect = opt.key === m.correct_option;
                  const isUserMistake = opt.key === m.last_selected_answer;
                  return (
                    <div
                      key={opt.key}
                      className={`p-3 rounded-xl border flex items-center gap-2.5 ${
                        isCorrect
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 font-semibold'
                          : isUserMistake
                          ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                          : 'bg-white/[0.02] border-white/5 text-slate-400'
                      }`}
                    >
                      <span className="w-5 h-5 rounded-md bg-white/10 flex items-center justify-center font-bold text-[10px] shrink-0">
                        {opt.key}
                      </span>
                      <span className="truncate">{opt.text}</span>
                      {isCorrect && (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 ml-auto shrink-0" />
                      )}
                      {isUserMistake && !isCorrect && (
                        <XCircle className="h-4 w-4 text-rose-400 ml-auto shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Explanation & Textbook Evidence */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-2">
                <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5 text-sky-400" /> Ground Truth Rationale:
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{m.explanation || 'Standard diagnostic rationale based on peer-reviewed guidelines.'}</p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
