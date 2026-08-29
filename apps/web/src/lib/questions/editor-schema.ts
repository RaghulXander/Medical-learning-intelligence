import type { FieldDefinition } from '@/components/editor/schema-field-editor';

const optionKeys = 'ABCDEFGH'.split('').map((value) => ({ label: value, value }));

export const questionEditorFields: FieldDefinition[] = [
  { name: 'stem', label: 'Question stem', type: 'textarea', required: true },
  {
    name: 'options', label: 'Answer options', type: 'array', minItems: 2, maxItems: 8, addLabel: 'Add option',
    item: { name: 'option', label: 'Option', type: 'object', fields: [
      { name: 'key', label: 'Key', type: 'select', options: optionKeys },
      { name: 'text', label: 'Option text', type: 'textarea', required: true },
    ] },
  },
  { name: 'correct_option', label: 'Correct option', type: 'select', options: optionKeys },
  { name: 'explanation', label: 'Explanation', type: 'textarea' },
  { name: 'learning_objective', label: 'Learning objective', type: 'textarea' },
  { name: 'primary_topic_id', label: 'Primary ontology/topic ID', type: 'text', description: 'Use a verified curriculum topic identifier; leave blank if unmapped.' },
  { name: 'difficulty', label: 'Difficulty', type: 'select', options: [{ label: 'Easy', value: 'easy' }, { label: 'Medium', value: 'medium' }, { label: 'Hard', value: 'hard' }] },
  { name: 'cognitive_level', label: 'Cognitive level', type: 'select', options: [{ label: 'Recall', value: 'recall' }, { label: 'Understanding', value: 'understanding' }, { label: 'Application', value: 'application' }, { label: 'Analysis', value: 'analysis' }] },
  { name: 'question_type', label: 'Question type', type: 'select', options: [{ label: 'Single best answer', value: 'single_best_answer' }, { label: 'Multiple choice', value: 'multiple_choice' }, { label: 'Case based', value: 'case_based' }] },
  { name: 'edit_notes', label: 'Editorial change notes', type: 'textarea', description: 'Explain clinically meaningful changes for the revision history.' },
];
