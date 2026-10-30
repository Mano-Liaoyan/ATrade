// Public entry of the assistant capability in the frontend: the credentials (docs/architecture/assistant.md 25.8.1), and
// the "Prompt" dialog and the prompt version requests (25.9). The assistant side column of the strategy page uses them.
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
export { default as CredentialsDialog } from './CredentialsDialog.svelte';
export { describeCredentialKind, describeCredentialState, formatKey, type Credential, type Provider } from './credentials';
