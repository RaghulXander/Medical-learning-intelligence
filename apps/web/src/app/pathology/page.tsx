import type { Metadata } from 'next';
import ontologySeed from '../../../../../data/ontology/surgical-pathology-2026.08-draft.1.json';
import { PathologyOntologyExplorer } from '@/components/ontology/pathology-ontology-explorer';
import type { OntologySeed } from '@/lib/ontology/types';

export const metadata: Metadata = {
  title: 'Surgical Pathology Ontology | DocEdge',
  description:
    'Browse the versioned DocEdge Surgical Pathology topic hierarchy and current Breast diagnostic-entity draft.',
};

export default function PathologyOntologyPage() {
  return (
    <div className="min-h-screen bg-slate-950">
      <PathologyOntologyExplorer ontology={ontologySeed as OntologySeed} />
    </div>
  );
}
