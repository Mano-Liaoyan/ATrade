// The items of CommandDialog. The public entry is index.ts.
import type { CarbonIconNode } from '#lib/foundation/carbon';

/** An icon button at the end of an item, for example "Add SMA to favorite indicators". A click on it does not select the item. */
export interface CommandDialogItemAction {
  label: string;
  icon: Pick<CarbonIconNode, 'attrs' | 'content'>;
}

/** One choice. `detail` shows at the end of the row in IBM Plex Mono. */
export interface CommandDialogItem {
  value: string;
  label: string;
  detail?: string;
  keywords?: string[];
  action?: CommandDialogItemAction;
}
