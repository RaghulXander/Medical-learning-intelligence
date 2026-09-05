'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Search,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  LayoutGrid,
  Columns,
  ShieldCheck,
  ShieldAlert,
  Lock,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { questionsApi, adminApi, TopicCountItem } from '@medical/api-client';
import { Question, AdminUserListItem, UserRole } from '@medical/shared';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';
import { AuthModal } from '@/components/auth/auth-modal';

export default function AdminDashboardPage() {
  const { user, isLoading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';
  const isAdmin = user?.role === 'ADMIN' || isSuperAdmin;

  const requestedView = searchParams.get('view');
  const activeTab: 'QUESTIONS' | 'USERS' | 'STATS' =
    requestedView === 'users' ? 'USERS' : requestedView === 'stats' ? 'STATS' : 'QUESTIONS';

  // ---------------------------------------------------------------------------
  // TAB 1: Questions State
  // ---------------------------------------------------------------------------
  const [questions, setQuestions] = useState<Question[]>([]);
  const [topics, setTopics] = useState<TopicCountItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'SPLIT' | 'TABLE'>('SPLIT');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // ---------------------------------------------------------------------------
  // TAB 2: Users & RBAC State
  // ---------------------------------------------------------------------------
  const [usersList, setUsersList] = useState<AdminUserListItem[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersSearch, setUsersSearch] = useState('');
  const [debouncedUserSearch, setDebouncedUserSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [usersLoading, setUsersLoading] = useState(false);
  const [roleUpdatingUserId, setRoleUpdatingUserId] = useState<string | null>(null);
  const [subscriptionUpdatingUserId, setSubscriptionUpdatingUserId] = useState<string | null>(null);
  const [userActionMsg, setUserActionMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // ---------------------------------------------------------------------------
  // TAB 3: System Statistics State
  // ---------------------------------------------------------------------------
  const [statsData, setStatsData] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Debounce search inputs
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
      setSelectedIndex(0);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedUserSearch(usersSearch);
      setUsersPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [usersSearch]);

  // Load available topics on mount
  useEffect(() => {
    if (!isAdmin) return;

    async function loadTopics() {
      try {
        const data = await questionsApi.listTopics();
        setTopics(data);
      } catch (err) {
        console.warn('Could not load topics list:', err);
      }
    }
    loadTopics();
  }, [isAdmin]);

  // Fetch questions
  const fetchQuestions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await questionsApi.listQuestions({
        search: debouncedSearch || undefined,
        topic: selectedTopic !== 'ALL' ? selectedTopic : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      setQuestions(res.items || []);
      setTotalCount(res.total || 0);
      setSelectedIndex(0);
    } catch (err: any) {
      console.error('Failed to fetch questions:', err);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, selectedTopic, statusFilter, page]);

  useEffect(() => {
    if (isAdmin && activeTab === 'QUESTIONS') {
      fetchQuestions();
    }
  }, [fetchQuestions, activeTab, isAdmin]);

  // Fetch users for RBAC management
  const fetchUsers = useCallback(async () => {
    try {
      setUsersLoading(true);
      setUserActionMsg(null);
      const res = await adminApi.listUsers({
        search: debouncedUserSearch || undefined,
        role: roleFilter !== 'ALL' ? roleFilter : undefined,
        page: usersPage,
        limit: 20,
      });
      setUsersList(res.items || []);
      setUsersTotal(res.total || 0);
    } catch (err: any) {
      console.error('Failed to fetch users list:', err);
    } finally {
      setUsersLoading(false);
    }
  }, [debouncedUserSearch, roleFilter, usersPage]);

  useEffect(() => {
    if (isAdmin && activeTab === 'USERS') {
      fetchUsers();
    }
  }, [fetchUsers, activeTab, isAdmin]);

  // Fetch statistics
  useEffect(() => {
    if (isAdmin && activeTab === 'STATS') {
      setStatsLoading(true);
      adminApi
        .getStats()
        .then(setStatsData)
        .catch(console.error)
        .finally(() => setStatsLoading(false));
    }
  }, [activeTab, isAdmin]);

  const handleUpdateStatus = async (questionId: string, newStatus: string) => {
    try {
      setUpdatingId(questionId);
      let notes: string | undefined = undefined;
      if (newStatus === 'REJECTED' || newStatus === 'RETIRED') {
        const inputNotes = window.prompt(
          `Please provide review notes / reason for marking this question as ${newStatus}:`
        );
        if (inputNotes === null) {
          // User clicked cancel
          setUpdatingId(null);
          return;
        }
        if (!inputNotes.trim()) {
          alert(`Review notes are required when moving a question to ${newStatus}.`);
          setUpdatingId(null);
          return;
        }
        notes = inputNotes.trim();
      }
      await questionsApi.updateStatus(questionId, newStatus as any, notes);
      setQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, status: newStatus as any } : q))
      );
    } catch (err: any) {
      alert('Failed to update status: ' + (err?.message || 'Unknown error'));
    } finally {
      setUpdatingId(null);
    }
  };

  const handleUpdateRole = async (targetUserId: string, newRole: string) => {
    try {
      setRoleUpdatingUserId(targetUserId);
      setUserActionMsg(null);
      await adminApi.updateUserRole(targetUserId, newRole);
      setUsersList((prev) =>
        prev.map((u) => (u.id === targetUserId ? { ...u, role: newRole as UserRole } : u))
      );
      setUserActionMsg({ text: `User role successfully updated to ${newRole}`, type: 'success' });
      setTimeout(() => setUserActionMsg(null), 3000);
    } catch (err: any) {
      setUserActionMsg({
        text: err?.message || 'Failed to update role. Insufficient permissions.',
        type: 'error',
      });
    } finally {
      setRoleUpdatingUserId(null);
    }
  };

  const handleUpdateSubscription = async (targetUserId: string, isSubscribed: boolean) => {
    try {
      setSubscriptionUpdatingUserId(targetUserId);
      setUserActionMsg(null);
      await adminApi.updateUserSubscription(targetUserId, isSubscribed);
      setUsersList((prev) =>
        prev.map((u) => (u.id === targetUserId ? { ...u, is_subscribed: isSubscribed } : u))
      );
      setUserActionMsg({
        text: isSubscribed ? 'Exam access granted successfully' : 'Exam access revoked successfully',
        type: 'success',
      });
    } catch (err: any) {
      setUserActionMsg({ text: err?.message || 'Failed to update exam access', type: 'error' });
    } finally {
      setSubscriptionUpdatingUserId(null);
    }
  };

  // ---------------------------------------------------------------------------
  // RBAC Authentication Guard
  // ---------------------------------------------------------------------------
  if (authLoading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <div className="animate-spin h-10 w-10 border-3 border-sky-500 border-t-transparent rounded-full mb-3" />
        <h3 className="text-base font-bold text-foreground">Verifying Admin Access Permissions...</h3>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center p-4">
        <Card className="glass-card max-w-md p-8 text-center border-border space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center mx-auto text-sky-400">
            <Lock className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Admin Privileges Required</h2>
          <p className="text-xs text-muted-foreground">
            Access to the Question Bank, Editorial Review, and User Governance is restricted to verified Administrators.
          </p>
          <Button variant="gradient" onClick={() => setAuthModalOpen(true)} className="w-full gap-2 font-bold">
            <ShieldCheck className="h-4 w-4" />
            <span>Sign In to Admin Portal</span>
          </Button>
        </Card>
        <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center p-4">
        <Card className="glass-card max-w-md p-8 text-center border-rose-500/30 bg-rose-950/20 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400">
            <ShieldAlert className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Access Forbidden (403)</h2>
          <p className="text-xs text-foreground/80">
            Your account ({user.email}) is currently assigned the role <Badge variant="destructive">{user.role}</Badge>.
          </p>
          <p className="text-xs text-muted-foreground">
            Contact a Super Administrator (<strong className="text-foreground">raghuldpi95@gmail.com</strong>) to request administrative privileges.
          </p>
          <Link href="/student" className="inline-block w-full">
            <Button variant="outline" className="w-full border-border text-xs">
              Return to Student Hub
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const selectedQuestion = questions[selectedIndex];

  return (
    <div className="container px-4 sm:px-8 py-6 max-w-7xl mx-auto space-y-6">
      {/* ======================================================================= */}
      {/* TAB 1: QUESTION BANK MANAGEMENT */}
      {/* ======================================================================= */}
      {activeTab === 'QUESTIONS' && (
        <div className="space-y-6 animate-fade-in">
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl glass-card border border-border bg-card/60">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              <div className="relative min-w-[220px] max-w-sm flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search question stem, keywords..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-xl bg-background/80 border border-border text-foreground text-xs placeholder:text-muted-foreground focus:outline-none focus:border-sky-500"
                />
              </div>

              <select
                value={selectedTopic}
                onChange={(e) => {
                  setSelectedTopic(e.target.value);
                  setPage(1);
                }}
                className="h-9 px-3 rounded-xl bg-background/80 border border-border text-foreground text-xs focus:outline-none focus:border-sky-500 max-w-[200px]"
              >
                <option value="ALL">All Topics</option>
                {topics.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name} ({t.count})
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="h-9 px-3 rounded-xl bg-background/80 border border-border text-foreground text-xs focus:outline-none focus:border-sky-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="IMPORTED">IMPORTED</option>
                <option value="APPROVED">APPROVED</option>
                <option value="AI_REVIEW">AI_REVIEW</option>
                <option value="REJECTED">REJECTED</option>
                <option value="REPORTED">REPORTED</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center p-1 rounded-xl bg-muted/40 border border-border">
                <button
                  type="button"
                  onClick={() => setViewMode('SPLIT')}
                  className={cn(
                    'p-1.5 rounded-lg text-xs transition-colors',
                    viewMode === 'SPLIT' ? 'bg-sky-500 text-white' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Split Review Mode"
                >
                  <Columns className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('TABLE')}
                  className={cn(
                    'p-1.5 rounded-lg text-xs transition-colors',
                    viewMode === 'TABLE' ? 'bg-sky-500 text-white' : 'text-muted-foreground hover:text-foreground'
                  )}
                  title="Full Table View"
                >
                  <LayoutGrid className="h-4 w-4" />
                </button>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={fetchQuestions}
                className="h-9 border-border text-xs gap-1 text-foreground/80"
              >
                <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
                <span>Refresh</span>
              </Button>
            </div>
          </div>

          {/* SPLIT VIEW REVIEW MODE */}
          {viewMode === 'SPLIT' ? (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
              {/* Left Question List */}
              <div className="lg:col-span-5 space-y-2 max-h-[750px] overflow-y-auto pr-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground pb-2">
                  <span>
                    Showing {questions.length} of {totalCount} Questions
                  </span>
                  <span>Page {page}</span>
                </div>

                {loading ? (
                  <div className="p-8 text-center text-xs text-muted-foreground">Loading questions...</div>
                ) : questions.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted-foreground">No questions found matching criteria.</div>
                ) : (
                  questions.map((q, idx) => (
                    <div
                      key={q.id}
                      onClick={() => setSelectedIndex(idx)}
                      className={cn(
                        'p-3.5 rounded-xl border text-left cursor-pointer transition-all space-y-1.5',
                        selectedIndex === idx
                          ? 'border-sky-500 bg-sky-500/10 shadow-md'
                          : 'border-border bg-muted/20 hover:border-border hover:bg-muted/40'
                      )}
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-mono text-muted-foreground truncate max-w-[120px]">{q.id}</span>
                        <Badge
                          variant={
                            q.status === 'APPROVED'
                              ? 'verified'
                              : q.status === 'REJECTED'
                              ? 'destructive'
                              : 'secondary'
                          }
                          className="text-[9px] px-1.5 py-0"
                        >
                          {q.status}
                        </Badge>
                      </div>
                      <p className="text-xs font-semibold text-foreground line-clamp-2">{q.stem}</p>
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span className="truncate max-w-[140px]">{q.primary_topic_id || 'General'}</span>
                        <span className="uppercase">{q.difficulty || 'medium'}</span>
                      </div>
                    </div>
                  ))
                )}

                {/* Pagination Controls */}
                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                    className="h-8 text-xs border-border"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">Page {page}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={questions.length < pageSize}
                    onClick={() => setPage(page + 1)}
                    className="h-8 text-xs border-border"
                  >
                    Next <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Right Deep Review Pane */}
              <div className="lg:col-span-7">
                {selectedQuestion ? (
                  <Card className="glass-card p-6 border-border space-y-6 sticky top-24 bg-card/85">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {selectedQuestion.id}
                          </Badge>
                          <Badge variant="verified" className="text-[10px]">
                            {selectedQuestion.status}
                          </Badge>
                        </div>
                        <h3 className="text-sm font-bold text-foreground">{selectedQuestion.primary_topic_id}</h3>
                      </div>

                      {/* Review Action Buttons */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="gradient"
                          size="sm"
                          disabled={updatingId === selectedQuestion.id || selectedQuestion.status === 'APPROVED'}
                          onClick={() => handleUpdateStatus(selectedQuestion.id, 'APPROVED')}
                          className="text-xs font-bold gap-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Approve</span>
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={updatingId === selectedQuestion.id || selectedQuestion.status === 'REJECTED'}
                          onClick={() => handleUpdateStatus(selectedQuestion.id, 'REJECTED')}
                          className="text-xs font-bold gap-1 border-rose-500/30 text-rose-300 hover:bg-rose-500/10"
                        >
                          <span>Reject</span>
                        </Button>
                      </div>
                    </div>

                    {/* Question Stem */}
                    <Link href={`/admin/questions/${selectedQuestion.id}`} className="block"><Button variant="outline" size="sm" className="w-full">Edit question content & review history</Button></Link>

                    {/* Question Stem */}
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground mb-1">Question Stem:</h4>
                      <p className="text-sm font-bold text-foreground leading-relaxed p-3.5 rounded-xl bg-background/70 border border-border/70">
                        {selectedQuestion.stem}
                      </p>
                    </div>

                    {/* Options */}
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground mb-2">Options:</h4>
                      <div className="space-y-2">
                        {Array.isArray(selectedQuestion.options)
                          ? selectedQuestion.options.map((opt: any) => {
                              const isCorrect = opt.key === selectedQuestion.correct_option;
                              return (
                                <div
                                  key={opt.key}
                                  className={cn(
                                    'p-3 rounded-xl border text-xs flex items-center gap-3',
                                    isCorrect
                                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300 font-semibold'
                                      : 'bg-muted/20 border-border/70 text-foreground/80'
                                  )}
                                >
                                  <span className="w-5 h-5 rounded-md bg-muted/60 flex items-center justify-center font-bold text-[10px]">
                                    {opt.key}
                                  </span>
                                  <span className="flex-1">{opt.text}</span>
                                  {isCorrect && <Check className="h-4 w-4 text-emerald-400" />}
                                </div>
                              );
                            })
                          : Object.entries(selectedQuestion.options || {}).map(([k, text]) => {
                              const isCorrect = k === selectedQuestion.correct_option;
                              return (
                                <div
                                  key={k}
                                  className={cn(
                                    'p-3 rounded-xl border text-xs flex items-center gap-3',
                                    isCorrect
                                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300 font-semibold'
                                      : 'bg-muted/20 border-border/70 text-foreground/80'
                                  )}
                                >
                                  <span className="w-5 h-5 rounded-md bg-muted/60 flex items-center justify-center font-bold text-[10px]">
                                    {k}
                                  </span>
                                  <span className="flex-1">{String(text)}</span>
                                  {isCorrect && <Check className="h-4 w-4 text-emerald-400" />}
                                </div>
                              );
                            })}
                      </div>
                    </div>

                    {/* Explanation */}
                    <div>
                      <h4 className="text-xs font-semibold text-muted-foreground mb-1">Clinical Explanation & Rationale:</h4>
                      <p className="text-xs text-foreground/80 leading-relaxed p-3.5 rounded-xl bg-background/70 border border-border/70">
                        {selectedQuestion.explanation || 'No detailed rationale attached.'}
                      </p>
                    </div>
                  </Card>
                ) : (
                  <div className="p-12 text-center text-xs text-muted-foreground">Select a question to inspect.</div>
                )}
              </div>
            </div>
          ) : (
            /* FULL TABLE VIEW */
            <div className="p-4 rounded-2xl glass-card border border-border overflow-x-auto">
              <table className="w-full text-left text-xs text-foreground/80">
                <thead className="border-b border-border text-muted-foreground uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">ID</th>
                    <th className="py-2.5 px-3">Stem Preview</th>
                    <th className="py-2.5 px-3">Topic</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {questions.map((q) => (
                    <tr key={q.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-3 font-mono text-[10px] text-muted-foreground truncate max-w-[90px]">{q.id}</td>
                      <td className="py-3 px-3 font-medium text-foreground max-w-md truncate">{q.stem}</td>
                      <td className="py-3 px-3 truncate max-w-[140px]">{q.primary_topic_id || 'General'}</td>
                      <td className="py-3 px-3">
                        <Badge
                          variant={
                            q.status === 'APPROVED'
                              ? 'verified'
                              : q.status === 'REJECTED'
                              ? 'destructive'
                              : 'secondary'
                          }
                          className="text-[10px]"
                        >
                          {q.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 text-right space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUpdateStatus(q.id, 'APPROVED')}
                          className="text-[11px] text-emerald-400 hover:bg-emerald-500/10 h-7"
                        >
                          Approve
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUpdateStatus(q.id, 'REJECTED')}
                          className="text-[11px] text-rose-400 hover:bg-rose-500/10 h-7"
                        >
                          Reject
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 2: USER MANAGEMENT & RBAC GOVERNANCE */}
      {/* ======================================================================= */}
      {activeTab === 'USERS' && (
        <div className="space-y-6 animate-fade-in">
          {/* Action Notification Banner */}
          {userActionMsg && (
            <div
              className={cn(
                'p-3.5 rounded-xl border text-xs flex items-center gap-2',
                userActionMsg.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              )}
            >
              {userActionMsg.type === 'success' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-rose-400" />
              )}
              <span>{userActionMsg.text}</span>
            </div>
          )}

          {/* User Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl glass-card border border-border bg-card/60">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              <div className="relative min-w-[240px] max-w-sm flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search user name, doctor email..."
                  value={usersSearch}
                  onChange={(e) => setUsersSearch(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-xl bg-background/80 border border-border text-foreground text-xs placeholder:text-muted-foreground focus:outline-none focus:border-sky-500"
                />
              </div>

              <select
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setUsersPage(1);
                }}
                className="h-9 px-3 rounded-xl bg-background/80 border border-border text-foreground text-xs focus:outline-none focus:border-sky-500"
              >
                <option value="ALL">All Roles</option>
                <option value="SUPER_ADMIN">Super Admins</option>
                <option value="ADMIN">Admins</option>
                <option value="REVIEWER">Reviewers</option>
                <option value="EDUCATOR">Educators</option>
                <option value="USER">Students / Users</option>
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchUsers}
              className="h-9 border-border text-xs gap-1 text-foreground/80"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', usersLoading && 'animate-spin')} />
              <span>Refresh Users</span>
            </Button>
          </div>

          {/* Users Table */}
          <Card className="glass-card p-4 sm:p-6 border-border overflow-x-auto">
            <div className="flex items-center justify-between text-xs text-muted-foreground pb-3 mb-2 border-b border-border">
              <span>
                Registered Users: <strong className="text-foreground">{usersTotal}</strong>
              </span>
              <span>
                Signed in as: <strong className="text-foreground">{user.email}</strong> ({user.role})
              </span>
            </div>

            <table className="w-full text-left text-xs text-foreground/80">
              <thead className="border-b border-border text-muted-foreground uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">User & Email</th>
                  <th className="py-2.5 px-3">Exam Access</th>
                  <th className="py-2.5 px-3">Target Exam</th>
                  <th className="py-2.5 px-3">Stage / College</th>
                  <th className="py-2.5 px-3">Attempts</th>
                  <th className="py-2.5 px-3">Current Role</th>
                  <th className="py-2.5 px-3 text-right">Assign Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {usersList.map((u) => {
                  const isProtectedSuperAdmin = u.is_protected;

                  return (
                    <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div>
                            <div className="font-bold text-foreground flex items-center gap-1.5">
                              <span>{u.name}</span>
                              {isProtectedSuperAdmin && (
                                <Badge variant="verified" className="text-[9px] bg-purple-500/20 text-purple-300 border-purple-500/40">
                                  🛡️ Permanent Super Admin
                                </Badge>
                              )}
                            </div>
                            <span className="text-[11px] text-muted-foreground">{u.email}</span>
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <button
                          type="button"
                          disabled={subscriptionUpdatingUserId === u.id}
                          onClick={() => handleUpdateSubscription(u.id, !u.is_subscribed)}
                          className={cn(
                            'text-[10px] px-2.5 py-1 rounded-full font-bold border transition-colors disabled:opacity-50',
                            u.is_subscribed
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                              : 'bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20'
                          )}
                        >
                          {subscriptionUpdatingUserId === u.id
                            ? 'Updating...'
                            : u.is_subscribed
                            ? 'Subscribed'
                            : 'Grant Access'}
                        </button>
                      </td>

                      <td className="py-3 px-3">
                        <Badge variant="outline" className="text-[10px]">
                          {u.target_exam || 'NEET_SS'}
                        </Badge>
                      </td>

                      <td className="py-3 px-3 text-[11px] text-muted-foreground">
                        {u.residency_stage ? `${u.residency_stage}` : 'Resident'}
                        {u.medical_college ? ` • ${u.medical_college}` : ''}
                      </td>

                      <td className="py-3 px-3 font-semibold text-foreground">
                        {u.total_attempts} Tests
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={cn(
                            'text-[10px] px-2 py-0.5 rounded-full font-bold uppercase',
                            u.role === 'SUPER_ADMIN'
                              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                              : u.role === 'ADMIN'
                              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                              : u.role === 'REVIEWER'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-muted/60 text-foreground/80'
                          )}
                        >
                          {u.role}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right">
                        {isProtectedSuperAdmin ? (
                          <span className="text-[10px] text-purple-400 font-semibold italic">Protected</span>
                        ) : (
                          <select
                            value={u.role}
                            disabled={roleUpdatingUserId === u.id || (!isSuperAdmin && (u.role === 'ADMIN' || u.role === 'SUPER_ADMIN'))}
                            onChange={(e) => handleUpdateRole(u.id, e.target.value)}
                            className="h-8 px-2.5 rounded-lg bg-background/90 border border-border text-foreground text-xs focus:outline-none focus:border-sky-500 transition-colors"
                          >
                            <option value="USER">USER (Student)</option>
                            <option value="REVIEWER">REVIEWER</option>
                            <option value="EDUCATOR">EDUCATOR</option>
                            {isSuperAdmin && <option value="ADMIN">ADMIN</option>}
                            {isSuperAdmin && <option value="SUPER_ADMIN">SUPER_ADMIN</option>}
                          </select>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 3: PLATFORM OVERVIEW & SYSTEM STATS */}
      {/* ======================================================================= */}
      {activeTab === 'STATS' && (
        <div className="space-y-6 animate-fade-in">
          {statsLoading || !statsData ? (
            <div className="p-12 text-center text-xs text-muted-foreground">Loading system metrics...</div>
          ) : (
            <div className="space-y-6">
              {/* Stat Counters */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="glass-card p-6 border-border text-center">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">Total Registered Users</span>
                  <div className="text-3xl sm:text-4xl font-extrabold text-foreground mt-1">{statsData.total_users}</div>
                </Card>

                <Card className="glass-card p-6 border-border text-center">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">Total Curated Questions</span>
                  <div className="text-3xl sm:text-4xl font-extrabold text-sky-400 mt-1">{statsData.total_questions}</div>
                </Card>

                <Card className="glass-card p-6 border-border text-center">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">Diagnostic Mock Attempts</span>
                  <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400 mt-1">{statsData.total_attempts}</div>
                </Card>
              </div>

              {/* Status & Roles Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="glass-card p-6 border-border space-y-4">
                  <h3 className="text-sm font-bold text-foreground">Questions by Status</h3>
                  <div className="space-y-2 text-xs">
                    {Object.entries(statsData.questions_by_status || {}).map(([st, cnt]: any) => (
                      <div key={st} className="flex items-center justify-between p-2.5 rounded-xl bg-muted/20 border border-border/70">
                        <span className="font-semibold text-foreground/80">{st}</span>
                        <Badge variant="outline" className="text-xs">{cnt}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="glass-card p-6 border-border space-y-4">
                  <h3 className="text-sm font-bold text-foreground">Users by RBAC Role</h3>
                  <div className="space-y-2 text-xs">
                    {Object.entries(statsData.users_by_role || {}).map(([r, cnt]: any) => (
                      <div key={r} className="flex items-center justify-between p-2.5 rounded-xl bg-muted/20 border border-border/70">
                        <span className="font-semibold text-foreground/80">{r}</span>
                        <Badge variant="verified" className="text-xs">{cnt}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
