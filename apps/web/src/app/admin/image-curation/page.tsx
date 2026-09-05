'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Image as ImageIcon, RefreshCw, Save, ShieldAlert, XCircle } from 'lucide-react';
import { adminApi, ApiError } from '@medical/api-client';
import { ImageReviewAsset, ImageReviewAssetListItem, ImageReviewSummary, SaveImageReview } from '@medical/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/lib/auth-context';
import { cn } from '@/lib/utils';

const utilityClasses = [
  'PATHOLOGY_MICROSCOPY', 'GROSS_PATHOLOGY', 'IHC_OR_SPECIAL_STAIN',
  'CYTOLOGY_OR_HEMATOLOGY', 'MEDICAL_DIAGRAM', 'CHART_OR_GRAPH',
  'TABLE_OR_TEXT_FIGURE', 'MULTI_PANEL_FIGURE', 'LOGO_ICON_OR_DECORATION',
  'PAGE_FRAGMENT_OR_RULE', 'BLANK_OR_NEAR_BLANK', 'DUPLICATE', 'UNKNOWN_REVIEW_REQUIRED',
];

type Draft = Omit<SaveImageReview, 'expected_revision' | 'attested'>;

function draftFrom(asset: ImageReviewAsset): Draft {
  const occurrence = asset.occurrences[0];
  const compatible = asset.links.find((link) =>
    occurrence && link.source_short_name === occurrence.source_short_name && link.pdf_page === occurrence.pdf_page
  );
  return {
    utility_class: asset.reviewed_utility_class || asset.triage_class,
    diagnosis: asset.reviewed_diagnosis || '', stain: asset.reviewed_stain || '',
    magnification: asset.reviewed_magnification || '', caption: asset.reviewed_caption || '',
    occurrence_id: compatible?.occurrence_id || occurrence?.id || null,
    link_id: compatible?.id || null, notes: asset.history[0]?.notes || '',
  };
}

