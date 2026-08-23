/**
 * packages/api-client/src/assessments.ts
 *
 * Universal Assessment Engine endpoints.
 */

import {
  AssessmentPreset,
  CreateAssessmentPayload,
  HeartbeatPayload,
  StartAttemptResponse,
  SubmitAttemptPayload,
  AttemptResults,
  AttemptReview,
} from '@medical/shared';
import { MedicalApiClient, defaultClient } from './client';

export class AssessmentsApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  /**
   * List 1-click exam presets (NEET-SS, NEET-PG, INI-CET, Daily Dose, etc.)
   */
  async listPresets(): Promise<AssessmentPreset[]> {
    return this.client.request<AssessmentPreset[]>('/api/assessments/presets');
  }

  /**
   * Generate an assessment from blueprint parameters
   */
  async createAssessment(payload: CreateAssessmentPayload): Promise<{
    status: string;
    assessment_id: string;
    title: string;
    type: string;
    question_count: number;
    duration_seconds: number;
    marking_scheme_id: string;
  }> {
    return this.client.request('/api/assessments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Start an assessment attempt (returns sanitized questions)
   */
  async startAttempt(
    assessmentId: string,
    userId?: string
  ): Promise<StartAttemptResponse> {
    return this.client.request<StartAttemptResponse>(
      `/api/assessments/${assessmentId}/start`,
      {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
      }
    );
  }

  /**
   * Get current state of an in-progress attempt
   */
  async getAttemptState(attemptId: string): Promise<{
    attempt_id: string;
    assessment_id: string;
    status: string;
    started_at: string;
    duration_seconds: number;
    total_questions: number;
    navigation_policy: string;
    questions: any[];
    responses: any[];
    elapsed_seconds: number;
  }> {
    return this.client.request(`/api/assessments/attempts/${attemptId}`);
  }

  /**
   * Background heartbeat sync
   */
  async recordHeartbeat(
    attemptId: string,
    payload: HeartbeatPayload
  ): Promise<{ status: string; synced_count: number }> {
    return this.client.request(`/api/assessments/attempts/${attemptId}/heartbeat`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Submit attempt for scoring
   */
  async submitAttempt(
    attemptId: string,
    payload?: SubmitAttemptPayload
  ): Promise<{
    status: string;
    attempt_id: string;
    score: number;
    max_score: number;
    percentage: number;
    correct_count: number;
    incorrect_count: number;
    unanswered_count: number;
  }> {
    return this.client.request(`/api/assessments/attempts/${attemptId}/submit`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  }

  /**
   * Get diagnostic results & topic breakdown
   */
  async getResults(attemptId: string): Promise<AttemptResults> {
    return this.client.request<AttemptResults>(
      `/api/assessments/attempts/${attemptId}/results`
    );
  }

  /**
   * Get complete question-by-question review with explanations & citations
   */
  async getReview(attemptId: string): Promise<AttemptReview> {
    return this.client.request<AttemptReview>(
      `/api/assessments/attempts/${attemptId}/review`
    );
  }
}

export const assessmentsApi = new AssessmentsApi();
