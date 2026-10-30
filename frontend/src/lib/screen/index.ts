// Public entry of the screen capability (docs/architecture/screen.md section 24.11): the HTTP client and the parts
// of the screen page. The condition card of the AI assistant uses ConditionBar too.
export { default as ConditionBar } from './ConditionBar.svelte';
export { default as ScreenExclusionTable } from './ScreenExclusionTable.svelte';
export { default as ScreenResultTable } from './ScreenResultTable.svelte';
export {
  buildConditionGroups,
  type ConditionGroup,
  type ConditionTag,
  type FunnelCounts,
  type IndicatorNames,
  type ScreenDefinition,
} from './condition_bar';
export { describeExclusionReason, listResultColumns, sortResultRows, type ScreenResultRow } from './result_table';
export {
  isDraftChanged,
  removeCondition,
  switchMarket,
  type RemovableGroup,
  type ScreenMarket,
} from './screen_draft';
export {
  createScreen,
  listScreens,
  readScreen,
  readScreenResult,
  runScreenDraft,
  saveScreen,
  type Screen,
  type ScreenListItem,
  type ScreenResult,
  type ScreenResultExclusion,
} from './screen_api';
