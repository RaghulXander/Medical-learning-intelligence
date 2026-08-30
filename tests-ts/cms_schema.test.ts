import { describe, expect, test } from 'bun:test';
import rawContent from '../apps/web/content/landing-page.json';
import { createSection } from '../apps/web/src/lib/cms/registry';
import { landingPageDocumentSchema } from '../apps/web/src/lib/cms/schema';

describe('landing page CMS schema', () => {
  test('accepts the published landing page document', () => {
    const parsed = landingPageDocumentSchema.parse(rawContent);
    expect(parsed.schemaVersion).toBe(1);
    expect(parsed.sections.length).toBeGreaterThan(0);
  });

  test('rejects duplicate section IDs', () => {
    const copy = structuredClone(rawContent);
    copy.sections.push(structuredClone(copy.sections[0]!));
    expect(landingPageDocumentSchema.safeParse(copy).success).toBe(false);
  });

  test('rejects unsupported actions', () => {
    const copy = structuredClone(rawContent) as unknown as {
      sections: Array<{ type: string; props: { primaryAction?: { action: string } } }>;
    };
    const hero = copy.sections.find((section) => section.type === 'hero');
    if (!hero?.props.primaryAction) throw new Error('Hero fixture missing');
    hero.props.primaryAction.action = 'RUN_JAVASCRIPT';
    expect(landingPageDocumentSchema.safeParse(copy).success).toBe(false);
  });

  test('creates valid defaults for every supported widget', () => {
    const widgetTypes = ['hero', 'diagnostic_cta', 'stats', 'feature_grid', 'content_block', 'contact_cta'] as const;
    for (const [index, widgetType] of widgetTypes.entries()) {
      const section = createSection(widgetType, (index + 1) * 10);
      expect(section.type).toBe(widgetType);
      expect(section.enabled).toBe(true);
    }
  });
});
