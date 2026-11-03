// Public entry of foundation/command_dialog: a Carbon modal with a search field and one list of choices, on Bits UI
// Dialog and Command. It has no domain meaning. The bar chart "Add indicator" dialog uses it
// (docs/architecture/indicator.md section 23.9.5).

export type { CommandDialogItem, CommandDialogItemAction } from './command_dialog';
export { default as CommandDialog } from './CommandDialog.svelte';
