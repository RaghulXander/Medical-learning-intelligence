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
  AttemptStateResponse,
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
  async startAttempt(assessmentId: string): Promise<StartAttemptResponse> {
    return this.client.request<StartAttemptResponse>(
      `/api/assessments/${assessmentId}/start`,
      {
        method: 'POST',
      }
    );
  }

  /**
   * Get current state of an in-progress attempt
   */
  async getAttemptState(attemptId: string): Promise<AttemptStateResponse> {
    return this.client.request<AttemptStateResponse>(`/api/assessments/attempts/${attemptId}`);
  }

  /**
   * Background heartbeat sync
   */
  async recordHeartbeat(
    attemptId: string,
    payload: HeartbeatPayload
  ): Promise<{
    status: string;
    attempt_id: string;
    time_spent_seconds: number;
    answered_count: number;
    unanswered_count: number;
  }> {
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
  ): Promise<AttemptResults> {
    return this.client.request<AttemptResults>(`/api/assessments/attempts/${attemptId}/submit`, {
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
   * Launch a 1-click preset exam attempt directly
   */
  async launchPreset(presetId: string): Promise<StartAttemptResponse> {
    const assessment = await this.createAssessment({
      title: `${presetId.toUpperCase()} Assessment`,
      preset_id: presetId,
      type: 'MOCK',
    });
    return this.startAttempt(assessment.assessment_id);
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
