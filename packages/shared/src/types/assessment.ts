/**
 * packages/shared/src/types/assessment.ts
 *
 * Universal Assessment Engine, Mock Exams, Runner State & Diagnostic Scoring Contracts.
 */

import { QuestionOption } from './question';

export type AssessmentType = 'MOCK' | 'SUBJECT' | 'TOPIC' | 'SUBTOPIC' | 'DAILY' | 'CUSTOM';
export type NavigationPolicy = 'FREE' | 'SECTION_LOCKED' | 'LINEAR';
export type AttemptStatus = 'IN_PROGRESS' | 'SUBMITTED' | 'TIMED_OUT' | 'ABANDONED';

export type PrometricQuestionState =
  | 'UNVISITED'
  | 'UNANSWERED'
  | 'ANSWERED'
  | 'MARKED_FOR_REVIEW'
  | 'ANSWERED_AND_MARKED';

export interface AssessmentPreset {
  id: string;
  title: string;
  type: AssessmentType;
  question_count: number;
  duration_seconds: number;
  marking_scheme_id: string;
  navigation_policy?: NavigationPolicy;
  description: string;
  tags?: string[];
  depth_level?: string;
  sections?: Array<{
    name: string;
    question_count: number;
    duration_seconds?: number;
  }>;
}

export interface SectionConfig {
  name: string;
  question_count: number;
  duration_seconds?: number;
  navigation_policy?: NavigationPolicy;
}

export interface CreateAssessmentPayload {
  title: string;
  type?: string;
  preset_id?: string;
  question_count?: number;
  duration_seconds?: number;
  marking_scheme_id?: string;
  navigation_policy?: string;
  blueprint?: Record<string, any>;
  sections?: SectionConfig[];
}

export interface SanitizedQuestion {
  sequence: number;
  question_id: string;
  section_id?: string | null;
  section_name?: string;
  stem: string;
  options: Record<string, string> | QuestionOption[];
  selected_answer?: string | null;
  marked_for_review?: boolean;
  status?: PrometricQuestionState | string;
  topic_name?: string;
  difficulty?: string;
  has_images?: boolean;
  image_assets?: Array<{
    image_id?: string;
    filename?: string;
    storage_uri?: string;
    cdn_url?: string;
    figure_label?: string;
    caption?: string;
    stain_type?: string;
    magnification?: string;
    [key: string]: any;
  }>;
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

export interface AttemptSectionInfo {
  id: string;
  section_order: number;
  name: string;
  question_count: number;
}

export interface AttemptStateResponse {
  attempt_id: string;
  assessment_id: string;
  title: string;
  type: string;
  status: AttemptStatus;
  total_questions: number;
  duration_seconds: number;
  time_spent_seconds: number;
  remaining_seconds: number;
  navigation_policy: string;
  sections: AttemptSectionInfo[];
  questions: SanitizedQuestion[];
}

export interface HeartbeatQuestionResponse {
  question_id: string;
  selected_answer?: string | null;
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

export interface TopicStatBreakdown {
  topic: string;
  total: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
}

export interface DifficultyStatBreakdown {
  difficulty: string;
  total: number;
  correct: number;
  incorrect: number;
  unanswered: number;
}

export interface MarkingSchemeInfo {
  name: string;
  correct_marks: number;
  penalty_marks: number;
}

export interface AttemptResults {
  attempt_id: string;
  assessment_id: string;
  title: string;
  status: AttemptStatus;
  started_at: string | null;
  submitted_at: string | null;
  score: number;
  max_score: number;
  percentage: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  attempted_count: number;
  accuracy: number;
  attempt_rate: number;
  negative_marks_lost: number;
  time_spent_seconds: number;
  avg_seconds_per_question: number;
  marking_scheme: MarkingSchemeInfo;
  topic_breakdown: TopicStatBreakdown[];
  difficulty_breakdown: DifficultyStatBreakdown[];
  weak_topics: string[];
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
  sequence: number;
  question_id: string;
  stem: string;
  options: Record<string, string> | QuestionOption[];
  selected_answer: string | null;
  correct_answer: string;
  is_correct: boolean | null;
  marks_awarded: number;
  time_spent_seconds: number;
  marked_for_review: boolean;
  explanation?: string;
  primary_topic_id?: string;
  difficulty?: string;
  source_exam_id?: string;
  external_source?: string;
  citations?: ReviewEvidenceItem[];
}

export interface AttemptReview {
  attempt_id: string;
  assessment_id: string;
  title: string;
  score: number;
  max_score: number;
  percentage: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  review_questions: ReviewQuestionItem[];
}
