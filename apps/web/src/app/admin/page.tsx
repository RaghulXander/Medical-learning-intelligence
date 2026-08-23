'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  Eye,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  BookOpen,
  LayoutGrid,
  Columns,
  ImageOff,
  ArrowRight,
  FileCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { questionsApi, TopicCountItem } from '@medical/api-client';
import { Question, QuestionStatus } from '@medical/shared';
import { cn } from '@/lib/utils';

export default function AdminQuestionBankPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [topics, setTopics] = useState<TopicCountItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  // View Mode: 'SPLIT' (Review & Next mode) vs 'TABLE'
  const [viewMode, setViewMode] = useState<'SPLIT' | 'TABLE'>('SPLIT');
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filters & Pagination State
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const [selectedModalQuestion, setSelectedModalQuestion] = useState<Question | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
      setSelectedIndex(0);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Load available topics on mount
  useEffect(() => {
    async function loadTopics() {
      try {
        const data = await questionsApi.listTopics();
        setTopics(data);
      } catch (err) {
        console.warn('Could not load topics list:', err);
      }
    }
    loadTopics();
  }, []);

  // Fetch questions on filter or page change
  const fetchQuestions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await questionsApi.listQuestions({
        search: debouncedSearch || undefined,
        topic: selectedTopic !== 'ALL' ? selectedTopic : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        difficulty: difficultyFilter !== 'ALL' ? difficultyFilter : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      setQuestions(res.items || []);
      setTotalCount(res.total || 0);
      setSelectedIndex(0);
    } catch (err: any) {
      console.error('Failed to fetch questions:', err);
      setError(err?.message || 'Failed to connect to backend database.');
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, selectedTopic, statusFilter, difficultyFilter, page]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const handleUpdateStatus = async (
    questionId: string,
    newStatus: QuestionStatus,
    advanceNext: boolean = false
  ) => {
    try {
      setUpdatingId(questionId);
      await questionsApi.updateStatus(questionId, newStatus);

      // Update local state
      setQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, status: newStatus } : q))
      );
      if (selectedModalQuestion?.id === questionId) {
        setSelectedModalQuestion((prev) => (prev ? { ...prev, status: newStatus } : null));
      }

      // If in review mode, advance to next question smoothly
      if (advanceNext && selectedIndex < questions.length - 1) {
        setSelectedIndex((idx) => idx + 1);
      }
    } catch (err: any) {
      console.error('Failed to update status:', err);
      alert('Status update error: ' + (err?.message || 'Please retry.'));
    } finally {
      setUpdatingId(null);
    }
  };

  const currentQ = questions[selectedIndex] || null;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  // Helper to detect if question mentions an image in stem
  const isImageReferencedInText = (stemText: string) => {
    const keywords = ['image', 'picture', 'photograph', 'shown below', 'given below', 'arrow mark', 'slide shown'];
    const lower = stemText.toLowerCase();
    return keywords.some((kw) => lower.includes(kw));
  };

  return (
    <div className="container max-w-7xl px-4 sm:px-8 py-8">
      {/* Admin Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/[0.08] mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
              Admin & Editorial Curation Desk
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Question Bank Review & Inspector
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Inspect questions with full options, ground truth explanations, and authoritative citations.
          </p>
        </div>

        {/* View Mode Toggle & Total Counter */}
        <div className="flex items-center gap-3">
          <div className="flex items-center p-1 rounded-xl bg-white/[0.04] border border-white/[0.08]">
            <button
              onClick={() => setViewMode('SPLIT')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                viewMode === 'SPLIT'
                  ? 'bg-sky-500 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              <Columns className="h-3.5 w-3.5" />
              <span>Inspector Mode</span>
            </button>
            <button
              onClick={() => setViewMode('TABLE')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                viewMode === 'TABLE'
                  ? 'bg-sky-500 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              <span>Table View</span>
            </button>
          </div>

          <div className="px-4 py-2 rounded-xl glass-card text-center border-sky-500/30">
            <div className="text-xs text-slate-400 font-medium">Matching Bank</div>
            <div className="text-lg font-bold text-white">
              {loading ? '...' : totalCount.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">MCQs</span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => fetchQuestions()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Retry
          </Button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6 p-4 rounded-2xl glass-card">
        {/* Search */}
        <div className="relative md:col-span-2">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search stem, keywords, or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.1] text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        {/* Topic Selector */}
        <div>
          <select
            value={selectedTopic}
            onChange={(e) => {
              setSelectedTopic(e.target.value);
              setPage(1);
            }}
            className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-white/[0.1] text-sm text-white focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
          >
            <option value="ALL">All Pathology Topics ({topics.reduce((acc, t) => acc + t.count, 0)})</option>
            {topics.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.count})
              </option>
            ))}
          </select>
        </div>

        {/* Difficulty Selector */}
        <div>
          <select
            value={difficultyFilter}
            onChange={(e) => {
              setDifficultyFilter(e.target.value);
              setPage(1);
            }}
            className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-white/[0.1] text-sm text-white focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
          >
            <option value="ALL">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
      </div>

      {/* Status Filter Tabs & Pagination Header */}
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div className="flex flex-wrap gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs">
          {(['ALL', 'IMPORTED', 'HUMAN_REVIEW', 'APPROVED', 'REJECTED'] as const).map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className={cn(
                'px-3.5 py-1.5 rounded-lg font-medium transition-colors cursor-pointer',
                statusFilter === st
                  ? 'bg-sky-500 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>
          <div className="flex items-center gap-1 ml-2">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 border-white/10"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 border-white/10"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* MODE 1: SPLIT-PANE INSPECTOR MODE (High-Throughput Review) */}
      {/* ------------------------------------------------------------------- */}
      {viewMode === 'SPLIT' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
          {/* Left 4 Columns: Compact Question List */}
          <div className="lg:col-span-5 flex flex-col justify-between rounded-2xl border border-white/[0.08] bg-slate-900/40 p-4 max-h-[750px] overflow-y-auto">
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-400 px-2 pb-2 border-b border-white/[0.06] flex items-center justify-between">
                <span>Questions in Batch</span>
                <span>{questions.length} Items</span>
              </div>

              {loading ? (
                <div className="py-20 text-center text-slate-400">
                  <div className="animate-spin h-7 w-7 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-2" />
                  <span className="text-xs">Loading batch...</span>
                </div>
              ) : questions.length === 0 ? (
                <div className="py-20 text-center text-slate-400 text-xs">
                  No questions match current filter.
                </div>
              ) : (
                questions.map((q, idx) => {
                  const isSelected = idx === selectedIndex;
                  const hasImageRef = isImageReferencedInText(q.stem);

                  return (
                    <div
                      key={q.id}
                      onClick={() => setSelectedIndex(idx)}
                      className={cn(
                        'p-3.5 rounded-xl border text-left cursor-pointer transition-all',
                        isSelected
                          ? 'bg-sky-500/15 border-sky-400/80 shadow-md shadow-sky-500/10 ring-1 ring-sky-400/50'
                          : 'bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.05] hover:border-white/15'
                      )}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[11px] font-mono text-slate-400">
                          #{(page - 1) * pageSize + idx + 1}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {hasImageRef && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                              <ImageOff className="h-2.5 w-2.5" />
                              <span>Image Ref</span>
                            </span>
                          )}
                          <Badge
                            variant={
                              q.status === 'APPROVED'
                                ? 'success'
                                : q.status === 'HUMAN_REVIEW'
                                ? 'warning'
                                : q.status === 'REJECTED'
                                ? 'destructive'
                                : 'outline'
                            }
                            className="text-[10px] px-1.5 py-0"
                          >
                            {q.status}
                          </Badge>
                        </div>
                      </div>

                      <div className="text-xs font-medium text-white line-clamp-2 leading-relaxed mb-1.5">
                        {q.stem}
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-white/[0.04]">
                        <span className="truncate max-w-[180px]">{q.topic_name_normalized}</span>
                        <span className="font-semibold text-emerald-400">Ans: {q.correct_option || '?'}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right 7 Columns: Active Question Inspection Workbench */}
          <div className="lg:col-span-7">
            {currentQ ? (
              <Card className="glass-card p-6 sm:p-8 h-full flex flex-col justify-between">
                <div className="space-y-6">
                  {/* Top Bar with Navigation & Meta */}
                  <div className="flex items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className="text-xs">
                        {currentQ.topic_name_normalized}
                      </Badge>
                      <Badge
                        variant={
                          currentQ.status === 'APPROVED'
                            ? 'success'
                            : currentQ.status === 'HUMAN_REVIEW'
                            ? 'warning'
                            : currentQ.status === 'REJECTED'
                            ? 'destructive'
                            : 'outline'
                        }
                        className="text-xs font-semibold"
                      >
                        {currentQ.status}
                      </Badge>
                      <span className="text-xs text-slate-500 font-mono">{currentQ.external_source_id}</span>
                    </div>

                    {/* Prev / Next Buttons */}
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={selectedIndex === 0}
                        onClick={() => setSelectedIndex((idx) => Math.max(0, idx - 1))}
                        className="h-8 text-xs border-white/10"
                      >
                        <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                        <span>Prev</span>
                      </Button>
                      <span className="text-xs font-mono text-slate-400 px-1">
                        {selectedIndex + 1} / {questions.length}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={selectedIndex === questions.length - 1}
                        onClick={() => setSelectedIndex((idx) => Math.min(questions.length - 1, idx + 1))}
                        className="h-8 text-xs border-white/10"
                      >
                        <span>Next</span>
                        <ChevronRight className="h-3.5 w-3.5 ml-1" />
                      </Button>
                    </div>
                  </div>

                  {/* Missing Image Alert Banner if referenced */}
                  {isImageReferencedInText(currentQ.stem) && (
                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2.5">
                      <ImageOff className="h-4 w-4 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Image Attachment Notice:</span> This question text mentions an image/picture (&quot;shown below&quot;) from the raw past paper scrape, but the raw MedMCQA dataset did not include image binaries. If the picture is mandatory to answer, flag or reject the question.
                      </div>
                    </div>
                  )}

                  {/* Question Stem */}
                  <div>
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Question Stem
                    </label>
                    <div className="text-base sm:text-lg font-medium text-white leading-relaxed whitespace-pre-wrap bg-white/[0.02] p-4 rounded-xl border border-white/[0.06]">
                      {currentQ.stem}
                    </div>
                  </div>

                  {/* Options List */}
                  <div>
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Options & Ground Truth
                    </label>
                    <div className="space-y-2.5">
                      {currentQ.options.map((opt) => {
                        const isCorrect = opt.key === currentQ.correct_option;
                        return (
                          <div
                            key={opt.key}
                            className={cn(
                              'p-3.5 rounded-xl border text-sm flex items-start gap-3 transition-colors',
                              isCorrect
                                ? 'border-emerald-500/50 bg-emerald-500/15 text-white font-medium shadow-sm'
                                : 'border-white/10 text-slate-300 bg-white/[0.02]'
                            )}
                          >
                            <span
                              className={cn(
                                'h-6 w-6 rounded-md flex items-center justify-center font-bold text-xs flex-shrink-0',
                                isCorrect ? 'bg-emerald-500 text-white' : 'bg-white/10 text-slate-300'
                              )}
                            >
                              {opt.key}
                            </span>
                            <span className="flex-1 pt-0.5">{opt.text}</span>
                            {isCorrect && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                                GROUND TRUTH
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Explanation */}
                  {currentQ.explanation && (
                    <div>
                      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                        Clinical & Pathological Explanation
                      </label>
                      <div className="text-slate-200 text-xs sm:text-sm bg-sky-950/30 p-4 rounded-xl border border-sky-500/20 leading-relaxed whitespace-pre-wrap">
                        {currentQ.explanation}
                      </div>
                    </div>
                  )}

                  {/* Citations */}
                  {currentQ.citations && currentQ.citations.length > 0 && (
                    <div>
                      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                        Authoritative Evidence Citations
                      </label>
                      <div className="space-y-2">
                        {currentQ.citations.map((c, i) => (
                          <div key={i} className="text-xs p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                            <div className="flex items-center justify-between mb-1 font-bold text-white">
                              <span>{c.source_title}</span>
                              <Badge variant={c.verification_status === 'HUMAN_VERIFIED' ? 'verified' : 'suggested'}>
                                {c.verification_status}
                              </Badge>
                            </div>
                            {c.chapter && <div className="text-slate-300">Chapter: {c.chapter}</div>}
                            {c.page_range && <div className="text-slate-400">Pages: {c.page_range}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bottom One-Click Editorial Action Buttons */}
                <div className="pt-6 mt-8 border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-slate-400">
                    Action will update status and advance to next question
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={updatingId === currentQ.id}
                      onClick={() => handleUpdateStatus(currentQ.id, 'REJECTED', true)}
                      className="bg-red-600/80 hover:bg-red-600 text-xs"
                    >
                      Reject & Next
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      disabled={updatingId === currentQ.id}
                      onClick={() => handleUpdateStatus(currentQ.id, 'HUMAN_REVIEW', true)}
                      className="border-amber-500/40 text-amber-300 hover:bg-amber-500/10 text-xs"
                    >
                      Flag for Faculty Review
                    </Button>

                    <Button
                      variant="gradient"
                      size="sm"
                      disabled={updatingId === currentQ.id}
                      onClick={() => handleUpdateStatus(currentQ.id, 'APPROVED', true)}
                      className="text-xs gap-1.5"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Approve & Next</span>
                    </Button>
                  </div>
                </div>
              </Card>
            ) : (
              <div className="h-full glass-card p-12 text-center flex flex-col items-center justify-center text-slate-400">
                <FileCheck className="h-12 w-12 text-slate-600 mb-3" />
                <h3 className="text-base font-bold text-white">Select a Question to Inspect</h3>
                <p className="text-xs mt-1">Choose any question from the left batch to inspect details and edit status.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* MODE 2: TABLE VIEW */}
      {/* ------------------------------------------------------------------- */}
      {viewMode === 'TABLE' && (
        <div className="rounded-2xl border border-white/[0.08] overflow-hidden bg-slate-900/40 backdrop-blur-md mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/[0.03] text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                <tr>
                  <th className="px-6 py-4 font-semibold">Question Stem</th>
                  <th className="px-6 py-4 font-semibold">Topic / Taxonomy</th>
                  <th className="px-6 py-4 font-semibold">Ans</th>
                  <th className="px-6 py-4 font-semibold">Difficulty</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                      <div className="animate-spin h-8 w-8 border-3 border-sky-500 border-t-transparent rounded-full mx-auto mb-3" />
                      <span>Loading questions from PostgreSQL...</span>
                    </td>
                  </tr>
                ) : questions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                      No questions found matching the selected filters.
                    </td>
                  </tr>
                ) : (
                  questions.map((q, idx) => (
                    <tr key={q.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 max-w-md">
                        <div className="font-medium text-white line-clamp-2 leading-relaxed">{q.stem}</div>
                        <div className="text-[11px] text-slate-500 mt-1 font-mono flex items-center gap-2">
                          <span>{q.external_source_id}</span>
                          {isImageReferencedInText(q.stem) && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              Image Ref
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant="secondary" className="text-xs">
                          {q.topic_name_normalized}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="h-6 w-6 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold inline-flex items-center justify-center">
                          {q.correct_option || '?'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="capitalize text-xs font-semibold text-slate-300">
                          {q.difficulty}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge
                          variant={
                            q.status === 'APPROVED'
                              ? 'success'
                              : q.status === 'HUMAN_REVIEW'
                              ? 'warning'
                              : q.status === 'REJECTED'
                              ? 'destructive'
                              : 'outline'
                          }
                          className="text-xs"
                        >
                          {q.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedIndex(idx);
                            setViewMode('SPLIT');
                          }}
                          className="h-8 text-xs border-white/10"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" />
                          <span>Inspect</span>
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination Footer */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-4">
        <div>
          Showing {questions.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
          {Math.min(page * pageSize, totalCount)} of {totalCount.toLocaleString()} questions
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="border-white/10"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            <span>Previous Page</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="border-white/10"
          >
            <span>Next Page</span>
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
