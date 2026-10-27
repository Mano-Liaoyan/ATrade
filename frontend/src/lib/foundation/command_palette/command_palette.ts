// The commands and the keyboard shortcut of the command palette. The public entry is index.ts.

/** One command of the palette. `run` opens a page or a form. The palette closes before it calls `run`. */
export interface PaletteCommand {
  label: string;
  keywords?: string[];
  run: () => void;
}

/** A named group of commands. The palette shows the heading above the commands of the group. */
export interface PaletteCommandGroup {
  heading: string;
  commands: PaletteCommand[];
}

type ShortcutKeys = Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey' | 'shiftKey' | 'repeat'>;

/**
 * True for Ctrl K and Cmd K (macOS). The palette accepts both keys on all systems, because a browser can report a
 * different system than the keyboard has (for example Safari emulation on Linux).
 */
export function isCommandPaletteShortcut(keys: ShortcutKeys): boolean {
  return (
    keys.key.toLowerCase() === 'k' && (keys.ctrlKey || keys.metaKey) && !keys.altKey && !keys.shiftKey && !keys.repeat
  );
}
