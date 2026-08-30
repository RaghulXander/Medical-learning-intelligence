'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronRight,
  CircleDot,
  ExternalLink,
  FolderTree,
  GitBranch,
  Microscope,
  Network,
  Search,
  Tags,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import {
  countOntologyDescendants,
  createOntologyIndex,
  findVisibleOntologyCodes,
  formatOntologyNodeType,
  getOntologyPath,
  ONTOLOGY_NODE_TYPES,
} from '@/lib/ontology/tree';
import type {
  OntologyIndex,
  OntologyNode,
  OntologyNodeType,
  OntologySeed,
} from '@/lib/ontology/types';

interface PathologyOntologyExplorerProps {
  ontology: OntologySeed;
}

interface TreeNodeProps {
  node: OntologyNode;
  index: OntologyIndex;
  depth: number;
  expandedCodes: Set<string>;
  visibleCodes: Set<string>;
  selectedCode: string;
  filtersActive: boolean;
  onSelect: (code: string) => void;
  onToggle: (code: string) => void;
}

const TYPE_ACCENTS: Partial<Record<OntologyNodeType, string>> = {
  ROOT: 'text-sky-300 bg-sky-500/15 border-sky-500/30',
  DISCIPLINE: 'text-indigo-300 bg-indigo-500/15 border-indigo-500/30',
  METHOD_GROUP: 'text-cyan-300 bg-cyan-500/15 border-cyan-500/30',
  METHOD: 'text-cyan-200 bg-cyan-500/10 border-cyan-500/20',
  ANATOMIC_SYSTEM: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/30',
  ORGAN: 'text-teal-300 bg-teal-500/15 border-teal-500/30',
  ANATOMIC_SITE: 'text-lime-300 bg-lime-500/10 border-lime-500/25',
  DISEASE_FAMILY: 'text-amber-300 bg-amber-500/15 border-amber-500/30',
  DIAGNOSTIC_ENTITY: 'text-rose-300 bg-rose-500/15 border-rose-500/30',
};

function NodeTypeBadge({ nodeType }: { nodeType: OntologyNodeType }) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide',
        TYPE_ACCENTS[nodeType] ?? 'border-white/10 bg-white/[0.04] text-slate-300',
      )}
    >
      {formatOntologyNodeType(nodeType)}
    </span>
  );
}

