'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowDown, ArrowLeft, ArrowUp, Plus, Save, ShieldAlert } from 'lucide-react';
import { ApiError, mobileUiApi } from '@medical/api-client';
import {
  MobileScreenDocument,
  MobileWidget,
  MobileWidgetType,
  mobileScreenDocumentSchema,
} from '@medical/shared';
import { SchemaFieldEditor } from '@/components/editor/schema-field-editor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/lib/auth-context';
import { cloneJson, JsonObject, setJsonPath } from '@/lib/editor/json';
import {
  createMobileWidget,
  mobileWidgetFields,
  mobileWidgetLabels,
} from '@/lib/mobile-ui/editor-schema';

export default function MobileLayoutEditorPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [draft, setDraft] = useState<MobileScreenDocument | null>(null);
  const [original, setOriginal] = useState<MobileScreenDocument | null>(null);
  const [version, setVersion] = useState<number | null>(null);
  const [source, setSource] = useState<'database' | 'bundled'>('bundled');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [addType, setAddType] = useState<MobileWidgetType>('goal_progress');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';
  const parsed = useMemo(() => mobileScreenDocumentSchema.safeParse(draft), [draft]);
  const widgets = parsed.success
    ? [...parsed.data.widgets].sort((left, right) => left.order - right.order)
    : [];
  const active = widgets.find((widget) => widget.id === activeId) ?? widgets[0];
  const changed = Boolean(draft && original && JSON.stringify(draft) !== JSON.stringify(original));

  useEffect(() => {
    if (!isAdmin) {
      if (!authLoading) setLoading(false);
      return;
    }
    mobileUiApi.getScreenForEditing('home')
      .then((response) => {
        const document = mobileScreenDocumentSchema.parse(response.document);
        setDraft(cloneJson(document));
        setOriginal(cloneJson(document));
        setVersion(response.version);
        setSource(response.source);
        setActiveId([...document.widgets].sort((a, b) => a.order - b.order)[0]?.id ?? null);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : 'Could not load mobile layout'))
      .finally(() => setLoading(false));
  }, [authLoading, isAdmin]);

  const replaceWidgets = (next: MobileWidget[]) => {
    if (!draft) return;
    setDraft({
      ...draft,
      widgets: next.map((widget, index) => ({ ...widget, order: (index + 1) * 10 })),
    });
  };

  const updateWidget = (id: string, updater: (widget: MobileWidget) => MobileWidget) => {
    replaceWidgets(widgets.map((widget) => widget.id === id ? updater(widget) : widget));
  };

  const moveWidget = (id: string, direction: -1 | 1) => {
    const currentIndex = widgets.findIndex((widget) => widget.id === id);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= widgets.length) return;
    const reordered = [...widgets];
    const [moved] = reordered.splice(currentIndex, 1);
    if (!moved) return;
    reordered.splice(nextIndex, 0, moved);
    replaceWidgets(reordered);
  };

  const publish = async () => {
    if (!parsed.success) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const response = await mobileUiApi.publishScreen('home', parsed.data, version, notes || undefined);
      setVersion(response.version);
      setDraft(cloneJson(response.document));
      setOriginal(cloneJson(response.document));
      setNotes('');
      setSource('database');
      setMessage(`Mobile home layout version ${response.version} published.`);
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 409
          ? 'A newer layout exists. Reload before publishing.'
          : caught instanceof Error ? caught.message : 'Publish failed'
      );
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || loading) {
    return <div className="min-h-[60vh] grid place-items-center text-foreground/80">Loading mobile layout…</div>;
  }
  if (!isAdmin) {
    return <div className="min-h-[60vh] grid place-items-center"><Card className="glass-card p-8 text-center"><ShieldAlert className="mx-auto mb-3 text-amber-300" /><p className="text-foreground">Mobile layout administrator access required.</p></Card></div>;
  }
  if (!draft) return <div className="p-8 text-red-300">{error ?? 'Layout unavailable'}</div>;

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/admin" className="mb-2 inline-flex items-center gap-1 text-xs text-sky-300"><ArrowLeft className="h-3 w-3" />Admin</Link>
          <h1 className="text-3xl font-bold text-foreground">Native Home Layout</h1>
          <div className="mt-2 flex gap-2"><Badge variant="secondary">Source: {source}</Badge><Badge variant="outline">Version: {version ?? 'bundled'}</Badge>{changed && <Badge variant="verified">Unpublished changes</Badge>}</div>
        </div>
        <Button variant="gradient" disabled={!changed || saving || !parsed.success} onClick={() => void publish()}><Save className="mr-2 h-4 w-4" />{saving ? 'Publishing…' : 'Publish mobile layout'}</Button>
      </div>

      {message && <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{message}</div>}
      {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>}
      {!parsed.success && <div className="mb-4 whitespace-pre-wrap rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">{parsed.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('\n')}</div>}

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="glass-card h-fit p-3">
          <div className="space-y-2">
            {widgets.map((widget, index) => (
              <button key={widget.id} type="button" onClick={() => setActiveId(widget.id)} className={`w-full rounded-lg border p-3 text-left ${active?.id === widget.id ? 'border-sky-500/50 bg-sky-500/10' : 'border-border'}`}>
                <div className="flex justify-between text-sm font-semibold text-foreground"><span>{mobileWidgetLabels[widget.type]}</span><span>{widget.enabled ? 'On' : 'Off'}</span></div>
                <div className="mt-2 flex gap-2"><span onClick={(event) => { event.stopPropagation(); moveWidget(widget.id, -1); }} className={index === 0 ? 'opacity-30' : ''}><ArrowUp className="h-3 w-3" /></span><span onClick={(event) => { event.stopPropagation(); moveWidget(widget.id, 1); }} className={index === widgets.length - 1 ? 'opacity-30' : ''}><ArrowDown className="h-3 w-3" /></span></div>
              </button>
            ))}
          </div>
          <div className="mt-4 flex gap-2 border-t border-border pt-4">
            <select value={addType} onChange={(event) => setAddType(event.target.value as MobileWidgetType)} className="min-w-0 flex-1 rounded bg-background text-xs text-foreground">{(Object.keys(mobileWidgetLabels) as MobileWidgetType[]).map((type) => <option key={type} value={type}>{mobileWidgetLabels[type]}</option>)}</select>
            <Button size="sm" variant="outline" onClick={() => { const widget = createMobileWidget(addType, (widgets.length + 1) * 10); replaceWidgets([...widgets, widget]); setActiveId(widget.id); }}><Plus className="h-4 w-4" /></Button>
          </div>
        </Card>

        <div className="space-y-6">
          {active && (
            <Card className="glass-card p-5">
              <div className="mb-5 flex justify-between border-b border-border pb-4"><div><h2 className="text-xl font-bold text-foreground">{mobileWidgetLabels[active.type]}</h2><p className="text-xs text-muted-foreground">{active.id}</p></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => updateWidget(active.id, (widget) => ({ ...widget, enabled: !widget.enabled }))}>{active.enabled ? 'Hide' : 'Show'}</Button><Button size="sm" variant="destructive" disabled={widgets.length <= 1} onClick={() => replaceWidgets(widgets.filter((widget) => widget.id !== active.id))}>Remove</Button></div></div>
              <div className="mb-5 grid gap-4 sm:grid-cols-3">
                <label className="text-xs text-foreground/80">Audience<select value={active.audience} onChange={(event) => updateWidget(active.id, (widget) => ({ ...widget, audience: event.target.value as MobileWidget['audience'] }))} className="mt-1 w-full rounded bg-background p-2 text-foreground"><option value="ALL">All</option><option value="AUTHENTICATED">Authenticated</option><option value="FREE">Free</option><option value="SUBSCRIBED">Subscribed</option></select></label>
                <label className="text-xs text-foreground/80">Platform<select value={active.platforms[0]} onChange={(event) => updateWidget(active.id, (widget) => ({ ...widget, platforms: [event.target.value as 'ALL' | 'IOS' | 'ANDROID'] }))} className="mt-1 w-full rounded bg-background p-2 text-foreground"><option value="ALL">All</option><option value="IOS">iOS</option><option value="ANDROID">Android</option></select></label>
                <label className="text-xs text-foreground/80">Rollout %<input type="number" min="0" max="100" value={active.rolloutPercentage} onChange={(event) => updateWidget(active.id, (widget) => ({ ...widget, rolloutPercentage: Number(event.target.value) }))} className="mt-1 w-full rounded bg-background p-2 text-foreground" /></label>
              </div>
              <SchemaFieldEditor value={cloneJson(active.props) as unknown as JsonObject} fields={mobileWidgetFields[active.type]} onChange={(path, value) => { const props = setJsonPath(cloneJson(active.props) as unknown as JsonObject, path, value); updateWidget(active.id, (widget) => ({ ...widget, props } as MobileWidget)); }} />
            </Card>
          )}
          <Card className="glass-card p-5"><label className="text-xs font-semibold text-foreground/80">Publication notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-2 w-full rounded bg-background p-3 text-sm text-foreground" /></label><p className="mt-3 text-xs text-muted-foreground">The app renders only precompiled widget types. Invalid configuration uses the bundled fallback layout.</p></Card>
        </div>
      </div>
    </div>
  );
}
