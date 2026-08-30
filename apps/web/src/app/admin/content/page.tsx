'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowDown, ArrowLeft, ArrowUp, Eye, FileJson, Plus, Save, ShieldAlert } from 'lucide-react';
import { cmsApi, ApiError } from '@medical/api-client';
import { LandingPageRenderer } from '@/components/cms/landing-page-renderer';
import { SchemaFieldEditor } from '@/components/editor/schema-field-editor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/lib/auth-context';
import { createSection, widgetLabels } from '@/lib/cms/registry';
import { landingWidgetFields } from '@/lib/cms/editor-schema';
import { cloneJson, JsonObject, JsonValue, setJsonPath } from '@/lib/editor/json';
import {
  LandingPageDocument,
  LandingSection,
  WidgetType,
  landingPageDocumentSchema,
} from '@/lib/cms/schema';

function toJsonObject(document: LandingPageDocument): JsonObject {
  return cloneJson(document) as unknown as JsonObject;
}

export default function CmsAdminPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [draft, setDraft] = useState<JsonObject | null>(null);
  const [original, setOriginal] = useState<JsonObject | null>(null);
  const [baseSha, setBaseSha] = useState<string | null>(null);
  const [source, setSource] = useState<'github' | 'local'>('local');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [addType, setAddType] = useState<WidgetType>('content_block');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';
  const parsedDraft = useMemo(() => landingPageDocumentSchema.safeParse(draft), [draft]);
  const hasChanges = Boolean(draft && original && JSON.stringify(draft) !== JSON.stringify(original));
  const sections = parsedDraft.success ? [...parsedDraft.data.sections].sort((a, b) => a.order - b.order) : [];
  const activeSection = sections.find((section) => section.id === activeId) ?? sections[0];

  useEffect(() => {
    if (!isAdmin) {
      if (!authLoading) setLoading(false);
      return;
    }
    cmsApi.getLandingPage()
      .then((response) => {
        const document = landingPageDocumentSchema.parse(response.document);
        const json = toJsonObject(document);
        setDraft(json);
        setOriginal(cloneJson(json));
        setBaseSha(response.sha);
        setSource(response.source);
        setActiveId(document.sections.sort((a, b) => a.order - b.order)[0]?.id ?? null);
      })
      .catch((error: unknown) => setErrorMessage(error instanceof Error ? error.message : 'Could not load CMS content'))
      .finally(() => setLoading(false));
  }, [authLoading, isAdmin]);

  const replaceSections = (nextSections: LandingSection[]) => {
    if (!draft) return;
    const ordered = nextSections.map((section, index) => ({ ...section, order: (index + 1) * 10 }));
    setDraft(setJsonPath(draft, ['sections'], cloneJson(ordered) as unknown as JsonValue));
  };

  const moveSection = (id: string, direction: -1 | 1) => {
    const currentIndex = sections.findIndex((section) => section.id === id);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= sections.length) return;
    const reordered = [...sections];
    const [moved] = reordered.splice(currentIndex, 1);
    if (!moved) return;
    reordered.splice(nextIndex, 0, moved);
    replaceSections(reordered);
  };

  const updateSection = (id: string, updater: (section: LandingSection) => LandingSection) => {
    replaceSections(sections.map((section) => section.id === id ? updater(section) : section));
  };

  const addSection = () => {
    const section = createSection(addType, (sections.length + 1) * 10);
    replaceSections([...sections, section]);
    setActiveId(section.id);
  };

  const publish = async () => {
    setErrorMessage(null);
    setStatusMessage(null);
    if (!parsedDraft.success) {
      setErrorMessage(parsedDraft.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('\n'));
      return;
    }
    setSaving(true);
    try {
      await cmsApi.validateLandingPage(parsedDraft.data);
      const response = await cmsApi.publishLandingPage(parsedDraft.data, baseSha);
      const document = landingPageDocumentSchema.parse(response.document);
      const json = toJsonObject(document);
      setDraft(json);
      setOriginal(cloneJson(json));
      setBaseSha(response.content_sha);
      setSource('github');
      setStatusMessage(`Published successfully${response.commit_sha ? ` — commit ${response.commit_sha.slice(0, 7)}` : ''}`);
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 409) {
        setErrorMessage('Another editor published newer content. Reload before publishing your changes.');
      } else {
        setErrorMessage(error instanceof Error ? error.message : 'Publishing failed');
      }
    } finally {
      setSaving(false);
    }
  };

  const exportJson = () => {
    if (!draft) return;
    const blob = new Blob([`${JSON.stringify(draft, null, 2)}\n`], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'landing-page.json';
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const importJson = async (file: File | undefined) => {
    if (!file) return;
    setErrorMessage(null);
    try {
      const candidate = JSON.parse(await file.text()) as unknown;
      const document = landingPageDocumentSchema.parse(candidate);
      setDraft(toJsonObject(document));
      setActiveId(document.sections.sort((a, b) => a.order - b.order)[0]?.id ?? null);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : 'The selected JSON file is invalid');
    }
  };

  if (authLoading || loading) return <div className="min-h-[60vh] grid place-items-center text-slate-300">Loading CMS…</div>;
  if (!isAdmin) return (
    <div className="min-h-[60vh] grid place-items-center p-6">
      <Card className="glass-card max-w-md p-8 text-center">
        <ShieldAlert className="mx-auto mb-4 h-10 w-10 text-amber-300" />
        <h1 className="text-xl font-bold text-white">CMS administrator access required</h1>
      </Card>
    </div>
  );
  if (!draft) return <div className="p-8 text-red-300">{errorMessage ?? 'Content unavailable'}</div>;

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/admin" className="mb-2 inline-flex items-center gap-1 text-xs text-sky-300"><ArrowLeft className="h-3 w-3" /> Admin</Link>
          <h1 className="text-3xl font-bold text-white">Landing Page CMS</h1>
          <div className="mt-2 flex gap-2"><Badge variant="secondary">Source: {source}</Badge><Badge variant={parsedDraft.success ? 'verified' : 'destructive'}>{parsedDraft.success ? 'Valid' : 'Invalid'}</Badge>{hasChanges && <Badge variant="outline">Unsaved changes</Badge>}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex h-10 cursor-pointer items-center rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/[0.08]">
            Import
            <input type="file" accept="application/json,.json" className="hidden" onChange={(event) => { void importJson(event.target.files?.[0]); event.target.value = ''; }} />
          </label>
          <Button variant="outline" onClick={exportJson}><FileJson className="mr-2 h-4 w-4" />Export</Button>
          <Button variant="outline" disabled={!hasChanges} onClick={() => original && setDraft(cloneJson(original))}>Reset</Button>
          <Button variant="gradient" disabled={!hasChanges || saving || !parsedDraft.success} onClick={publish}><Save className="mr-2 h-4 w-4" />{saving ? 'Saving & publishing…' : 'Save & publish'}</Button>
        </div>
      </div>

      {statusMessage && <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{statusMessage}</div>}
      {errorMessage && <div className="mb-4 whitespace-pre-wrap rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{errorMessage}</div>}

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="glass-card h-fit p-3">
          <div className="space-y-2">
            {sections.map((section, index) => (
              <button key={section.id} type="button" onClick={() => setActiveId(section.id)} className={`w-full rounded-lg border p-3 text-left ${activeSection?.id === section.id ? 'border-sky-500/50 bg-sky-500/10' : 'border-white/10 bg-slate-950/30'}`}>
                <div className="flex items-center justify-between"><span className="text-sm font-semibold text-white">{widgetLabels[section.type]}</span><span className={section.enabled ? 'text-emerald-300' : 'text-slate-500'}>{section.enabled ? 'On' : 'Off'}</span></div>
                <div className="mt-2 flex gap-1">
                  <span onClick={(event) => { event.stopPropagation(); moveSection(section.id, -1); }} className={`rounded border border-white/10 p-1 ${index === 0 ? 'opacity-30' : ''}`}><ArrowUp className="h-3 w-3" /></span>
                  <span onClick={(event) => { event.stopPropagation(); moveSection(section.id, 1); }} className={`rounded border border-white/10 p-1 ${index === sections.length - 1 ? 'opacity-30' : ''}`}><ArrowDown className="h-3 w-3" /></span>
                </div>
              </button>
            ))}
          </div>
          <div className="mt-4 flex gap-2 border-t border-white/10 pt-4">
            <select value={addType} onChange={(event) => setAddType(event.target.value as WidgetType)} className="min-w-0 flex-1 rounded-md border border-white/10 bg-slate-950 px-2 text-xs text-white">
              {(Object.keys(widgetLabels) as WidgetType[]).map((type) => <option key={type} value={type}>{widgetLabels[type]}</option>)}
            </select>
            <Button size="sm" variant="outline" onClick={addSection}><Plus className="h-4 w-4" /></Button>
          </div>
        </Card>

        <div className="space-y-6">
          {activeSection && (
            <Card className="glass-card p-5">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                <div><h2 className="text-xl font-bold text-white">{widgetLabels[activeSection.type]}</h2><p className="text-xs text-slate-400">{activeSection.id}</p></div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => updateSection(activeSection.id, (section) => ({ ...section, enabled: !section.enabled }))}>{activeSection.enabled ? 'Hide' : 'Show'}</Button>
                  <Button size="sm" variant="destructive" disabled={sections.length <= 1} onClick={() => { replaceSections(sections.filter((section) => section.id !== activeSection.id)); setActiveId(null); }}>Remove</Button>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-xs font-semibold text-slate-300">Audience<select value={activeSection.audience} onChange={(event) => updateSection(activeSection.id, (section) => ({ ...section, audience: event.target.value as LandingSection['audience'] }))} className="mt-1.5 w-full rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"><option value="ALL">Everyone</option><option value="GUEST">Guests</option><option value="AUTHENTICATED">Signed-in users</option></select></label>
              </div>
              <div className="mt-6">
                <SchemaFieldEditor
                  value={cloneJson(activeSection.props) as unknown as JsonObject}
                  fields={landingWidgetFields[activeSection.type]}
                  onChange={(path, value) => {
                    const props = setJsonPath(cloneJson(activeSection.props) as unknown as JsonObject, path, value);
                    updateSection(activeSection.id, (section) => ({ ...section, props } as LandingSection));
                  }}
                />
              </div>
            </Card>
          )}

          {parsedDraft.success && (
            <Card className="glass-card overflow-hidden">
              <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3 text-sm font-semibold text-white"><Eye className="h-4 w-4" />Live preview</div>
              <div className="max-h-[720px] overflow-y-auto bg-slate-950">
                <LandingPageRenderer document={parsedDraft.data} isAuthenticated={false} diagnosticLoading={false} onStartDiagnostic={() => setStatusMessage('Preview mode: diagnostic launch is disabled.')} />
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