function TreeNode({
  node,
  index,
  depth,
  expandedCodes,
  visibleCodes,
  selectedCode,
  filtersActive,
  onSelect,
  onToggle,
}: TreeNodeProps) {
  const children = (index.childrenByCode.get(node.code) ?? []).filter((child) =>
    visibleCodes.has(child.code),
  );
  const autoExpanded = filtersActive && children.length > 0;
  const isExpanded = expandedCodes.has(node.code) || autoExpanded;
  const hasChildren = children.length > 0;

  return (
    <div role="treeitem" aria-expanded={hasChildren ? isExpanded : undefined}>
      <div
        className={cn(
          'group flex items-center gap-1 rounded-xl border transition-colors',
          selectedCode === node.code
            ? 'border-sky-500/40 bg-sky-500/10'
            : 'border-transparent hover:border-white/[0.08] hover:bg-white/[0.035]',
        )}
        style={{ marginLeft: Math.min(depth, 5) * 12 }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggle(node.code)}
            aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${node.preferred_name}`}
            disabled={autoExpanded}
            className="flex h-9 w-8 shrink-0 items-center justify-center text-slate-500 transition-colors hover:text-white disabled:cursor-default disabled:opacity-30"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="flex h-9 w-8 shrink-0 items-center justify-center" aria-hidden="true">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />
          </span>
        )}
        <button
          type="button"
          onClick={() => onSelect(node.code)}
          className="flex min-w-0 flex-1 items-center justify-between gap-3 py-2 pr-2 text-left"
        >
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-slate-100">
              {node.preferred_name}
            </span>
            <span className="block truncate font-mono text-[10px] text-slate-500">
              {node.code}
            </span>
          </span>
          <NodeTypeBadge nodeType={node.node_type} />
        </button>
      </div>
      {hasChildren && isExpanded ? (
        <div role="group" className="mt-0.5 space-y-0.5">
          {children.map((child) => (
            <TreeNode
              key={child.code}
              node={child}
              index={index}
              depth={depth + 1}
              expandedCodes={expandedCodes}
              visibleCodes={visibleCodes}
              selectedCode={selectedCode}
              filtersActive={filtersActive}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function PathologyOntologyExplorer({ ontology }: PathologyOntologyExplorerProps) {
  const [query, setQuery] = useState('');
  const [nodeType, setNodeType] = useState<OntologyNodeType | 'ALL'>('ALL');
  const [selectedCode, setSelectedCode] = useState('SP-BREAST');
  const [expandedCodes, setExpandedCodes] = useState(
    () => new Set(['PATH', 'SP', 'SP-BREAST', 'SP-BREAST-EPITHELIAL']),
  );

  const index = useMemo(() => createOntologyIndex(ontology.nodes), [ontology.nodes]);
  const visibleCodes = useMemo(
    () => findVisibleOntologyCodes(ontology.nodes, index, query, nodeType),
    [index, nodeType, ontology.nodes, query],
  );
  const filtersActive = Boolean(query.trim()) || nodeType !== 'ALL';
  const selectedNode = index.nodesByCode.get(selectedCode) ?? index.roots[0];

  useEffect(() => {
    if (selectedNode && visibleCodes.has(selectedNode.code)) return;
    const firstVisibleNode = ontology.nodes.find((node) => visibleCodes.has(node.code));
    if (firstVisibleNode) setSelectedCode(firstVisibleNode.code);
  }, [ontology.nodes, selectedNode, visibleCodes]);

  const typeCounts = useMemo(() => {
    const counts = new Map<OntologyNodeType, number>();
    for (const node of ontology.nodes) {
      counts.set(node.node_type, (counts.get(node.node_type) ?? 0) + 1);
    }
    return counts;
  }, [ontology.nodes]);

  const selectedPath = selectedNode ? getOntologyPath(selectedNode, index) : [];
  const selectedChildren = selectedNode
    ? index.childrenByCode.get(selectedNode.code) ?? []
    : [];
  const descendantCount = selectedNode
    ? countOntologyDescendants(selectedNode.code, index)
    : 0;
  const overviewStats: Array<{ label: string; value: number; icon: LucideIcon }> = [
    { label: 'Total nodes', value: ontology.nodes.length, icon: Network },
    { label: 'Organ systems', value: typeCounts.get('ANATOMIC_SYSTEM') ?? 0, icon: FolderTree },
    { label: 'Diagnostic entities', value: typeCounts.get('DIAGNOSTIC_ENTITY') ?? 0, icon: Microscope },
    {
      label: 'Aliases',
      value: ontology.nodes.reduce((sum, node) => sum + (node.aliases?.length ?? 0), 0),
      icon: Tags,
    },
  ];

  const toggleNode = (code: string) => {
    setExpandedCodes((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-8 lg:py-14">
      <section className="relative mb-8 overflow-hidden rounded-3xl border border-white/[0.08] bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950/60 p-6 sm:p-8">
        <div className="absolute right-[-5rem] top-[-6rem] h-64 w-64 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="relative">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge variant="warning" className="gap-1.5">
              <AlertTriangle className="h-3 w-3" />
              Editorial draft
            </Badge>
            <Badge variant="outline">Version {ontology.scheme.version}</Badge>
          </div>
          <div className="max-w-3xl">
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-sky-400">
              Milestone 14 · Knowledge architecture
            </p>
            <h1 className="text-3xl font-black tracking-tight text-white sm:text-5xl">
              Surgical Pathology Ontology
            </h1>
            <p className="mt-4 text-sm leading-6 text-slate-300 sm:text-base">
              Browse the current topic hierarchy from organ systems to the initial
              Breast diagnostic-entity slice. This is an editorial preview, not a
              released clinical classification or verified question mapping.
            </p>
          </div>
          <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overviewStats.map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-white/[0.08] bg-white/[0.035] p-4">
                <Icon className="mb-3 h-4 w-4 text-sky-400" />
                <p className="text-2xl font-black text-white">{value}</p>
                <p className="mt-1 text-xs text-slate-400">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.8fr)]">
        <Card className="overflow-hidden bg-slate-900/65">
          <div className="border-b border-white/[0.08] p-4 sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="relative flex-1">
                <span className="sr-only">Search ontology nodes</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name, code, or alias…"
                  className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/70 pl-10 pr-3 text-sm text-white outline-none transition focus:border-sky-500/50 focus:ring-2 focus:ring-sky-500/10"
                />
              </label>
              <label>
                <span className="sr-only">Filter by node type</span>
                <select
                  value={nodeType}
                  onChange={(event) => setNodeType(event.target.value as OntologyNodeType | 'ALL')}
                  className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 text-sm text-slate-200 outline-none focus:border-sky-500/50 sm:w-56"
                >
                  <option value="ALL">All node types</option>
                  {ONTOLOGY_NODE_TYPES.filter((type) => typeCounts.has(type)).map((type) => (
                    <option key={type} value={type}>
                      {formatOntologyNodeType(type)} ({typeCounts.get(type)})
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
              <span>{visibleCodes.size} visible nodes including parent branches</span>
              {filtersActive ? (
                <button
                  type="button"
                  onClick={() => {
                    setQuery('');
                    setNodeType('ALL');
                  }}
                  className="font-semibold text-sky-400 hover:text-sky-300"
                >
                  Clear filters
                </button>
              ) : null}
            </div>
          </div>
          <div className="max-h-[760px] overflow-y-auto p-3 sm:p-4" role="tree" aria-label="Surgical Pathology ontology">
            {visibleCodes.size > 0 ? (
              <div className="space-y-0.5">
                {index.roots
                  .filter((root) => visibleCodes.has(root.code))
                  .map((root) => (
                    <TreeNode
                      key={root.code}
                      node={root}
                      index={index}
                      depth={0}
                      expandedCodes={expandedCodes}
                      visibleCodes={visibleCodes}
                      selectedCode={selectedCode}
                      filtersActive={filtersActive}
                      onSelect={setSelectedCode}
                      onToggle={toggleNode}
                    />
                  ))}
              </div>
            ) : (
              <div className="flex min-h-52 flex-col items-center justify-center text-center">
                <Search className="mb-3 h-7 w-7 text-slate-600" />
                <p className="font-semibold text-slate-300">No ontology nodes found</p>
                <p className="mt-1 text-xs text-slate-500">Try a broader term or clear the type filter.</p>
              </div>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          {selectedNode ? (
            <Card className="sticky top-24 overflow-hidden bg-slate-900/80">
              <div className="border-b border-white/[0.08] bg-white/[0.025] p-5">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <NodeTypeBadge nodeType={selectedNode.node_type} />
                  <Badge variant="warning" className="text-[10px]">{selectedNode.status}</Badge>
                </div>
                <h2 className="text-xl font-bold leading-snug text-white">
                  {selectedNode.preferred_name}
                </h2>
                <p className="mt-2 font-mono text-xs text-sky-400">{selectedNode.code}</p>
              </div>
              <div className="space-y-5 p-5">
                <div>
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Hierarchy
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-300">
                    {selectedPath.map((pathNode, indexPosition) => (
                      <span key={pathNode.code} className="contents">
                        {indexPosition > 0 ? <ChevronRight className="h-3 w-3 text-slate-600" /> : null}
                        <button
                          type="button"
                          onClick={() => setSelectedCode(pathNode.code)}
                          className="rounded-md bg-white/[0.04] px-2 py-1 hover:bg-white/[0.08] hover:text-white"
                        >
                          {pathNode.preferred_name}
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
                    <GitBranch className="mb-2 h-4 w-4 text-indigo-400" />
                    <p className="text-lg font-bold text-white">{selectedChildren.length}</p>
                    <p className="text-[11px] text-slate-500">Direct children</p>
                  </div>
                  <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
                    <CircleDot className="mb-2 h-4 w-4 text-emerald-400" />
                    <p className="text-lg font-bold text-white">{descendantCount}</p>
                    <p className="text-[11px] text-slate-500">All descendants</p>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Aliases and synonyms
                  </p>
                  {selectedNode.aliases?.length ? (
                    <div className="space-y-2">
                      {selectedNode.aliases.map((alias) => (
                        <div key={`${alias.language}-${alias.alias}`} className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-semibold text-slate-200">{alias.alias}</span>
                            <Badge variant="suggested" className="text-[9px]">{alias.verification_status}</Badge>
                          </div>
                          <p className="mt-1 text-[10px] text-slate-500">{alias.alias_type} · {alias.language}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No aliases are recorded for this node.</p>
                  )}
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      </div>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-sky-400" />
            <h2 className="font-bold text-white">Structural source scope</h2>
          </div>
          <div className="space-y-3">
            {ontology.scheme.source_scope.map((source) => (
              <a
                key={source.url}
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-xl border border-white/[0.08] bg-white/[0.025] p-4 transition hover:border-sky-500/30 hover:bg-sky-500/[0.04]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{source.title}</p>
                    <p className="mt-1 text-xs text-slate-400">{source.edition} · {source.publisher}</p>
                  </div>
                  <ExternalLink className="h-4 w-4 shrink-0 text-slate-500" />
                </div>
                <p className="mt-3 text-xs leading-5 text-slate-500">{source.use}</p>
              </a>
            ))}
          </div>
        </Card>
        <Card className="border-amber-500/20 bg-amber-500/[0.035] p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2 text-amber-300">
            <AlertTriangle className="h-5 w-5" />
            <h2 className="font-bold">What this preview does not mean</h2>
          </div>
          <ul className="space-y-3 text-sm leading-6 text-slate-300">
            <li>• Node names and hierarchy are not diagnostic evidence.</li>
            <li>• AI-suggested aliases are not human-verified terminology.</li>
            <li>• Question mappings and feature relationships are not shown because review is still pending.</li>
            <li>• No textbook prose, tables, figures, or protected images are included.</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}
