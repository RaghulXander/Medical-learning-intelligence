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

export interface Course {
  id: string;
  name: string;
  code: string; // e.g. "NEET_PG", "NEET_SS_ONCOPATH", "INI_CET", "MBBS_PATH"
  level: 'undergraduate' | 'postgraduate' | 'super_specialty';
  description?: string;
}
