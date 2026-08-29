'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, History, Save, ShieldAlert } from 'lucide-react';
import { ApiError, questionsApi } from '@medical/api-client';
import { Question, QuestionEditPayload, QuestionEditSchema, QuestionRevision, QuestionStatus } from '@medical/shared';
import { SchemaFieldEditor } from '@/components/editor/schema-field-editor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/lib/auth-context';
import { cloneJson, JsonObject, setJsonPath } from '@/lib/editor/json';
import { questionEditorFields } from '@/lib/questions/editor-schema';

function normalizeOptions(options: Question['options']): Question['options'] {
  if (Array.isArray(options)) return options;
  return Object.entries(options as unknown as Record<string, string>).map(([key, text]) => ({ key, text }));
}

function createDraft(question: Question): QuestionEditPayload {
  return {
    expected_updated_at: question.updated_at ?? '',
    stem: question.stem,
    options: normalizeOptions(question.options),
    correct_option: question.correct_option,
    explanation: question.explanation ?? '',
    difficulty: question.difficulty,
    cognitive_level: question.cognitive_level,
    question_type: question.question_type,
    primary_topic_id: question.primary_topic_id ?? '',
    learning_objective: question.learning_objective ?? '',
    edit_notes: '',
  };
}

export default function QuestionEditorPage({ params }: { params: Promise<{ questionId: string }> }) {
  const { user, isLoading: authLoading } = useAuth();
  const [questionId, setQuestionId] = useState('');
  const [question, setQuestion] = useState<Question | null>(null);
  const [draft, setDraft] = useState<QuestionEditPayload | null>(null);
  const [revisions, setRevisions] = useState<QuestionRevision[]>([]);
  const [reviewNotes, setReviewNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canEdit = ['SUPER_ADMIN', 'ADMIN', 'REVIEWER', 'EDUCATOR'].includes(user?.role ?? '');
  const canReview = ['SUPER_ADMIN', 'ADMIN', 'REVIEWER'].includes(user?.role ?? '');

  useEffect(() => { void params.then(({ questionId: id }) => setQuestionId(id)); }, [params]);

  const load = useCallback(async () => {
    if (!questionId || !canEdit) return;
    setLoading(true);
    try {
      const [loadedQuestion, revisionResponse] = await Promise.all([questionsApi.getQuestion(questionId), questionsApi.listRevisions(questionId)]);
      setQuestion(loadedQuestion);
      setDraft(createDraft(loadedQuestion));
      setRevisions(revisionResponse.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load question');
    } finally { setLoading(false); }
  }, [canEdit, questionId]);

  useEffect(() => { if (!authLoading) void load(); }, [authLoading, load]);

  const parsed = useMemo(() => QuestionEditSchema.safeParse(draft), [draft]);
  const save = async () => {
    if (!parsed.success || !draft) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      await questionsApi.updateQuestion(questionId, parsed.data);
      setMessage('Question saved with an immutable revision snapshot.');
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409 ? 'Another editor saved this question. Reload before applying your changes.' : caught instanceof Error ? caught.message : 'Save failed');
    } finally { setSaving(false); }
  };

  const transition = async (status: QuestionStatus) => {
    if ((status === 'REJECTED' || status === 'RETIRED') && !reviewNotes.trim()) { setError('Review notes are required to reject or retire a question.'); return; }
    setSaving(true); setError(null); setMessage(null);
    try {
      await questionsApi.updateStatus(questionId, status, reviewNotes);
      setMessage(`Question moved to ${status}.`); setReviewNotes(''); await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Status update failed'); }
    finally { setSaving(false); }
  };

  if (authLoading || loading) return <div className="min-h-[60vh] grid place-items-center text-slate-300">Loading question editor…</div>;
  if (!canEdit) return <div className="min-h-[60vh] grid place-items-center"><Card className="glass-card p-8 text-center"><ShieldAlert className="mx-auto mb-3 text-amber-300" /><p className="text-white">Editorial permission required.</p></Card></div>;
  if (!question || !draft) return <div className="p-8 text-red-300">{error ?? 'Question unavailable'}</div>;

  const jsonDraft = cloneJson(draft) as unknown as JsonObject;
  return <div className="container mx-auto max-w-7xl px-4 py-8">
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div><Link href="/admin" className="mb-2 inline-flex items-center gap-1 text-xs text-sky-300"><ArrowLeft className="h-3 w-3" />Question bank</Link><h1 className="text-2xl font-bold text-white">Question editor</h1><div className="mt-2 flex gap-2"><Badge variant="secondary">{question.id}</Badge><Badge variant="verified">{question.status}</Badge></div></div>
      <Button variant="gradient" disabled={saving || !parsed.success} onClick={() => void save()}><Save className="mr-2 h-4 w-4" />{saving ? 'Saving…' : 'Save revision'}</Button>
    </div>
    {message && <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{message}</div>}
    {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>}
    {!parsed.success && <div className="mb-4 whitespace-pre-wrap rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">{parsed.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('\n')}</div>}
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <Card className="glass-card p-6"><SchemaFieldEditor value={jsonDraft} fields={questionEditorFields} onChange={(path, value) => setDraft(setJsonPath(jsonDraft, path, value) as unknown as QuestionEditPayload)} /></Card>
      <div className="space-y-6">
        {canReview && <Card className="glass-card p-5"><h2 className="mb-3 font-bold text-white">Review workflow</h2><textarea rows={4} value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="Review notes (required for reject/retire)" className="mb-3 w-full rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white" /><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void transition('HUMAN_REVIEW')}>Human review</Button><Button size="sm" variant="gradient" onClick={() => void transition('APPROVED')}>Approve</Button><Button size="sm" variant="destructive" onClick={() => void transition('REJECTED')}>Reject</Button><Button size="sm" variant="outline" onClick={() => void transition('RETIRED')}>Retire</Button></div></Card>}
        <Card className="glass-card p-5"><h2 className="mb-3 flex items-center gap-2 font-bold text-white"><History className="h-4 w-4" />Revision history</h2>{revisions.length === 0 ? <p className="text-xs text-slate-400">No content revisions yet.</p> : <div className="space-y-3">{revisions.map((revision) => <div key={revision.id} className="rounded-lg border border-white/10 p-3 text-xs"><div className="font-semibold text-white">Revision {revision.revision_number}</div><div className="mt-1 text-slate-400">{revision.changed_fields.join(', ')}</div>{revision.edit_notes && <p className="mt-2 text-slate-300">{revision.edit_notes}</p>}<time className="mt-2 block text-slate-500">{new Date(revision.created_at).toLocaleString()}</time></div>)}</div>}</Card>
        {question.citations && question.citations.length > 0 && <Card className="glass-card p-5"><h2 className="mb-3 font-bold text-white">Evidence (read only)</h2>{question.citations.map((citation, index) => <div key={index} className="mb-2 rounded border border-white/10 p-3 text-xs text-slate-300">{citation.source_title}<br /><span className="text-slate-500">{citation.verification_status}</span></div>)}</Card>}
      </div>
    </div>
  </div>;
}
