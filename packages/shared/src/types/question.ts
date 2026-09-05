/**
 * packages/shared/src/types/question.ts
 *
 * Unified Question and Option definitions for the Medical Exam AI Platform.
 */

export type QuestionStatus =
  | 'IMPORTED'
  | 'GENERATED'
  | 'AI_REVIEW'
  | 'HUMAN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'REPORTED'
  | 'RETIRED';

export type CognitiveLevel = 'recall' | 'understanding' | 'application' | 'analysis';
export type DifficultyLevel = 'easy' | 'medium' | 'hard' | 'very_hard';
export type QuestionType = 'single_best_answer' | 'multiple_choice' | 'case_based';

export interface QuestionOption {
  key: string; // "A", "B", "C", "D"
  text: string;
}

export interface QuestionEvidenceCitation {
  id?: string;
  source_id?: string;
  source_title: string;
  author?: string;
  edition?: string;
  chapter?: string;
  page_range?: string;
  evidence_text?: string;
  verification_status: 'AI_SUGGESTED' | 'HUMAN_VERIFIED' | 'REJECTED';
}

export interface Question {
  id: string;
  external_source?: string;
  external_source_id?: string;
  content_hash?: string;
  duplicate_cluster_id?: string;
  
  // Decoupled Medical Taxonomy
  specialty: string;
  subject: string;
  primary_topic_id?: string;
  topic_name_original?: string;
  topic_name_normalized?: string;
  topic_mapping_status?: 'UNMAPPED' | 'RAW_ONLY' | 'MAPPED';
  
  // MCQ Stem & Options
  stem: string;
  options: QuestionOption[];
  correct_option: string; // "A" | "B" | "C" | "D"
  explanation?: string;
  learning_objective?: string;
  
  // Metadata & Status
  difficulty: DifficultyLevel;
  cognitive_level: CognitiveLevel;
  question_type: QuestionType;
  status: QuestionStatus;
  quality_score?: number;
  
  // Citations & Provenance
  citations?: QuestionEvidenceCitation[];
  source_exam_name?: string;
  source_exam_year?: number;
  
  created_at?: string;
  updated_at?: string;
}

export interface QuestionEditPayload {
  expected_updated_at: string;
  stem: string;
  options: QuestionOption[];
  correct_option: string;
  explanation?: string | null;
  difficulty: DifficultyLevel;
  cognitive_level: CognitiveLevel;
  question_type: QuestionType;
  primary_topic_id?: string | null;
  learning_objective?: string | null;
  edit_notes?: string | null;
}

export interface QuestionRevision {
  id: string;
  revision_number: number;
  editor_id?: string | null;
  changed_fields: string[];
  edit_notes?: string | null;
  snapshot: Record<string, unknown>;
  created_at: string;
}
