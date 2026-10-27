// The types of InlineNotification. The public entry is index.ts.

/** success and info are a status, error and warning are an alert. */
export type NotificationKind = 'success' | 'error' | 'info' | 'warning';

/** The result of an action that a page shows. Spread it on the component: <InlineNotification {...message} />. */
export interface NotificationMessage {
  kind: NotificationKind;
  title: string;
  subtitle?: string;
}
