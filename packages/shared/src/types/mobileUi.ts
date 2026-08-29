import { z } from 'zod';

const widgetBase = {
  id: z.string().regex(/^[a-z][a-z0-9-]{2,63}$/),
  enabled: z.boolean(),
  order: z.number().int().min(0).max(10000),
  audience: z.enum(['ALL', 'AUTHENTICATED', 'FREE', 'SUBSCRIBED']),
  platforms: z.array(z.enum(['ALL', 'IOS', 'ANDROID'])).min(1).max(3),
  rolloutPercentage: z.number().int().min(0).max(100),
};

export const mobileWidgetSchema = z.discriminatedUnion('type', [
  z.object({ ...widgetBase, type: z.literal('goal_progress'), props: z.object({ title: z.string().min(1).max(100), dailyGoal: z.number().int().min(1).max(500), actionLabel: z.string().min(1).max(80) }) }),
  z.object({ ...widgetBase, type: z.literal('continue_learning'), props: z.object({ title: z.string().min(1).max(100), actionLabel: z.string().min(1).max(80) }) }),
  z.object({ ...widgetBase, type: z.literal('focus_area'), props: z.object({ title: z.string().min(1).max(100), actionLabel: z.string().min(1).max(80) }) }),
  z.object({ ...widgetBase, type: z.literal('custom_mock'), props: z.object({ title: z.string().min(1).max(120), description: z.string().min(1).max(300) }) }),
  z.object({ ...widgetBase, type: z.literal('quick_presets'), props: z.object({ title: z.string().min(1).max(100), viewAllLabel: z.string().min(1).max(80), limit: z.number().int().min(1).max(10) }) }),
]);

export const mobileScreenDocumentSchema = z.object({
  schemaVersion: z.literal(1),
  screenKey: z.literal('home'),
  minimumAppVersion: z.string().regex(/^\d+\.\d+\.\d+$/),
  cacheTtlSeconds: z.number().int().min(60).max(86400),
  widgets: z.array(mobileWidgetSchema).min(1).max(30),
}).superRefine((document, context) => {
  const ids = document.widgets.map((widget) => widget.id);
  if (new Set(ids).size !== ids.length) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ['widgets'], message: 'Widget IDs must be unique' });
  }
});

export type MobileWidget = z.infer<typeof mobileWidgetSchema>;
export type MobileWidgetType = MobileWidget['type'];
export type MobileScreenDocument = z.infer<typeof mobileScreenDocumentSchema>;

export interface MobileScreenResponse {
  version: number;
  document: MobileScreenDocument;
  appVersion?: string;
}
