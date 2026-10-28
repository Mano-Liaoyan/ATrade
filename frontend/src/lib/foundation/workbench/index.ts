// Public entry of foundation/workbench: the full-window workbench frame and its shared parts (spec #99, ticket #102).
// Each page that fills the window uses these parts, so all pages have the same header lines, buttons, and splitter.
export { default as Workbench } from './Workbench.svelte';
export { default as SideColumn } from './SideColumn.svelte';
export { default as PanelSplit } from './PanelSplit.svelte';
export { default as Panel, type PanelState, type PanelTabs } from './Panel.svelte';
export { default as PanelHeader } from './PanelHeader.svelte';
export { default as Splitter } from './Splitter.svelte';
export {
  createPanelSplitLayout,
  findPanelPixelRange,
  findPanelSize,
  isPanelHeaderOnly,
  listPanelRows,
  readPanelSplitLayout,
  restorePanelSplit,
  togglePanelSize,
  type PanelRow,
  type PanelSize,
  type PanelSpec,
  type PanelSplitLayout,
  type PixelRange,
} from './panel_split';
export { findSplitterDragValue, findSplitterKeyValue, type SplitterDrag, type SplitterKeyRange, type SplitterRange } from './splitter';
export { readSideColumnLayout, readStoredLayout, writeStoredLayout, type SideColumnLayout } from './stored_layout';
export { isEmptyHeaderPart } from './header_target';
