import { z } from 'zod';

const cmsActionSchema = z.object({
  label: z.string().trim().min(1).max(80),
  action: z.enum(['START_DIAGNOSTIC', 'OPEN_STUDENT_HUB', 'OPEN_SIGNUP', 'CONTACT']),
});

const sectionBase = {
  id: z.string().regex(/^[a-z][a-z0-9-]{2,63}$/),
  enabled: z.boolean(),
  order: z.number().int().min(0).max(10000),
  audience: z.enum(['ALL', 'GUEST', 'AUTHENTICATED']),
};

const heroSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('hero'),
  props: z.object({
    eyebrow: z.string().trim().min(1).max(100),
    title: z.string().trim().min(1).max(160),
    highlight: z.string().trim().min(1).max(160),
    description: z.string().trim().min(1).max(600),
    primaryAction: cmsActionSchema,
    secondaryAction: cmsActionSchema.optional(),
  }),
});

const diagnosticSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('diagnostic_cta'),
  props: z.object({
    badge: z.string().trim().min(1).max(80),
    title: z.string().trim().min(1).max(200),
    description: z.string().trim().min(1).max(500),
    questionCount: z.number().int().min(1).max(20),
    durationMinutes: z.number().int().min(1).max(60),
    actionLabel: z.string().trim().min(1).max(80),
  }),
});

const statsSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('stats'),
  props: z.object({
    items: z.array(z.object({
      label: z.string().trim().min(1).max(80),
      value: z.string().trim().min(1).max(40),
    })).min(1).max(8),
  }),
});

const featureSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('feature_grid'),
  props: z.object({
    badge: z.string().trim().min(1).max(80),
    title: z.string().trim().min(1).max(200),
    description: z.string().trim().min(1).max(500),
    items: z.array(z.object({
      icon: z.enum(['microscope', 'zap', 'shield-check', 'brain-circuit', 'book-open']),
      title: z.string().trim().min(1).max(140),
      description: z.string().trim().min(1).max(500),
      tag: z.string().trim().min(1).max(80),
    })).min(1).max(12),
  }),
});

const contentSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('content_block'),
  props: z.object({
    title: z.string().trim().min(1).max(200),
    body: z.string().trim().min(1).max(4000),
  }),
});

const contactSectionSchema = z.object({
  ...sectionBase,
  type: z.literal('contact_cta'),
  props: z.object({
    title: z.string().trim().min(1).max(200),
    description: z.string().trim().min(1).max(500),
    email: z.string().email().max(254),
    actionLabel: z.string().trim().min(1).max(80),
  }),
});

export const landingSectionSchema = z.discriminatedUnion('type', [
  heroSectionSchema,
  diagnosticSectionSchema,
  statsSectionSchema,
  featureSectionSchema,
  contentSectionSchema,
  contactSectionSchema,
]);

export const landingPageDocumentSchema = z.object({
  schemaVersion: z.literal(1),
  documentVersion: z.string().datetime(),
  site: z.object({
    title: z.string().trim().min(1).max(120),
    description: z.string().trim().min(1).max(500),
  }),
  sections: z.array(landingSectionSchema).min(1).max(30),
}).superRefine((document, context) => {
  const ids = new Set<string>();
  for (const [index, section] of document.sections.entries()) {
    if (ids.has(section.id)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['sections', index, 'id'],
        message: `Duplicate section ID: ${section.id}`,
      });
    }
    ids.add(section.id);
  }
});

export type LandingPageDocument = z.infer<typeof landingPageDocumentSchema>;
export type LandingSection = z.infer<typeof landingSectionSchema>;
export type WidgetType = LandingSection['type'];

export function parseLandingPageDocument(value: unknown): LandingPageDocument {
  return landingPageDocumentSchema.parse(value);
}
