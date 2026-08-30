import type { FieldDefinition } from '@/components/editor/schema-field-editor';
import type { WidgetType } from './schema';

const actions = ['START_DIAGNOSTIC', 'OPEN_STUDENT_HUB', 'OPEN_SIGNUP', 'CONTACT'].map((value) => ({ label: value.replaceAll('_', ' '), value }));
const icons = ['microscope', 'zap', 'shield-check', 'brain-circuit', 'book-open'].map((value) => ({ label: value, value }));
const action: FieldDefinition = { name: 'action', label: 'Action', type: 'object', fields: [{ name: 'label', label: 'Label', type: 'text', required: true }, { name: 'action', label: 'Action type', type: 'select', options: actions }] };
const statItem: FieldDefinition = { name: 'item', label: 'Statistic', type: 'object', fields: [{ name: 'label', label: 'Label', type: 'text', required: true }, { name: 'value', label: 'Value', type: 'text', required: true }] };
const featureItem: FieldDefinition = { name: 'item', label: 'Feature', type: 'object', fields: [{ name: 'icon', label: 'Icon', type: 'select', options: icons }, { name: 'title', label: 'Title', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }, { name: 'tag', label: 'Tag', type: 'text', required: true }] };

export const landingWidgetFields: Record<WidgetType, FieldDefinition[]> = {
  hero: [{ name: 'eyebrow', label: 'Eyebrow', type: 'text', required: true }, { name: 'title', label: 'Title', type: 'text', required: true }, { name: 'highlight', label: 'Highlight', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }, { ...action, name: 'primaryAction', label: 'Primary action' }],
  diagnostic_cta: [{ name: 'badge', label: 'Badge', type: 'text', required: true }, { name: 'title', label: 'Title', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }, { name: 'questionCount', label: 'Question count', type: 'number', min: 1, max: 20 }, { name: 'durationMinutes', label: 'Duration (minutes)', type: 'number', min: 1, max: 60 }, { name: 'actionLabel', label: 'Action label', type: 'text', required: true }],
  stats: [{ name: 'items', label: 'Statistics', type: 'array', item: statItem, minItems: 1, maxItems: 8, addLabel: 'Add statistic' }],
  feature_grid: [{ name: 'badge', label: 'Badge', type: 'text', required: true }, { name: 'title', label: 'Title', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }, { name: 'items', label: 'Features', type: 'array', item: featureItem, minItems: 1, maxItems: 12, addLabel: 'Add feature' }],
  content_block: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'body', label: 'Body', type: 'textarea', required: true }],
  contact_cta: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }, { name: 'email', label: 'Email', type: 'text', required: true }, { name: 'actionLabel', label: 'Action label', type: 'text', required: true }],
};
