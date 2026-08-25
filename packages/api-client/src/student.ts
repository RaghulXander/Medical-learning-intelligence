/**
 * packages/api-client/src/student.ts
 *
 * Student Hub, Daily Quiz, Mistake Review & Readiness API client.
 */

import { MedicalApiClient, defaultClient } from './client';
import {
  AnswerSyncItem,
  ContinueLearningResponse,
  DailyQuizResponse,
  ExamReadinessResponse,
  MistakeReviewResponse,
  UserProfile,
} from '@medical/shared';

export class StudentApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  public async updateOnboarding(payload: {
    target_exam?: string;
    target_year?: number;
    residency_stage?: string;
    medical_college?: string;
    primary_speciality?: string;
  }): Promise<UserProfile> {
    return this.client.request<UserProfile>('/api/student/onboarding', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async getDailyQuiz(): Promise<DailyQuizResponse> {
    return this.client.request<DailyQuizResponse>('/api/student/daily-quiz', {
      method: 'GET',
    });
  }

  public async getContinueLearning(): Promise<ContinueLearningResponse> {
    return this.client.request<ContinueLearningResponse>('/api/student/continue-learning', {
      method: 'GET',
    });
  }

  public async getExamReadiness(targetExam?: string): Promise<ExamReadinessResponse> {
    const query = targetExam ? `?target_exam=${encodeURIComponent(targetExam)}` : '';
    return this.client.request<ExamReadinessResponse>(`/api/student/readiness${query}`, {
      method: 'GET',
    });
  }

  public async getMistakes(options?: {
    topic_id?: string;
    repeated_only?: boolean;
    limit?: number;
  }): Promise<MistakeReviewResponse> {
    const params = new URLSearchParams();
    if (options?.topic_id) params.set('topic_id', options.topic_id);
    if (options?.repeated_only) params.set('repeated_only', 'true');
    if (options?.limit) params.set('limit', String(options.limit));
    const qs = params.toString() ? `?${params.toString()}` : '';

    return this.client.request<MistakeReviewResponse>(`/api/student/mistakes${qs}`, {
      method: 'GET',
    });
  }

  public async syncAnswers(attemptId: string, answers: AnswerSyncItem[]): Promise<{ success: boolean; attempt_id: string; synced_count: number }> {
    return this.client.request('/api/student/sync-answers', {
      method: 'POST',
      body: JSON.stringify({ attempt_id: attemptId, answers }),
    });
  }
}

export const studentApi = new StudentApi();
