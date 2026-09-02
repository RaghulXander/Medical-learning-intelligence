'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  ChevronRight,
  FileSearch,
  History,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Trash2,
  XCircle,
} from 'lucide-react';
import { adminApi, ApiError } from '@medical/api-client';
import {
  RetrievalEvidenceChunk,
  RetrievalReviewCase,
  RetrievalReviewCaseListItem,
  RetrievalReviewSummary,
  RetrievalVerificationStatus,
} from '@medical/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/lib/auth-context';
import { cn } from '@/lib/utils';

const BENCHMARK_SLUG = 'm16a-retrieval-v1';
const sources = [
  'robbins_review',
  'robbins_pathologic_basis_11th',
  'sternberg_review_2nd',
];

type Draft = {
  domain: string;
  query: string;
  expected_chunk_ids: string[];
  out_of_corpus: boolean;
  notes: string;
};

function toDraft(item: RetrievalReviewCase): Draft {
  return {
    domain: item.domain,
    query: item.query,
    expected_chunk_ids: [...item.expected_chunk_ids],
    out_of_corpus: item.out_of_corpus,
    notes: item.review_notes ?? '',
  };
}

function statusVariant(status: RetrievalVerificationStatus) {
  if (status === 'HUMAN_VERIFIED') return 'success' as const;
  if (status === 'REJECTED') return 'destructive' as const;
  if (status === 'HUMAN_REVIEW') return 'warning' as const;
  return 'suggested' as const;
}

function pageLabel(chunk: RetrievalEvidenceChunk) {
  const printed = chunk.textbook_page ? `textbook p. ${chunk.textbook_page}` : null;
  const physical = chunk.pdf_page ? `PDF p. ${chunk.pdf_page}` : null;
  return [printed, physical].filter(Boolean).join(' · ') || 'Page unavailable';
}

