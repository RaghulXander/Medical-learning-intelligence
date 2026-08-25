/**
 * apps/student-native/src/index.ts
 *
 * Mobile Native Shell & WebView Bridge for DocEdge Medical Exam Platform.
 * Provides typed contract helpers and direct WebView URL resolvers for iOS & Android wrappers.
 */

import { AssessmentPreset, CreateAssessmentPayload, AttemptResults } from '@medical/shared';
import { assessmentsApi } from '@medical/api-client';

export const DEFAULT_WEBVIEW_BASE_URL = 'http://localhost:3000';

export function getMobileExamSummary(preset: AssessmentPreset): string {
  return `[DocEdge Mobile] Loaded: ${preset.title} (${preset.question_count} MCQs, ${Math.round(preset.duration_seconds / 60)} mins)`;
}

export function getStudentExamUrl(attemptId: string, baseUrl = DEFAULT_WEBVIEW_BASE_URL): string {
  return `${baseUrl}/student/exam/${attemptId}`;
}

export function getStudentResultsUrl(attemptId: string, baseUrl = DEFAULT_WEBVIEW_BASE_URL): string {
  return `${baseUrl}/student/results/${attemptId}`;
}

export function getStudentReviewUrl(attemptId: string, baseUrl = DEFAULT_WEBVIEW_BASE_URL): string {
  return `${baseUrl}/student/review/${attemptId}`;
}

export async function launchMobileAssessment(
  payload: CreateAssessmentPayload,
  userId?: string
): Promise<{ attempt_id: string; exam_url: string }> {
  const assessment = await assessmentsApi.createAssessment(payload);
  const attempt = await assessmentsApi.startAttempt(assessment.assessment_id, userId);
  return {
    attempt_id: attempt.attempt_id,
    exam_url: getStudentExamUrl(attempt.attempt_id),
  };
}

export async function fetchAttemptResults(attemptId: string): Promise<AttemptResults> {
  return assessmentsApi.getResults(attemptId);
}
