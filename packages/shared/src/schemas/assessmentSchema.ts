/**
 * packages/shared/src/schemas/assessmentSchema.ts
 *
 * Zod validation schemas for assessment creation, runner heartbeat, and submission.
 */

import { z } from 'zod';

export const SectionConfigSchema = z.object({
  name: z.string().min(1, 'Section name is required'),
  question_count: z.number().int().positive('Question count must be positive'),
  duration_seconds: z.number().int().positive().optional(),
  navigation_policy: z.enum(['FREE', 'SECTION_TIMED', 'FORWARD_ONLY']).default('FREE'),
});

export const CreateAssessmentSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters'),
  type: z.enum(['MOCK', 'TOPIC_TEST', 'DAILY_DOSE', 'GRAND_TEST', 'CUSTOM']).default('MOCK'),
  question_count: z.number().int().min(1).max(300).default(50),
  duration_seconds: z.number().int().min(60).default(3000),
  marking_scheme_id: z.string().default('NEET_4_1'),
  navigation_policy: z.enum(['FREE', 'SECTION_TIMED', 'FORWARD_ONLY']).default('FREE'),
  blueprint: z.record(z.any()).optional().default({}),
  sections: z.array(SectionConfigSchema).optional(),
});

export const HeartbeatQuestionResponseSchema = z.object({
  question_id: z.string().uuid(),
  selected_answer: z.string().nullable().optional(),
  marked_for_review: z.boolean().optional().default(false),
  time_spent_seconds: z.number().int().nonnegative().optional().default(0),
});

export const HeartbeatRequestSchema = z.object({
  responses: z.array(HeartbeatQuestionResponseSchema),
  elapsed_seconds: z.number().int().nonnegative().optional(),
});

export const SubmitAttemptSchema = z.object({
  responses: z.array(HeartbeatQuestionResponseSchema).optional(),
  final_elapsed_seconds: z.number().int().nonnegative().optional(),
});
