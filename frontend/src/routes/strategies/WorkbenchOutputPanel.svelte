<!-- PROTOTYPE (#99), throwaway: the Problems / Output panel and the status bar of the strategy workbench (VS Code
     layout). The 24px status bar always shows at the bottom of the main area: the problem counts and Output. The panel
     opens above it. Problems are the code check results of the last save; the API gives them no severity, so all count
     as errors. A click on the selected tab minimizes the panel to the status bar again. -->
<script lang="ts">
  import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
  import WarningAltFilled16 from '@carbon/icons/es/warning--alt--filled/16.js';
  import { Icon, Tabs } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { CodeProblem } from '#lib/strategy';
  import type { OutputTab, PanelSize } from './workbench_layout';
  import WorkbenchTabLine from './WorkbenchTabLine.svelte';

  interface Props {
    problems: CodeProblem[];
    outputLines: string[];
    size: PanelSize;
    // False while the panel is minimized or another panel is maximized: then only the status bar shows.
    isVisible: boolean;
    tab: OutputTab;
    onOpen: (tab: OutputTab) => void;
    onTabChange: (tab: OutputTab) => void;
    onToggleMinimized: () => void;
    onToggleMaximized: () => void;
  }

  const { problems, outputLines, size, isVisible, tab, onOpen, onTabChange, onToggleMinimized, onToggleMaximized }: Props =
    $props();

  const WARNING_COUNT = 0;
  // The selected state of the tab under the pointer, before the click selects it.
  let wasSelectedTabPressed = false;

  function notePressedTab(event: PointerEvent): void {
    const pressedTab = event.target instanceof Element ? event.target.closest('[role="tab"]') : null;
    wasSelectedTabPressed = pressedTab?.getAttribute('aria-selected') === 'true';
  }

  function minimizeOnSelectedTabClick(): void {
    if (wasSelectedTabPressed) {
      wasSelectedTabPressed = false;
      onToggleMinimized();
    }
  }
</script>

{#if isVisible}
  <section class={['output-panel', size === 'maximized' && 'maximized']} aria-label="Problems and output">
    <WorkbenchTabLine {size} minimizesToStatusBar {onToggleMinimized} {onToggleMaximized}>
      <!-- The tabs take the keyboard; this only reads the pointer to find a click on the selected tab. -->
      <!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
      <div class="panel-tabs" onpointerdown={notePressedTab} onclick={minimizeOnSelectedTabClick}>
        <Tabs
          label="Problems and output"
          items={[
            { value: 'problems', label: `Problems ${String(problems.length)}` },
            { value: 'output', label: 'Output' },
          ]}
          value={tab}
          onValueChange={(value: string) => {
            onTabChange(value === 'output' ? 'output' : 'problems');
          }}
        />
      </div>
    </WorkbenchTabLine>
    <div class="panel-body">
      <ScrollRegion label={tab === 'problems' ? 'Problems' : 'Output'} maxHeight="100%">
        {#if tab === 'problems'}
          <ul class="panel-lines">
            {#each problems as problem, index (index)}
              <li>
                <span class="problem-place"><Icon icon={ErrorFilled16} />Line {problem.line}</span>
                <span>{problem.message}</span>
              </li>
            {/each}
          </ul>
        {:else}
          <ol class="panel-lines code-lines">
            {#each outputLines as line, index (index)}
              <li>{line}</li>
            {/each}
          </ol>
        {/if}
      </ScrollRegion>
    </div>
  </section>
{/if}

<footer class="status-bar">
  <button
    type="button"
    class="status-item"
    aria-label={`Problems: ${String(problems.length)} errors, ${String(WARNING_COUNT)} warnings`}
    onclick={() => {
      onOpen('problems');
    }}
  >
    <span class="status-count error"><Icon icon={ErrorFilled16} />{problems.length}</span>
    <span class="status-count warning"><Icon icon={WarningAltFilled16} />{WARNING_COUNT}</span>
  </button>
  <button
    type="button"
    class="status-item"
    onclick={() => {
      onOpen('output');
    }}
  >
    Output
  </button>
</footer>

<style>
  .output-panel {
    display: flex;
    flex: none;
    flex-direction: column;
    block-size: calc(5 * var(--cds-spacing-09));
    min-block-size: 0;
    border-block-start: 1px solid var(--cds-border-subtle-01);
  }

  .output-panel.maximized {
    flex: 1;
    block-size: auto;
  }

  .panel-tabs {
    block-size: 100%;
  }

  .panel-body {
    position: relative;
    flex: 1;
    min-block-size: 0;
  }

  .panel-body :global(.scroll-region) {
    position: absolute;
    inset: 0;
  }

  .panel-lines {
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
  }

  .panel-lines li {
    display: flex;
    gap: var(--cds-spacing-05);
    align-items: center;
    min-block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .problem-place {
    display: inline-flex;
    flex: none;
    gap: var(--cds-spacing-03);
    align-items: center;
    inline-size: var(--cds-spacing-10);
    font-variant-numeric: tabular-nums;
  }

  .problem-place :global(svg),
  .status-count.error :global(svg) {
    fill: var(--cds-support-error);
  }

  .status-count.warning :global(svg) {
    fill: var(--cds-support-warning);
  }

  .code-lines {
    font-family: 'IBM Plex Mono', monospace;
    font-size: var(--cds-code-01-font-size);
  }

  .status-bar {
    display: flex;
    flex: none;
    align-items: stretch;
    block-size: var(--cds-spacing-06);
    border-block-start: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
  }

  .status-item {
    display: inline-flex;
    gap: var(--cds-spacing-04);
    align-items: center;
    padding: 0 var(--cds-spacing-04);
    border: 0;
    background: transparent;
    color: var(--cds-text-secondary);
    font: inherit;
    cursor: pointer;
  }

  .status-item:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-primary);
  }

  .status-item:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .status-count {
    display: inline-flex;
    gap: var(--cds-spacing-02);
    align-items: center;
    font-variant-numeric: tabular-nums;
  }
</style>