export default function ImageCurationPage() {
  const { user, isLoading: authLoading } = useAuth();
  const canReview = ['SUPER_ADMIN', 'ADMIN'].includes(user?.role ?? '');
  const [summary, setSummary] = useState<ImageReviewSummary | null>(null);
  const [assets, setAssets] = useState<ImageReviewAssetListItem[]>([]);
  const [totalAssets, setTotalAssets] = useState(0);
  const [selected, setSelected] = useState<ImageReviewAsset | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [utilityFilter, setUtilityFilter] = useState('');
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [queuePage, setQueuePage] = useState(1);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [attested, setAttested] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadQueue = useCallback(async (showLoader = true) => {
    if (!canReview) { if (showLoader) setLoading(false); return; }
    if (showLoader) setLoading(true);
    try {
      const [nextSummary, page] = await Promise.all([
        adminApi.getImageReviewSummary(),
        adminApi.listImageReviewAssets({ curation_status: statusFilter || undefined, utility_class: utilityFilter || undefined, pilot_shortlisted: shortlistOnly || undefined, page: queuePage, limit: 50 }),
      ]);
      setSummary(nextSummary); setAssets(page.items); setTotalAssets(page.total); setError(null);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not load image queue'); }
    finally { if (showLoader) setLoading(false); }
  }, [canReview, queuePage, shortlistOnly, statusFilter, utilityFilter]);

  useEffect(() => { if (!authLoading) void loadQueue(); }, [authLoading, loadQueue]);
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  const openAsset = async (id: string) => {
    setSaving(true); setError(null); setMessage(null); setImageUrl(null);
    try {
      const item = await adminApi.getImageReviewAsset(id);
      setSelected(item); setDraft(draftFrom(item)); setDirty(false); setAttested(false);
      try {
        const blob = await adminApi.getImageContent(id);
        setImageUrl(URL.createObjectURL(blob));
      } catch (caught) {
        setError(`Metadata loaded, but image preview failed: ${caught instanceof Error ? caught.message : 'unknown error'}`);
      }
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not open image'); }
    finally { setSaving(false); }
  };

  const compatibleLinks = useMemo(() => {
    if (!selected || !draft?.occurrence_id) return [];
    const occurrence = selected.occurrences.find((item) => item.id === draft.occurrence_id);
    return selected.links.filter((link) =>
      occurrence && link.source_short_name === occurrence.source_short_name && link.pdf_page === occurrence.pdf_page
    );
  }, [draft?.occurrence_id, selected]);

  const updateDraft = (change: Partial<Draft>) => {
    setDraft((current) => current ? { ...current, ...change } : current);
    setDirty(true); setAttested(false);
  };

  const payload = (): SaveImageReview | null => selected && draft ? {
    ...draft, expected_revision: selected.review_revision, attested,
  } : null;

  const persist = async (action?: Parameters<typeof adminApi.decideImageReview>[1]) => {
    const body = payload(); if (!selected || !body) return;
    if (body.notes.trim().length < 3) { setError('Add concise review notes first.'); return; }
    if (action && !attested) { setError('Human-review attestation is required.'); return; }
    setSaving(true); setError(null); setMessage(null);
    try {
      const item = action
        ? await adminApi.decideImageReview(selected.id, action, body)
        : await adminApi.saveImageReview(selected.id, body);
      setSelected(item); setDraft(draftFrom(item)); setDirty(false); setAttested(false);
      setMessage(action ? 'Human decision recorded with an immutable audit snapshot.' : 'Draft saved.');
      void loadQueue(false);
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409
        ? 'Another reviewer changed this image. Reopen it before saving.'
        : caught instanceof Error ? caught.message : 'Could not save image review');
    } finally { setSaving(false); }
  };

  if (authLoading || loading) return <div className="grid min-h-[60vh] place-items-center text-muted-foreground">Loading image curation…</div>;
  if (!canReview) return <div className="grid min-h-[60vh] place-items-center"><Card className="p-8 text-center"><ShieldAlert className="mx-auto mb-3 text-amber-400" /><p>Administrator media permission required.</p></Card></div>;

  return <div className="mx-auto max-w-[1700px] space-y-5 px-4 py-6 sm:px-6">
    {summary && <Card className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-bold">Private pathology image catalog</h2><p className="mt-1 text-sm text-muted-foreground">{summary.total_assets} assets · exact occurrence + evidence verification required</p></div><div className="flex gap-2"><Badge variant="success">{summary.eligible_question_assets}/30 pilot eligible</Badge><Badge variant={summary.pilot_gate_open ? 'success' : 'warning'}>{summary.pilot_gate_open ? 'Pilot gate open' : 'Pilot blocked'}</Badge></div></div></Card>}
    {message && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{message}</div>}
    {error && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}
    <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <Card className="overflow-hidden"><div className="space-y-2 border-b border-border p-4"><div className="flex items-center gap-2"><select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setQueuePage(1); }} className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2 py-2 text-xs"><option value="">All statuses</option><option value="CURATED_VALID">Unreviewed catalog</option><option value="HUMAN_REVIEW">Draft review</option><option value="APPROVED_INTERNAL_STUDY">Study approved</option><option value="APPROVED_INTERNAL_QUESTION_CANDIDATE">Question approved</option><option value="REJECTED_NON_EDUCATIONAL">Non-educational</option><option value="REJECTED_UNUSABLE_QUALITY">Poor quality</option><option value="PROVENANCE_UNRESOLVED">Unresolved provenance</option></select><Button size="icon" variant="ghost" onClick={() => void loadQueue()}><RefreshCw className="h-4 w-4" /></Button></div><select value={utilityFilter} onChange={(e) => { setUtilityFilter(e.target.value); setQueuePage(1); }} className="w-full rounded-lg border border-border bg-background px-2 py-2 text-xs"><option value="">All utility classes</option>{utilityClasses.map((item) => <option key={item}>{item}</option>)}</select><label className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs"><input type="checkbox" checked={shortlistOnly} onChange={(e) => { setShortlistOnly(e.target.checked); setQueuePage(1); }} /><span>Pilot shortlist only</span></label><div className="flex items-center justify-between text-xs text-muted-foreground"><Button size="sm" variant="ghost" disabled={queuePage === 1} onClick={() => setQueuePage((value) => Math.max(1, value - 1))}>Previous</Button><span>Page {queuePage} · {totalAssets} assets</span><Button size="sm" variant="ghost" disabled={queuePage * 50 >= totalAssets} onClick={() => setQueuePage((value) => value + 1)}>Next</Button></div></div><div className="max-h-[calc(100vh-400px)] overflow-y-auto">{assets.map((item) => <button key={item.id} type="button" onClick={() => void openAsset(item.id)} className={cn('w-full border-b border-border p-4 text-left hover:bg-muted/50', selected?.id === item.id && 'bg-sky-500/10')}><div className="flex items-center justify-between gap-2"><span className="truncate text-xs font-bold">{item.filename}</span><Badge variant={item.verified_link_count ? 'success' : 'suggested'}>{item.verified_link_count} links</Badge></div><p className="mt-2 text-xs text-muted-foreground">{item.source_short_name || 'Unknown source'} · PDF {item.pdf_page ?? '—'} · {item.width}×{item.height}</p><div className="mt-1 flex items-center justify-between gap-2 text-xs"><span>{item.reviewed_utility_class || item.automated_suggested_utility_class || item.triage_class}</span>{item.automated_rank_score != null && <span className="font-mono text-sky-400">{item.automated_rank_score.toFixed(1)}</span>}</div></button>)}</div></Card>
      {!selected || !draft ? <Card className="grid min-h-[600px] place-items-center p-10 text-center text-muted-foreground"><div><ImageIcon className="mx-auto mb-3 h-10 w-10" /><p>Select an image to review.</p></div></Card> : <div className="space-y-5">
        <Card className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold">{selected.filename}</h3><p className="text-xs text-muted-foreground">SHA {selected.sha256.slice(0, 12)}… · {selected.rights_status} · storage {selected.storage_access_status} · revision {selected.review_revision}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={saving || !dirty} onClick={() => void persist()}><Save className="mr-2 h-4 w-4" />Save draft</Button><Button variant="outline" disabled={saving || !attested} onClick={() => void persist('approve-study')}>Approve study</Button><Button variant="gradient" disabled={saving || !attested} onClick={() => void persist('approve-question')}><CheckCircle2 className="mr-2 h-4 w-4" />Approve for questions</Button></div></div><div className="mt-5 grid gap-5 lg:grid-cols-2"><div className="grid min-h-80 place-items-center overflow-hidden rounded-xl border border-border bg-black/80">{imageUrl ? <img src={imageUrl} alt="Private pathology review asset" className="max-h-[560px] w-full object-contain" /> : <RefreshCw className="animate-spin text-muted-foreground" />}</div><div className="space-y-3"><label className="block text-sm"><span className="mb-1 block font-semibold">Utility class</span><select value={draft.utility_class} onChange={(e) => updateDraft({ utility_class: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2">{utilityClasses.map((item) => <option key={item}>{item}</option>)}</select></label><label className="block text-sm"><span className="mb-1 block font-semibold">Diagnosis</span><input value={draft.diagnosis || ''} onChange={(e) => updateDraft({ diagnosis: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2" /></label><div className="grid grid-cols-2 gap-2"><label className="text-sm"><span className="mb-1 block font-semibold">Stain</span><input value={draft.stain || ''} onChange={(e) => updateDraft({ stain: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2" /></label><label className="text-sm"><span className="mb-1 block font-semibold">Magnification</span><input value={draft.magnification || ''} onChange={(e) => updateDraft({ magnification: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2" /></label></div><label className="block text-sm"><span className="mb-1 block font-semibold">Reviewed caption</span><textarea rows={4} value={draft.caption || ''} onChange={(e) => updateDraft({ caption: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2" /></label></div></div></Card>
        <Card className="p-5"><h3 className="font-bold">Exact provenance and evidence</h3><div className="mt-3 grid gap-3 md:grid-cols-2"><label className="text-sm"><span className="mb-1 block font-semibold">Image occurrence</span><select value={draft.occurrence_id || ''} onChange={(e) => updateDraft({ occurrence_id: e.target.value, link_id: null })} className="w-full rounded-lg border border-border bg-background p-2"><option value="">Select occurrence</option>{selected.occurrences.map((item) => <option key={item.id} value={item.id}>{item.source_short_name} · PDF {item.pdf_page ?? '—'} · {item.figure_label || 'unlabelled'}</option>)}</select></label><label className="text-sm"><span className="mb-1 block font-semibold">Same-page text link</span><select value={draft.link_id || ''} onChange={(e) => updateDraft({ link_id: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2"><option value="">Select evidence</option>{compatibleLinks.map((item) => <option key={item.id} value={item.id}>{item.section_heading || 'Chunk'} · PDF {item.pdf_page ?? '—'}</option>)}</select></label></div>{compatibleLinks.find((item) => item.id === draft.link_id) && <p className="mt-4 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-xl bg-muted/40 p-4 text-sm leading-6">{compatibleLinks.find((item) => item.id === draft.link_id)?.content}</p>}</Card>
        <Card className="p-5"><label className="block text-sm"><span className="mb-1 block font-semibold">Review notes</span><textarea rows={3} value={draft.notes} onChange={(e) => updateDraft({ notes: e.target.value })} className="w-full rounded-lg border border-border bg-background p-2" /></label><label className="mt-4 flex items-start gap-3 rounded-xl border border-sky-500/25 bg-sky-500/5 p-3 text-sm"><input type="checkbox" checked={attested} onChange={(e) => setAttested(e.target.checked)} className="mt-1" /><span><strong>Human-review attestation</strong><span className="block text-xs text-muted-foreground">I inspected the image, exact occurrence, and complete selected evidence. Entered diagnosis/caption metadata is verified from the book context, not inferred from appearance alone.</span></span></label><div className="mt-4 flex flex-wrap gap-2"><Button variant="destructive" disabled={saving || !attested} onClick={() => void persist('reject-non-educational')}><XCircle className="mr-2 h-4 w-4" />Non-educational</Button><Button variant="destructive" disabled={saving || !attested} onClick={() => void persist('reject-quality')}>Poor quality</Button><Button variant="outline" disabled={saving || !attested} onClick={() => void persist('provenance-unresolved')}>Provenance unresolved</Button></div></Card>
      </div>}
    </div>
  </div>;
}
