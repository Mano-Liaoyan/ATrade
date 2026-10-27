// Public entry of the strategy capability: the strategy HTTP client, the unsaved drafts in the browser, and the
// language server connection of the editor.
export {
  createStrategy,
  deleteStrategy,
  listStrategies,
  readStrategy,
  readStrategyVersion,
  saveStrategyVersion,
  type CodeProblem,
  type DeleteResult,
  type RequestResult,
  type SaveResult,
  type StrategyDetail,
  type StrategyListItem,
  type StrategyVersion,
  type StrategyVersionSummary,
} from './strategy_api';
export { clearDraft, formatVersionLabel, readDraft, writeDraft, type DraftKey } from './strategy_drafts';
export { connectStrategyLanguageServer, type LanguageServerConnection } from './strategy_language_server';
