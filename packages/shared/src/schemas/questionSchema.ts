/**
 * packages/shared/src/schemas/questionSchema.ts
 *
 * Zod validation schemas for question review, status changes, and issue reporting.
 */

import { z } from 'zod';

export const QuestionOptionSchema = z.object({
  key: z.string().min(1).max(2),
  text: z.string().min(1, 'Option text cannot be empty'),
});

export const QuestionFilterSchema = z.object({
  specialty: z.string().optional(),
  subject: z.string().optional(),
  topic_id: z.string().uuid().optional(),
  status: z.enum([
    'IMPORTED',
    'GENERATED',
    'AI_REVIEW',
    'HUMAN_REVIEW',
    'APPROVED',
    'REJECTED',
    'REPORTED',
    'RETIRED',
  ]).optional(),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional(),
  cognitive_level: z.enum(['recall', 'understanding', 'application', 'analysis']).optional(),
  search: z.string().optional(),
  page: z.number().int().positive().default(1),
  limit: z.number().int().positive().max(100).default(25),
});

export const QuestionReportSchema = z.object({
  question_id: z.string().uuid(),
  category: z.enum([
    'INCORRECT_ANSWER',
    'INCORRECT_EXPLANATION',
    'AMBIGUOUS_QUESTION',
    'MULTIPLE_CORRECT_ANSWERS',
    'POOR_WORDING',
    'WRONG_TOPIC',
    'OUTDATED_INFO',
    'REFERENCE_ISSUE',
    'OTHER',
  ]),
  comment: z.string().min(5, 'Please provide context for the issue report'),
});
