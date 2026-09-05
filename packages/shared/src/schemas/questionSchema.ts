/**
 * packages/shared/src/schemas/questionSchema.ts
 *
 * Zod validation schemas for question review, status changes, and issue reporting.
 */

import { z } from 'zod';

export const QuestionOptionSchema = z.object({
  key: z.string().regex(/^[A-Z]$/),
  text: z.string().min(1, 'Option text cannot be empty'),
});

export const QuestionEditSchema = z.object({
  expected_updated_at: z.string().datetime(),
  stem: z.string().trim().min(10).max(10000),
  options: z.array(QuestionOptionSchema).min(2).max(8),
  correct_option: z.string().regex(/^[A-Z]$/),
  explanation: z.string().trim().max(20000).nullable().optional(),
  difficulty: z.enum(['easy', 'medium', 'hard', 'very_hard']),
  cognitive_level: z.enum(['recall', 'understanding', 'application', 'analysis']),
  question_type: z.enum(['single_best_answer', 'multiple_choice', 'case_based']),
  primary_topic_id: z.string().nullable().optional(),
  learning_objective: z.string().trim().max(2000).nullable().optional(),
  edit_notes: z.string().trim().max(1000).nullable().optional(),
}).superRefine((question, context) => {
  const keys = question.options.map((option) => option.key);
  if (new Set(keys).size !== keys.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ['options'], message: 'Option keys must be unique' });
  }
  if (!keys.includes(question.correct_option)) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ['correct_option'], message: 'Correct answer must match an option' });
  }
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
  difficulty: z.enum(['easy', 'medium', 'hard', 'very_hard']).optional(),
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
