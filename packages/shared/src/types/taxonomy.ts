/**
 * packages/shared/src/types/taxonomy.ts
 *
 * 3-Tier Decoupled Medical Taxonomy, Curriculum, and Course types.
 */

export interface MedicalSpecialty {
  id: string;
  name: string;
  code: string;
  description?: string;
}

export interface CurriculumTopic {
  id: string;
  specialty_id: string;
  name: string;
  code?: string;
  parent_topic_id?: string;
  subtopics?: CurriculumTopic[];
  question_count?: number;
}

export interface SpecialityNode {
  id: string;
  name: string;
  is_default?: boolean;
  description?: string;
}

export interface ExaminationNode {
  id: string;
  title: string;
  badge: string;
  category: 'super_specialty' | 'postgraduate' | 'undergraduate' | 'fellowship';
  description: string;
  has_specialities: boolean;
  default_speciality?: string;
  specialities: SpecialityNode[];
}

export interface ExperienceStageNode {
  id: string;
  label: string;
}

export interface MedicalTaxonomyMetadata {
  examinations: ExaminationNode[];
  experience_stages: ExperienceStageNode[];
  target_years: number[];
  metadata_version: string;
}
