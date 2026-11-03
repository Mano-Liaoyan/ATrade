// The items of CommandDialog. The public entry is index.ts.

/** One choice. `detail` shows at the end of the row in IBM Plex Mono. A disabled item shows `disabledText`. */
export interface CommandDialogItem {
  value: string;
  label: string;
  detail?: string;
  keywords?: string[];
  disabledText?: string;
}
