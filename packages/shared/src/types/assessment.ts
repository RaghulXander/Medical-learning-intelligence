/**
 * packages/shared/src/types/assessment.ts
 *
 * Types for Universal Assessment Engine, Mock Exams, Runner State & Scoring.
 */

import { QuestionOption } from './question';

export type AssessmentType = 'MOCK' | 'TOPIC_TEST' | 'DAILY_DOSE' | 'GRAND_TEST' | 'CUSTOM';
export type NavigationPolicy = 'FREE' | 'SECTION_TIMED' | 'FORWARD_ONLY';
export type AttemptStatus = 'IN_PROGRESS' | 'SUBMITTED' | 'EXPIRED' | 'ABANDONED';

export interface AssessmentPreset {
  id: string;
  title: string;
  type: AssessmentType;
  question_count: number;
  duration_seconds: number;
  marking_scheme_id: string;
  description: string;
  tags: string[];
}

export interface SectionConfig {
  name: string;
  question_count: number;
  duration_seconds?: number;
  navigation_policy?: NavigationPolicy;
}

export interface CreateAssessmentPayload {
  title: string;
  type: AssessmentType;
  question_count: number;
  duration_seconds: number;
  marking_scheme_id: string;
  navigation_policy?: NavigationPolicy;
  blueprint?: Record<string, any>;
  sections?: SectionConfig[];
}

export interface SanitizedQuestion {
  question_id: string;
  item_order: number;
  section_name?: string;
  stem: string;
  options: QuestionOption[];
  question_type: string;
  topic_name?: string;
  difficulty?: string;
}

export interface StartAttemptResponse {
  attempt_id: string;
  assessment_id: string;
  status: AttemptStatus;
  started_at: string;
  duration_seconds: number;
  total_questions: number;
  navigation_policy: NavigationPolicy;
  questions: SanitizedQuestion[];
}

export interface HeartbeatQuestionResponse {
  question_id: string;
  selected_answer: string | null;
  marked_for_review?: boolean;
  time_spent_seconds?: number;
}

export interface HeartbeatPayload {
  responses: HeartbeatQuestionResponse[];
  elapsed_seconds?: number;
}

export interface SubmitAttemptPayload {
  responses?: HeartbeatQuestionResponse[];
  final_elapsed_seconds?: number;
}

export interface TopicBreakdown {
  topic_id: string;
  topic_name: string;
  total: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
}

export interface AttemptResults {
  attempt_id: string;
  assessment_id: string;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string;
  total_questions: number;
  answered_questions: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  score: number;
  max_score: number;
  percentage: number;
  time_spent_seconds: number;
  accuracy: number;
  topic_breakdown: TopicBreakdown[];
}

export interface ReviewEvidenceItem {
  source_title: string;
  author?: string;
  edition?: string;
  chapter?: string;
  page_range?: string;
  evidence_text?: string;
  verification_status: 'AI_SUGGESTED' | 'HUMAN_VERIFIED' | 'REJECTED';
}

export interface ReviewQuestionItem {
  question_id: string;
  item_order: number;
  stem: string;
  options: QuestionOption[];
  user_selected_answer: string | null;
  correct_answer: string;
  is_correct: boolean;
  is_marked_for_review: boolean;
  time_spent_seconds: number;
  explanation?: string;
  topic_name?: string;
  difficulty?: string;
  citations: ReviewEvidenceItem[];
}

export interface AttemptReview {
  attempt_id: string;
  assessment_id: string;
  title: string;
  score: number;
  max_score: number;
  percentage: number;
  questions: ReviewQuestionItem[];
}
