'use client';

import type { JsonObject, JsonValue } from '@/lib/editor/json';

export interface SelectOption { label: string; value: string }

export type FieldDefinition = {
  name: string;
  label: string;
  description?: string;
  required?: boolean;
} & (
  | { type: 'text' | 'textarea'; placeholder?: string }
  | { type: 'number'; min?: number; max?: number; step?: number }
  | { type: 'boolean' }
  | { type: 'select'; options: SelectOption[] }
  | { type: 'object'; fields: FieldDefinition[] }
  | { type: 'array'; item: FieldDefinition; minItems?: number; maxItems?: number; addLabel?: string }
);

interface SchemaFieldEditorProps {
  value: JsonObject;
  fields: FieldDefinition[];
  onChange: (path: Array<string | number>, value: JsonValue) => void;
  path?: Array<string | number>;
}

function emptyValue(field: FieldDefinition): JsonValue {
  switch (field.type) {
    case 'text':
    case 'textarea': return '';
    case 'select': return field.options[0]?.value ?? '';
    case 'number': return field.min ?? 0;
    case 'boolean': return false;
    case 'array': return [];
    case 'object': return Object.fromEntries(field.fields.map((child) => [child.name, emptyValue(child)]));
  }
}

function FieldControl({ field, value, path, onChange }: { field: FieldDefinition; value: JsonValue | undefined; path: Array<string | number>; onChange: SchemaFieldEditorProps['onChange'] }) {
  const controlClass = 'w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white';
  if (field.type === 'object') {
    const objectValue = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    return <SchemaFieldEditor value={objectValue} fields={field.fields} path={path} onChange={onChange} />;
  }
  if (field.type === 'array') {
    const items = Array.isArray(value) ? value : [];
    return <div className="space-y-3">
      {items.map((item, index) => <div key={index} className="rounded-lg border border-white/10 bg-slate-950/30 p-3">
        <div className="mb-2 flex items-center justify-between"><span className="text-xs font-semibold text-slate-300">Item {index + 1}</span><button type="button" disabled={items.length <= (field.minItems ?? 0)} onClick={() => onChange(path, items.filter((_, itemIndex) => itemIndex !== index))} className="text-xs text-red-300 disabled:opacity-30">Remove</button></div>
        <FieldControl field={field.item} value={item} path={[...path, index]} onChange={onChange} />
      </div>)}
      <button type="button" disabled={items.length >= (field.maxItems ?? Number.POSITIVE_INFINITY)} onClick={() => onChange(path, [...items, emptyValue(field.item)])} className="rounded-md border border-sky-500/30 px-3 py-1.5 text-xs text-sky-300 disabled:opacity-30">{field.addLabel ?? 'Add item'}</button>
    </div>;
  }
  if (field.type === 'boolean') return <button type="button" onClick={() => onChange(path, value !== true)} className={`rounded-full px-3 py-1 text-xs font-semibold ${value === true ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-700 text-slate-300'}`}>{value === true ? 'Enabled' : 'Disabled'}</button>;
  if (field.type === 'number') return <input className={controlClass} type="number" min={field.min} max={field.max} step={field.step} value={typeof value === 'number' ? value : field.min ?? 0} onChange={(event) => onChange(path, Number(event.target.value))} />;
  if (field.type === 'select') return <select className={controlClass} value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(path, event.target.value)}>{field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
  const stringValue = typeof value === 'string' ? value : '';
  return field.type === 'textarea'
    ? <textarea className={controlClass} rows={5} placeholder={field.placeholder} value={stringValue} onChange={(event) => onChange(path, event.target.value)} />
    : <input className={controlClass} type="text" placeholder={field.placeholder} value={stringValue} onChange={(event) => onChange(path, event.target.value)} />;
}

export function SchemaFieldEditor({ value, fields, onChange, path = [] }: SchemaFieldEditorProps) {
  return <div className="space-y-4">{fields.map((field) => <div key={field.name}>
    <label className="mb-1.5 block text-xs font-semibold text-slate-300">{field.label}{field.required ? ' *' : ''}</label>
    {field.description && <p className="mb-1.5 text-[11px] text-slate-500">{field.description}</p>}
    <FieldControl field={field} value={value[field.name]} path={[...path, field.name]} onChange={onChange} />
  </div>)}</div>;
}
