import { describe, expect, test } from 'bun:test';
import ontologySeed from '../data/ontology/surgical-pathology-2026.08-draft.1.json';
import {
  countOntologyDescendants,
  createOntologyIndex,
  findVisibleOntologyCodes,
  getOntologyPath,
} from '../apps/web/src/lib/ontology/tree';
import type { OntologySeed } from '../apps/web/src/lib/ontology/types';

const ontology = ontologySeed as OntologySeed;
const index = createOntologyIndex(ontology.nodes);

describe('pathology ontology explorer tree', () => {
  test('builds the versioned hierarchy in editorial order', () => {
    expect(index.roots.map((node) => node.code)).toEqual(['PATH']);
    expect(index.childrenByCode.get('PATH')?.map((node) => node.code)).toEqual(['SP']);
    expect(index.childrenByCode.get('SP-BREAST-INVASIVE')?.[0]?.code).toBe('SP-BREAST-IBC-NST');
  });

  test('keeps ancestors visible when searching by an alias', () => {
    const visible = findVisibleOntologyCodes(ontology.nodes, index, 'DCIS', 'ALL');
    expect(visible.has('SP-BREAST-DCIS')).toBe(true);
    expect(visible.has('SP-BREAST-IN-SITU')).toBe(true);
    expect(visible.has('SP-BREAST')).toBe(true);
    expect(visible.has('SP-GI')).toBe(false);
  });

  test('filters diagnostic entities while preserving their parent branches', () => {
    const visible = findVisibleOntologyCodes(ontology.nodes, index, '', 'DIAGNOSTIC_ENTITY');
    expect(visible.has('SP-BREAST-PHYLLODES')).toBe(true);
    expect(visible.has('SP-BREAST-FIBROEPITHELIAL')).toBe(true);
    expect(visible.has('SP-PRINCIPLES')).toBe(false);
  });

  test('provides paths and descendant counts for the detail panel', () => {
    const dcis = index.nodesByCode.get('SP-BREAST-DCIS');
    expect(dcis).toBeDefined();
    expect(getOntologyPath(dcis!, index).map((node) => node.code)).toEqual([
      'PATH',
      'SP',
      'SP-BREAST',
      'SP-BREAST-EPITHELIAL',
      'SP-BREAST-IN-SITU',
      'SP-BREAST-DCIS',
    ]);
    expect(countOntologyDescendants('SP-BREAST-IN-SITU', index)).toBe(3);
  });
});
