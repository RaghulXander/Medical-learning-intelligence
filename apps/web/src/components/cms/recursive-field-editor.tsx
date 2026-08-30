'use client';

export type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
export interface JsonObject { [key: string]: JsonValue }

interface RecursiveFieldEditorProps {
  value: JsonValue;
  path?: Array<string | number>;
  onChange: (path: Array<string | number>, value: JsonValue) => void;
}

function labelFor(key: string | number): string {
  if (typeof key === 'number') return `Item ${key + 1}`;
  return key.replace(/([A-Z])/g, ' $1').replaceAll('_', ' ').replace(/^./, (value) => value.toUpperCase());
}

function emptyCopy(value: JsonValue): JsonValue {
  if (typeof value === 'string') return '';
  if (typeof value === 'number') return 0;
  if (typeof value === 'boolean') return false;
  if (Array.isArray(value)) return [];
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, emptyCopy(item)]));
  }
  return null;
}

export function RecursiveFieldEditor({ value, path = [], onChange }: RecursiveFieldEditorProps) {
  if (Array.isArray(value)) {
    return (
      <div className="space-y-3">
        {value.map((item, index) => (
          <div key={index} className="rounded-lg border border-white/10 bg-slate-950/30 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">Item {index + 1}</span>
              <button
                type="button"
                disabled={value.length <= 1}
                onClick={() => onChange(path, value.filter((_, itemIndex) => itemIndex !== index))}
                className="text-xs text-red-300 hover:text-red-200 disabled:cursor-not-allowed disabled:opacity-30"
              >
                Remove
              </button>
            </div>
            <RecursiveFieldEditor value={item} path={[...path, index]} onChange={onChange} />
          </div>
        ))}
        <button
          type="button"
          disabled={value.length === 0}
          onClick={() => value.length > 0 && onChange(path, [...value, emptyCopy(value[0] ?? null)])}
          className="rounded-md border border-sky-500/30 px-3 py-1.5 text-xs text-sky-300 disabled:opacity-40"
        >
          Add item
        </button>
      </div>
    );
  }

  if (value && typeof value === 'object') {
    return (
      <div className="space-y-4">
        {Object.entries(value).map(([key, item]) => (
          <div key={key}>
            <label className="mb-1.5 block text-xs font-semibold text-slate-300">{labelFor(key)}</label>
            <RecursiveFieldEditor value={item} path={[...path, key]} onChange={onChange} />
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === 'boolean') {
    return (
      <button
        type="button"
        onClick={() => onChange(path, !value)}
        className={`rounded-full px-3 py-1 text-xs font-semibold ${value ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-700 text-slate-300'}`}
      >
        {value ? 'Enabled' : 'Disabled'}
      </button>
    );
  }

  if (typeof value === 'number') {
    return (
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(path, Number(event.target.value))}
        className="w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white"
      />
    );
  }

  const stringValue = value ?? '';
  const fieldName = String(path[path.length - 1] ?? '');
  if (fieldName === 'action') {
    return (
      <select value={stringValue} onChange={(event) => onChange(path, event.target.value)} className="w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white">
        <option value="START_DIAGNOSTIC">Start diagnostic</option>
        <option value="OPEN_STUDENT_HUB">Open student hub</option>
        <option value="OPEN_SIGNUP">Open signup</option>
        <option value="CONTACT">Contact</option>
      </select>
    );
  }
  if (fieldName === 'icon') {
    return (
      <select value={stringValue} onChange={(event) => onChange(path, event.target.value)} className="w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white">
        <option value="microscope">Microscope</option>
        <option value="zap">Lightning</option>
        <option value="shield-check">Verified shield</option>
        <option value="brain-circuit">Brain circuit</option>
        <option value="book-open">Open book</option>
      </select>
    );
  }
  const multiline = typeof stringValue === 'string' && stringValue.length > 100;
  return multiline ? (
    <textarea
      value={stringValue}
      rows={4}
      onChange={(event) => onChange(path, event.target.value)}
      className="w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white"
    />
  ) : (
    <input
      type={fieldName === 'email' ? 'email' : 'text'}
      value={stringValue}
      onChange={(event) => onChange(path, event.target.value)}
      className="w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white"
    />
  );
}
