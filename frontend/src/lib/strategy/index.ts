// Public entry of the strategy capability: the strategy HTTP client and the unsaved drafts in the browser.
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
