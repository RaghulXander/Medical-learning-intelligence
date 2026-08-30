export type OntologyNodeType =
  | 'ROOT'
  | 'DISCIPLINE'
  | 'METHOD_GROUP'
  | 'METHOD'
  | 'ANATOMIC_SYSTEM'
  | 'ORGAN'
  | 'ANATOMIC_SITE'
  | 'DISEASE_FAMILY'
  | 'DIAGNOSTIC_ENTITY'
  | 'MORPHOLOGIC_FEATURE'
  | 'CLINICAL_FEATURE'
  | 'GROSS_FEATURE'
  | 'IHC_MARKER'
  | 'MOLECULAR_ALTERATION'
  | 'GRADING_SYSTEM'
  | 'STAGING_SYSTEM'
  | 'LEARNING_OBJECTIVE';

export interface OntologyAlias {
  alias: string;
  alias_type: string;
  language: string;
  verification_status: string;
}

export interface OntologyNode {
  code: string;
  preferred_name: string;
  node_type: OntologyNodeType;
  parent_code: string | null;
  display_order: number;
  status: string;
  aliases?: OntologyAlias[];
}

export interface OntologySourceScope {
  title: string;
  edition: string;
  publisher: string;
  use: string;
  url: string;
  accessed_on: string;
}

export interface OntologyScheme {
  code: string;
  name: string;
  version: string;
  status: string;
  description: string;
  source_scope: OntologySourceScope[];
  copyright_note: string;
}

export interface OntologySeed {
  scheme: OntologyScheme;
  nodes: OntologyNode[];
}

export interface OntologyIndex {
  nodesByCode: Map<string, OntologyNode>;
  childrenByCode: Map<string, OntologyNode[]>;
  roots: OntologyNode[];
}
