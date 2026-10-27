// Public entry of foundation/command_palette: the shell of the global command palette (docs/architecture.md section
// 13). The shell has no domain meaning. src/routes/ gives it the commands.

export { isCommandPaletteShortcut, type PaletteCommand, type PaletteCommandGroup } from './command_palette';
export { default as CommandPalette } from './CommandPalette.svelte';