export default function RetrievalReviewPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [summary, setSummary] = useState<RetrievalReviewSummary | null>(null);
  const [cases, setCases] = useState<RetrievalReviewCaseListItem[]>([]);
  const [selected, setSelected] = useState<RetrievalReviewCase | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [searchText, setSearchText] = useState('');
  const [searchSource, setSearchSource] = useState('');
  const [searchResults, setSearchResults] = useState<RetrievalEvidenceChunk[]>([]);
  const [attested, setAttested] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canReview = ['SUPER_ADMIN', 'ADMIN', 'REVIEWER'].includes(user?.role ?? '');
  const domains = useMemo(
    () => Object.keys(summary?.domain_counts ?? {}).sort(),
    [summary]
  );

  const loadQueue = useCallback(async () => {
    if (!canReview) return;
    setLoading(true);
    try {
      const [nextSummary, page] = await Promise.all([
        adminApi.getRetrievalReviewSummary(BENCHMARK_SLUG),
        adminApi.listRetrievalReviewCases(BENCHMARK_SLUG, {
          verification_status: statusFilter || undefined,
          domain: domainFilter || undefined,
          limit: 100,
        }),
      ]);
      setSummary(nextSummary);
      setCases(page.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load review queue');
    } finally {
      setLoading(false);
    }
  }, [canReview, domainFilter, statusFilter]);

  useEffect(() => {
    if (!authLoading) void loadQueue();
  }, [authLoading, loadQueue]);

  const openCase = async (caseId: string) => {
    setSaving(true);
    setError(null);
    try {
      const item = await adminApi.getRetrievalReviewCase(caseId, BENCHMARK_SLUG);
      setSelected(item);
      setDraft(toDraft(item));
      setDirty(false);
      setAttested(false);
      setSearchResults([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load case');
    } finally {
      setSaving(false);
    }
  };

  const refreshAfterChange = async (item: RetrievalReviewCase) => {
    setSelected(item);
    setDraft(toDraft(item));
    setDirty(false);
    setAttested(false);
    await loadQueue();
  };

  const updateDraft = (change: Partial<Draft>) => {
    setDraft((current) => (current ? { ...current, ...change } : current));
    setDirty(true);
    setAttested(false);
  };

  const saveDraft = async () => {
    if (!selected || !draft) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const item = await adminApi.updateRetrievalReviewCase(
        selected.id,
        {
          expected_revision: selected.revision,
          domain: draft.domain,
          query: draft.query,
          expected_chunk_ids: draft.out_of_corpus ? [] : draft.expected_chunk_ids,
          out_of_corpus: draft.out_of_corpus,
          notes: draft.notes,
        },
        BENCHMARK_SLUG
      );
      setMessage('Draft saved with an immutable review snapshot.');
      await refreshAfterChange(item);
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? 'Another reviewer changed this case. Reload it before saving.'
          : caught instanceof Error
          ? caught.message
          : 'Could not save draft'
      );
    } finally {
      setSaving(false);
    }
  };

  const decide = async (action: 'approve' | 'reject') => {
    if (!selected || !draft) return;
    if (dirty) {
      setError('Save your evidence and query changes before making a decision.');
      return;
    }
    if (!attested) {
      setError('Confirm the human-review attestation before making a decision.');
      return;
    }
    if (draft.notes.trim().length < 3) {
      setError('Add concise review notes before making a decision.');
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const item = await adminApi.decideRetrievalReviewCase(
        selected.id,
        action,
        selected.revision,
        draft.notes,
        BENCHMARK_SLUG
      );
      setMessage(action === 'approve' ? 'Case human-verified.' : 'Case rejected for correction.');
      await refreshAfterChange(item);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not record decision');
    } finally {
      setSaving(false);
    }
  };

  const searchEvidence = async () => {
    if (searchText.trim().length < 2) return;
    setSaving(true);
    setError(null);
    try {
      const result = await adminApi.searchRetrievalEvidence(
        searchText.trim(),
        searchSource || undefined
      );
      setSearchResults(result.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Evidence search failed');
    } finally {
      setSaving(false);
    }
  };

  const selectedEvidence = useMemo(() => {
    if (!selected || !draft) return [];
    const combined = [...selected.evidence, ...searchResults];
    const byId = new Map(combined.map((chunk) => [chunk.id, chunk]));
    return draft.expected_chunk_ids.map((id) => byId.get(id)).filter(Boolean) as RetrievalEvidenceChunk[];
  }, [draft, searchResults, selected]);

  if (authLoading || loading) {
    return <div className="grid min-h-[60vh] place-items-center text-muted-foreground">Loading retrieval review…</div>;
  }
  if (!canReview) {
    return <div className="grid min-h-[60vh] place-items-center"><Card className="p-8 text-center"><ShieldAlert className="mx-auto mb-3 text-amber-400" /><p>Reviewer permission required.</p></Card></div>;
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-5 px-4 py-6 sm:px-6">
      {summary && (
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold">{summary.title}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Human verification only · {summary.verified_cases} of {summary.total_cases} complete
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="success">{summary.verified_cases} verified</Badge>
              <Badge variant="suggested">{summary.status_counts.AUTO_BOOTSTRAP_UNVERIFIED ?? 0} bootstrap</Badge>
              <Badge variant="warning">{summary.status_counts.HUMAN_REVIEW ?? 0} draft</Badge>
              <Badge variant="destructive">{summary.status_counts.REJECTED ?? 0} rejected</Badge>
            </div>
          </div>
          <Progress className="mt-4" value={summary.progress_percent} />
        </Card>
      )}

      {message && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{message}</div>}
      {error && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <div className="space-y-3 border-b border-border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-bold">Review queue</h2>
              <Button size="icon" variant="ghost" onClick={() => void loadQueue()} aria-label="Refresh queue">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-lg border border-border bg-background px-2 py-2 text-xs">
                <option value="">All statuses</option>
                <option value="AUTO_BOOTSTRAP_UNVERIFIED">Bootstrap</option>
                <option value="HUMAN_REVIEW">Draft review</option>
                <option value="HUMAN_VERIFIED">Verified</option>
                <option value="REJECTED">Rejected</option>
              </select>
              <select value={domainFilter} onChange={(event) => setDomainFilter(event.target.value)} className="rounded-lg border border-border bg-background px-2 py-2 text-xs">
                <option value="">All domains</option>
                {domains.map((domain) => <option key={domain} value={domain}>{domain.replaceAll('_', ' ')}</option>)}
              </select>
            </div>
          </div>
          <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
            {cases.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void openCase(item.id)}
                className={cn(
                  'w-full border-b border-border p-4 text-left hover:bg-muted/50',
                  selected?.id === item.id && 'bg-sky-500/10'
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold">{item.case_key}</span>
                  <Badge variant={statusVariant(item.verification_status)}>{item.verification_status.replaceAll('_', ' ')}</Badge>
                </div>
                <p className="mt-2 line-clamp-2 text-sm">{item.query}</p>
                <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>{item.domain.replaceAll('_', ' ')}</span>
                  <span>{item.out_of_corpus ? 'Out of corpus' : `${item.expected_chunk_count} candidate chunk(s)`}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        {!selected || !draft ? (
          <Card className="grid min-h-[520px] place-items-center p-10 text-center text-muted-foreground">
            <div><FileSearch className="mx-auto mb-3 h-10 w-10" /><p>Select a benchmark case to inspect its evidence.</p></div>
          </Card>
        ) : (
          <div className="space-y-5">
            <Card className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{selected.case_key}</Badge>
                  <Badge variant={statusVariant(selected.verification_status)}>{selected.verification_status.replaceAll('_', ' ')}</Badge>
                  <span className="text-xs text-muted-foreground">Revision {selected.revision}</span>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" disabled={saving || !dirty} onClick={() => void saveDraft()}><Save className="mr-2 h-4 w-4" />Save draft</Button>
                  <Button variant="destructive" disabled={saving || dirty || !attested} onClick={() => void decide('reject')}><XCircle className="mr-2 h-4 w-4" />Reject</Button>
                  <Button variant="gradient" disabled={saving || dirty || !attested} onClick={() => void decide('approve')}><CheckCircle2 className="mr-2 h-4 w-4" />Verify</Button>
                </div>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-[220px_minmax(0,1fr)]">
                <label className="text-sm"><span className="mb-1 block font-semibold">Domain</span><input value={draft.domain} onChange={(event) => updateDraft({ domain: event.target.value })} className="w-full rounded-lg border border-border bg-background px-3 py-2" /></label>
                <label className="text-sm"><span className="mb-1 block font-semibold">Human-reviewed retrieval prompt</span><textarea rows={3} value={draft.query} onChange={(event) => updateDraft({ query: event.target.value })} className="w-full rounded-lg border border-border bg-background px-3 py-2" /></label>
              </div>

              <label className="mt-4 flex items-start gap-3 rounded-xl border border-border bg-muted/30 p-3 text-sm">
                <input type="checkbox" checked={draft.out_of_corpus} onChange={(event) => updateDraft({ out_of_corpus: event.target.checked, expected_chunk_ids: event.target.checked ? [] : draft.expected_chunk_ids })} className="mt-1" />
                <span><strong>Out-of-corpus control</strong><span className="block text-xs text-muted-foreground">Use only when none of the three books supports the prompt. Expected chunks must remain empty.</span></span>
              </label>
            </Card>

            {!draft.out_of_corpus && (
              <Card className="p-5">
                <h3 className="font-bold">Expected evidence</h3>
                <p className="mt-1 text-xs text-muted-foreground">Read the evidence and retain only chunks that directly support the prompt. Page proximity alone is insufficient.</p>
                <div className="mt-4 space-y-3">
                  {selectedEvidence.length === 0 && <div className="rounded-lg border border-dashed border-border p-5 text-sm text-muted-foreground">No expected evidence selected.</div>}
                  {selectedEvidence.map((chunk) => (
                    <div key={chunk.id} className="rounded-xl border border-border bg-background/40 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div><p className="text-sm font-bold">{chunk.source_title}</p><p className="text-xs text-muted-foreground">{chunk.edition} · {pageLabel(chunk)} · {chunk.chapter_name || 'Chapter unavailable'}</p></div>
                        <Button size="sm" variant="ghost" onClick={() => updateDraft({ expected_chunk_ids: draft.expected_chunk_ids.filter((id) => id !== chunk.id) })}><Trash2 className="mr-1 h-3.5 w-3.5" />Remove</Button>
                      </div>
                      <p className="mt-3 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm leading-6">{chunk.content}</p>
                      <p className="mt-2 break-all font-mono text-[10px] text-muted-foreground">Chunk {chunk.id} · SHA {chunk.content_hash}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 border-t border-border pt-5">
                  <h4 className="flex items-center gap-2 text-sm font-bold"><Search className="h-4 w-4" />Find replacement/additional evidence</h4>
                  <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_260px_auto]">
                    <input value={searchText} onChange={(event) => setSearchText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void searchEvidence(); }} placeholder="Medical term or short phrase" className="rounded-lg border border-border bg-background px-3 py-2 text-sm" />
                    <select value={searchSource} onChange={(event) => setSearchSource(event.target.value)} className="rounded-lg border border-border bg-background px-3 py-2 text-sm"><option value="">All three books</option>{sources.map((source) => <option key={source} value={source}>{source}</option>)}</select>
                    <Button variant="outline" disabled={saving || searchText.trim().length < 2} onClick={() => void searchEvidence()}>Search</Button>
                  </div>
                  <div className="mt-3 space-y-2">
                    {searchResults.map((chunk) => {
                      const added = draft.expected_chunk_ids.includes(chunk.id);
                      return <div key={chunk.id} className="flex items-start gap-3 rounded-lg border border-border p-3"><div className="min-w-0 flex-1"><p className="text-xs font-bold">{chunk.source_short_name} · {pageLabel(chunk)}</p><p className="mt-1 line-clamp-3 text-xs leading-5 text-muted-foreground">{chunk.content}</p></div><Button size="sm" variant={added ? 'secondary' : 'outline'} disabled={added} onClick={() => updateDraft({ expected_chunk_ids: [...draft.expected_chunk_ids, chunk.id] })}><Plus className="mr-1 h-3.5 w-3.5" />{added ? 'Added' : 'Add'}</Button></div>;
                    })}
                  </div>
                </div>
              </Card>
            )}

            <Card className="p-5">
              <label className="text-sm"><span className="mb-1 block font-semibold">Review notes</span><textarea rows={3} value={draft.notes} onChange={(event) => updateDraft({ notes: event.target.value })} placeholder="Why the selected evidence supports or does not support this prompt" className="w-full rounded-lg border border-border bg-background px-3 py-2" /></label>
              <label className="mt-4 flex items-start gap-3 rounded-xl border border-sky-500/25 bg-sky-500/5 p-3 text-sm"><input type="checkbox" checked={attested} disabled={dirty} onChange={(event) => setAttested(event.target.checked)} className="mt-1" /><span><strong>Human-review attestation</strong><span className="block text-xs text-muted-foreground">I inspected the complete selected chunk text and verified the prompt/label. This is not approval based on automated matching.</span></span></label>
            </Card>

            {selected.history.length > 0 && <Card className="p-5"><h3 className="flex items-center gap-2 font-bold"><History className="h-4 w-4" />Review history</h3><div className="mt-3 space-y-2">{selected.history.map((entry) => <div key={entry.id} className="rounded-lg border border-border p-3 text-xs"><div className="flex items-center gap-2"><Badge variant="outline">{entry.action}</Badge><ChevronRight className="h-3 w-3" /><time className="text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</time></div><p className="mt-2">{entry.notes}</p></div>)}</div></Card>}
          </div>
        )}
      </div>
    </div>
  );
}
