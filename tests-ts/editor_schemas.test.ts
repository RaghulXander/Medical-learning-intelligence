import { describe, expect, test } from 'bun:test';
import homeScreen from '../apps/mobile/content/home-screen.json';
import { QuestionEditSchema, mobileScreenDocumentSchema } from '../packages/shared/src';

describe('mobile screen schema', () => {
  test('accepts the bundled native home layout', () => {
    expect(mobileScreenDocumentSchema.parse(homeScreen).screenKey).toBe('home');
  });

  test('rejects duplicate widget identifiers', () => {
    const duplicate = structuredClone(homeScreen);
    duplicate.widgets.push(structuredClone(duplicate.widgets[0]!));
    expect(mobileScreenDocumentSchema.safeParse(duplicate).success).toBe(false);
  });
});

describe('question edit schema', () => {
  const valid = {
    expected_updated_at: new Date().toISOString(),
    stem: 'Which option is the single best answer?',
    options: [{ key: 'A', text: 'One' }, { key: 'B', text: 'Two' }],
    correct_option: 'A',
    explanation: 'Option A is supported by the reviewed evidence.',
    difficulty: 'medium',
    cognitive_level: 'application',
    question_type: 'single_best_answer',
  };

  test('accepts a complete editorial document', () => {
    expect(QuestionEditSchema.safeParse(valid).success).toBe(true);
  });

  test('rejects a correct answer that is not an option', () => {
    expect(QuestionEditSchema.safeParse({ ...valid, correct_option: 'C' }).success).toBe(false);
  });
});
