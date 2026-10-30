// Public entry of the assistant capability in the frontend: the "Prompt" dialog and the prompt version requests
// (docs/architecture/assistant.md 25.9). The assistant side column of the strategy page uses them.
export { default as PromptDialog } from './PromptDialog.svelte';
export {
  addSavedVersion,
  describeSaveProblem,
  formatPromptVersionLabel,
  listPromptVersions,
  openPromptDialog,
  restoreDefault,
  savePromptVersion,
  selectPromptVersion,
  type PromptDialogState,
  type PromptVersion,
  type PromptVersionItem,
  type PromptVersionList,
} from './prompt_dialog';
