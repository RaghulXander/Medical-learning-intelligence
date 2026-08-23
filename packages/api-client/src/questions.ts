/**
 * packages/api-client/src/questions.ts
 *
 * Question Bank API endpoints for search, filtering, and editorial curation.
 */

import { Question, QuestionStatus } from '@medical/shared';
import { MedicalApiClient, defaultClient } from './client';

export interface ListQuestionsParams {
  search?: string;
  topic?: string;
  status?: string;
  difficulty?: string;
  cognitive_level?: string;
  limit?: number;
  offset?: number;
}

export interface ListQuestionsResponse {
  total: number;
  limit: number;
  offset: number;
  items: Question[];
}

export interface TopicCountItem {
  name: string;
  count: number;
}

export class QuestionsApi {
  constructor(private client: MedicalApiClient = defaultClient) {}

  /**
   * List unique normalized topics with question counts
   */
  async listTopics(): Promise<TopicCountItem[]> {
    return this.client.request<TopicCountItem[]>('/api/questions/topics');
  }

  /**
   * Search and filter questions
   */
  async listQuestions(params?: ListQuestionsParams): Promise<ListQuestionsResponse> {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.topic && params.topic !== 'ALL') query.set('topic', params.topic);
    if (params?.status && params.status !== 'ALL') query.set('status', params.status);
    if (params?.difficulty && params.difficulty !== 'ALL') query.set('difficulty', params.difficulty);
    if (params?.cognitive_level && params.cognitive_level !== 'ALL') query.set('cognitive_level', params.cognitive_level);
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());

    const qs = query.toString();
    return this.client.request<ListQuestionsResponse>(`/api/questions${qs ? `?${qs}` : ''}`);
  }

  /**
   * Get single question details
   */
  async getQuestion(questionId: string): Promise<Question> {
    return this.client.request<Question>(`/api/questions/${questionId}`);
  }

  /**
   * Transition question editorial status
   */
  async updateStatus(
    questionId: string,
    newStatus: QuestionStatus,
    notes?: string
  ): Promise<{ status: string; question_id: string; new_status: string }> {
    return this.client.request(`/api/questions/${questionId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus, notes }),
    });
  }

  /**
   * Update question content
   */
  async updateQuestion(
    questionId: string,
    payload: Partial<Question>
  ): Promise<{ status: string; question_id: string; updated: boolean }> {
    return this.client.request(`/api/questions/${questionId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }
}

export const questionsApi = new QuestionsApi();
