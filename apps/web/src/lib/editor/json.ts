export type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
export interface JsonObject { [key: string]: JsonValue }

export function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function setJsonPath(root: JsonObject, path: Array<string | number>, value: JsonValue): JsonObject {
  if (path.length === 0) return value as JsonObject;
  const copy = cloneJson(root);
  let cursor: JsonValue = copy;
  for (const key of path.slice(0, -1)) {
    if (Array.isArray(cursor) && typeof key === 'number') cursor = cursor[key] ?? null;
    else if (cursor && !Array.isArray(cursor) && typeof cursor === 'object') cursor = cursor[String(key)] ?? null;
    else throw new Error('Invalid editor field path');
  }
  const finalKey = path[path.length - 1];
  if (Array.isArray(cursor) && typeof finalKey === 'number') cursor[finalKey] = value;
  else if (cursor && !Array.isArray(cursor) && typeof cursor === 'object' && finalKey !== undefined) cursor[String(finalKey)] = value;
  else throw new Error('Invalid editor field target');
  return copy;
}
