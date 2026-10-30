// Public entry of the assistant capability in the frontend (docs/architecture/assistant.md 25.8.1 and 25.9).
export { default as CredentialsDialog } from './CredentialsDialog.svelte';
export { describeCredentialKind, describeCredentialState, formatKey, type Credential, type Provider } from './credentials';
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
