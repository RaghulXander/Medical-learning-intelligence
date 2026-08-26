/**
 * apps/mobile/lib/sync/draft-sync.ts
 *
 * Optimistic Answer Sync & Background Batching Queue.
 */

import { studentApi } from '@medical/api-client';
import { AnswerSyncItem } from '@medical/shared';

export interface QueuedAnswer {
  question_id: string;
  selected_answer: string;
  time_spent_seconds?: number;
  updated_at: number;
}

class DraftAnswerSyncQueue {
  private queue: Map<string, QueuedAnswer> = new Map();
  private syncTimer: any = null;
  private isSyncing = false;
  private currentAttemptId: string | null = null;

  setAttemptId(attemptId: string | null) {
    this.currentAttemptId = attemptId;
    this.queue.clear();
  }

  recordAnswer(questionId: string, selectedAnswer: string, timeSpentSeconds = 0) {
    this.queue.set(questionId, {
      question_id: questionId,
      selected_answer: selectedAnswer,
      time_spent_seconds: timeSpentSeconds,
      updated_at: Date.now(),
    });

    this.scheduleSync();
  }

  private scheduleSync() {
    if (this.syncTimer) clearTimeout(this.syncTimer);
    this.syncTimer = setTimeout(() => {
      this.flush();
    }, 1200); // 1.2s debounce for batch synchronization
  }

  async flush(): Promise<boolean> {
    if (!this.currentAttemptId || this.queue.size === 0 || this.isSyncing) {
      return true;
    }

    this.isSyncing = true;
    const answers: AnswerSyncItem[] = Array.from(this.queue.values()).map((a) => ({
      question_id: a.question_id,
      selected_answer: a.selected_answer,
      time_spent_seconds: a.time_spent_seconds || 15,
      client_timestamp: new Date().toISOString(),
    }));

    try {
      const res = await studentApi.syncAnswers(this.currentAttemptId, answers);
      if (res && res.success) {
        this.queue.clear();
      }
      return true;
    } catch (err) {
      console.warn('[DraftSyncQueue] Background sync retry scheduled:', err);
      setTimeout(() => this.flush(), 4000);
      return false;
    } finally {
      this.isSyncing = false;
    }
  }
}

export const draftSyncQueue = new DraftAnswerSyncQueue();
