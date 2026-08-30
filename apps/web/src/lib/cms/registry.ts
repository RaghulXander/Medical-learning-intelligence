import type { LandingSection, WidgetType } from './schema';

export const widgetLabels: Record<WidgetType, string> = {
  hero: 'Hero',
  diagnostic_cta: 'Diagnostic CTA',
  stats: 'Statistics',
  feature_grid: 'Feature Grid',
  content_block: 'Content Block',
  contact_cta: 'Contact CTA',
};

export function createSection(type: WidgetType, order: number): LandingSection {
  const id = `${type.replaceAll('_', '-')}-${Date.now()}`;
  const common = { id, enabled: true, order, audience: 'ALL' as const };
  switch (type) {
    case 'hero':
      return { ...common, type, props: {
        eyebrow: 'New announcement', title: 'New headline', highlight: 'Highlighted message',
        description: 'Describe this section.',
        primaryAction: { label: 'Get Started', action: 'OPEN_SIGNUP' },
      } };
    case 'diagnostic_cta':
      return { ...common, type, props: {
        badge: 'Diagnostic', title: 'Test your knowledge', description: 'Start a short assessment.',
        questionCount: 5, durationMinutes: 5, actionLabel: 'Start Test',
      } };
    case 'stats':
      return { ...common, type, props: { items: [{ label: 'Statistic', value: '0' }] } };
    case 'feature_grid':
      return { ...common, type, props: {
        badge: 'Features', title: 'Platform features', description: 'What the platform provides.',
        items: [{ icon: 'book-open', title: 'Feature', description: 'Feature description.', tag: 'New' }],
      } };
    case 'content_block':
      return { ...common, type, props: { title: 'Content heading', body: 'Content body' } };
    case 'contact_cta':
      return { ...common, type, props: {
        title: 'Contact us', description: 'Talk with our team.', email: 'raghuljayan@gmail.com', actionLabel: 'Email Us',
      } };
  }
}
