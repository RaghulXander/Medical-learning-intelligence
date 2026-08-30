import type {
  OntologyIndex,
  OntologyNode,
  OntologyNodeType,
} from './types';

export const ONTOLOGY_NODE_TYPES: OntologyNodeType[] = [
  'ROOT',
  'DISCIPLINE',
  'METHOD_GROUP',
  'METHOD',
  'ANATOMIC_SYSTEM',
  'ORGAN',
  'ANATOMIC_SITE',
  'DISEASE_FAMILY',
  'DIAGNOSTIC_ENTITY',
  'MORPHOLOGIC_FEATURE',
  'CLINICAL_FEATURE',
  'GROSS_FEATURE',
  'IHC_MARKER',
  'MOLECULAR_ALTERATION',
  'GRADING_SYSTEM',
  'STAGING_SYSTEM',
  'LEARNING_OBJECTIVE',
];

function compareNodes(left: OntologyNode, right: OntologyNode): number {
  return (
    left.display_order - right.display_order ||
    left.preferred_name.localeCompare(right.preferred_name)
  );
}

export function createOntologyIndex(nodes: OntologyNode[]): OntologyIndex {
  const nodesByCode = new Map(nodes.map((node) => [node.code, node]));
  const childrenByCode = new Map<string, OntologyNode[]>();
  const roots: OntologyNode[] = [];

  for (const node of nodes) {
    if (!node.parent_code || !nodesByCode.has(node.parent_code)) {
      roots.push(node);
      continue;
    }
    const children = childrenByCode.get(node.parent_code) ?? [];
    children.push(node);
    childrenByCode.set(node.parent_code, children);
  }

  roots.sort(compareNodes);
  for (const children of childrenByCode.values()) children.sort(compareNodes);
  return { nodesByCode, childrenByCode, roots };
}

export function formatOntologyNodeType(nodeType: OntologyNodeType): string {
  return nodeType
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function nodeMatchesQuery(node: OntologyNode, normalizedQuery: string): boolean {
  if (!normalizedQuery) return true;
  return [
    node.code,
    node.preferred_name,
    ...(node.aliases?.map((alias) => alias.alias) ?? []),
  ].some((value) => value.toLocaleLowerCase().includes(normalizedQuery));
}

export function findVisibleOntologyCodes(
  nodes: OntologyNode[],
  index: OntologyIndex,
  query: string,
  nodeType: OntologyNodeType | 'ALL',
): Set<string> {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery && nodeType === 'ALL') {
    return new Set(nodes.map((node) => node.code));
  }

  const visibleCodes = new Set<string>();
  for (const node of nodes) {
    if (
      (nodeType === 'ALL' || node.node_type === nodeType) &&
      nodeMatchesQuery(node, normalizedQuery)
    ) {
      let cursor: OntologyNode | undefined = node;
      while (cursor) {
        visibleCodes.add(cursor.code);
        cursor = cursor.parent_code
          ? index.nodesByCode.get(cursor.parent_code)
          : undefined;
      }
    }
  }
  return visibleCodes;
}

export function getOntologyPath(
  node: OntologyNode,
  index: OntologyIndex,
): OntologyNode[] {
  const path: OntologyNode[] = [];
  let cursor: OntologyNode | undefined = node;
  while (cursor) {
    path.unshift(cursor);
    cursor = cursor.parent_code
      ? index.nodesByCode.get(cursor.parent_code)
      : undefined;
  }
  return path;
}

export function countOntologyDescendants(
  code: string,
  index: OntologyIndex,
): number {
  const children = index.childrenByCode.get(code) ?? [];
  return children.reduce(
    (total, child) => total + 1 + countOntologyDescendants(child.code, index),
    0,
  );
}
