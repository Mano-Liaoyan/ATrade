// The keyboard shortcut of the command palette: Ctrl K, or Cmd K on macOS.
import { describe, expect, it } from 'vite-plus/test';
import { isCommandPaletteShortcut } from './command_palette';

const NO_KEYS = { key: 'k', ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, repeat: false };

describe('isCommandPaletteShortcut', () => {
  it('is true for Ctrl K and for Cmd K', () => {
    expect(isCommandPaletteShortcut({ ...NO_KEYS, ctrlKey: true })).toBe(true);
    expect(isCommandPaletteShortcut({ ...NO_KEYS, metaKey: true })).toBe(true);
    expect(isCommandPaletteShortcut({ ...NO_KEYS, key: 'K', ctrlKey: true })).toBe(true);
  });

  it('is false for K without Ctrl or Cmd', () => {
    expect(isCommandPaletteShortcut(NO_KEYS)).toBe(false);
  });

  it('is false for other keys and for Shift or Alt with Ctrl K', () => {
    expect(isCommandPaletteShortcut({ ...NO_KEYS, key: 'j', ctrlKey: true })).toBe(false);
    expect(isCommandPaletteShortcut({ ...NO_KEYS, ctrlKey: true, shiftKey: true })).toBe(false);
    expect(isCommandPaletteShortcut({ ...NO_KEYS, ctrlKey: true, altKey: true })).toBe(false);
  });

  it('is false for a key that the keyboard repeats while the user holds it', () => {
    expect(isCommandPaletteShortcut({ ...NO_KEYS, ctrlKey: true, repeat: true })).toBe(false);
  });
});
