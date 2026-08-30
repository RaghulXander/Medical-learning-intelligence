import type { FieldDefinition } from '@/components/editor/schema-field-editor';
import type { MobileWidget, MobileWidgetType } from '@medical/shared';

export const mobileWidgetLabels: Record<MobileWidgetType, string> = {
  goal_progress: 'Daily Goal', continue_learning: 'Continue Learning', focus_area: 'Focus Area', custom_mock: 'Custom Mock', quick_presets: 'Quick Presets',
};

export const mobileWidgetFields: Record<MobileWidgetType, FieldDefinition[]> = {
  goal_progress: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'dailyGoal', label: 'Daily question goal', type: 'number', min: 1, max: 500 }, { name: 'actionLabel', label: 'Action label', type: 'text', required: true }],
  continue_learning: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'actionLabel', label: 'Action label', type: 'text', required: true }],
  focus_area: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'actionLabel', label: 'Action label', type: 'text', required: true }],
  custom_mock: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'description', label: 'Description', type: 'textarea', required: true }],
  quick_presets: [{ name: 'title', label: 'Title', type: 'text', required: true }, { name: 'viewAllLabel', label: 'View all label', type: 'text', required: true }, { name: 'limit', label: 'Maximum cards', type: 'number', min: 1, max: 10 }],
};

export function createMobileWidget(type: MobileWidgetType, order: number): MobileWidget {
  const common = { id: `${type.replaceAll('_', '-')}-${Date.now()}`, enabled: true, order, audience: 'ALL' as const, platforms: ['ALL' as const], rolloutPercentage: 100 };
  switch (type) {
    case 'goal_progress': return { ...common, type, props: { title: 'Daily Preparation Target', dailyGoal: 20, actionLabel: 'Start Daily Quiz' } };
    case 'continue_learning': return { ...common, type, props: { title: 'Unfinished Assessment', actionLabel: 'Resume Exam Now' } };
    case 'focus_area': return { ...common, type, props: { title: 'High-Yield Weak Topic', actionLabel: 'Practice Weak Area' } };
    case 'custom_mock': return { ...common, type, props: { title: 'Custom QBank & Mock Test', description: 'Build a test by topic and difficulty.' } };
    case 'quick_presets': return { ...common, type, props: { title: 'High-Yield Test Modules', viewAllLabel: 'View All', limit: 3 } };
  }
}
