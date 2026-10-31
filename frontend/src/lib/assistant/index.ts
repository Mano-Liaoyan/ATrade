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
export {
  addServerMessage,
  addUserMessage,
  describeToolStep,
  EMPTY_LOG,
  readConversationLog,
  type ConversationLog,
  type DiffItem,
  type LogItem,
  type MessageItem,
  type MetricsItem,
  type ScreenItem,
  type ServerMessage,
  type ToolStepItem,
} from './conversation_log';
export {
  createConversation,
  deleteConversation,
  discardStrategyVersion,
  listConversations,
  readConversation,
  renameConversation,
  type Conversation,
  type ConversationDetail,
} from './conversation_api';
export { openConversationSocket, type ConversationSocket } from './conversation_socket';
export {
  changeProvider,
  DEFAULT_THINKING_LEVEL,
  describeSendButton,
  describeThinkingSelect,
  findDefaultSelection,
  isThinkingLevel,
  listSelectItems,
  type ConnectionState,
  type LastModel,
  type ModelSelection,
  type ThinkingLevel,
} from './model_selection';
export { listCredentials, listProviders } from './credentials';
export { describeToolStepGroup, groupToolSteps, type GroupedLogEntry, type ToolStepGroup } from './tool_step_groups';
