/**
 * packages/shared/src/types/student.ts
 *
 * Student Personalization, Daily Quiz, Mistake Review, and Readiness Types.
 */

export interface DailyQuizResponse {
  date: string;
  title: string;
  question_count: number;
  current_streak: number;
  longest_streak: number;
  questions: Array<{
    id: string;
    stem: string;
    options: Array<{ key: string; text: string }>;
    difficulty: string;
    primary_topic_id?: string | null;
  }>;
}

export interface ResumableAttempt {
  attempt_id: string;
  assessment_id: string;
  assessment_title: string;
  started_at?: string | null;
  answered_count: number;
  total_questions: number;
}

export interface WeakTopicRecommendation {
  curriculum_node_id: string;
  topic_name: string;
  smoothed_accuracy: number;
  attempted_count: number;
  incorrect_count: number;
  remediation_blueprint: {
    topic_id: string;
    question_count: number;
    assessment_mode: string;
  };
}

export interface ContinueLearningResponse {
  resumable_attempts: ResumableAttempt[];
  weak_topic_recommendations: WeakTopicRecommendation[];
}

export interface ExamReadinessResponse {
  readiness_score: number;
  breakdown: {
    curriculum_coverage_pct: number;
    topics_covered: number;
    total_topics: number;
    average_accuracy_pct: number;
    mock_average_pct: number;
  };
  rating: 'EXCELLENT' | 'GOOD' | 'NEEDS_FOCUS';
}

export interface MistakeReviewItem {
  question_id: string;
  stem: string;
  options: Array<{ key: string; text: string }>;
  correct_option: string;
  explanation?: string | null;
  error_count: number;
  last_selected_answer?: string | null;
  last_failed_at?: string | null;
  primary_topic_id?: string | null;
}

export interface MistakeReviewResponse {
  total_mistakes: number;
  mistakes: MistakeReviewItem[];
  remediation_blueprint: {
    question_ids: string[];
    question_count: number;
    assessment_mode: string;
  };
}

export interface AnswerSyncItem {
  question_id: string;
  selected_answer?: string | null;
  time_spent_seconds?: number;
  client_timestamp?: string | null;
}
