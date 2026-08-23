/**
 * apps/student-native/src/index.ts
 *
 * Mobile application entry point importing typed shared contracts.
 */

import { Question, AssessmentPreset, AttemptResults } from '@medical/shared';
import { assessmentsApi } from '@medical/api-client';

export function getMobileExamSummary(preset: AssessmentPreset): string {
  return `[Mobile App] Loaded Preset: ${preset.title} (${preset.question_count} Questions)`;
}
