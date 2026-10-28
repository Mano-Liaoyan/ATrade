<!-- The body of the problems and output panel of the strategy page (spec #99, ticket #107). Problems: the code
     problems of the last save; a click on a problem goes to its line in the editor. Output: the events and errors of
     saves, backtests, and forward tests, the oldest first. Each tab scrolls in its own region. -->
<script lang="ts">
  import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
  import { Icon } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { CodeProblem } from '#lib/strategy';
  import type { OutputTab } from './strategy_workbench';

  interface Props {
    tab: OutputTab;
    problems: readonly CodeProblem[];
    outputLines: readonly string[];
    onProblemClick: (problem: CodeProblem) => void;
  }

  const { tab, problems, outputLines, onProblemClick }: Props = $props();
</script>

{#if tab === 'problems'}
  <ScrollRegion label="Code problems" fill>
    <ul class="output-lines">
      {#each problems as problem, index (index)}
        <li>
          <button
            type="button"
            class="problem"
            onclick={() => {
              onProblemClick(problem);
            }}
          >
            <span class="problem-line"><Icon icon={ErrorFilled16} />Line {problem.line}</span>
            <span>{problem.message}</span>
          </button>
        </li>
      {/each}
    </ul>
  </ScrollRegion>
{:else}
  <ScrollRegion label="Output" fill>
    <ol class="output-lines code-lines">
      {#each outputLines as line, index (index)}
        <li>{line}</li>
      {/each}
    </ol>
  </ScrollRegion>
{/if}

<style>
  .output-lines {
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }

  .output-lines li {
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .code-lines li {
    display: flex;
    align-items: center;
    min-block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    white-space: pre-wrap;
  }

  .problem {
    display: flex;
    gap: var(--cds-spacing-05);
    align-items: center;
    box-sizing: border-box;
    inline-size: 100%;
    min-block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05);
    border: 0;
    background: transparent;
    color: var(--cds-text-primary);
    font: inherit;
    text-align: start;
    cursor: pointer;
  }

  .problem:hover {
    background: var(--cds-layer-hover-01);
  }

  .problem:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .problem-line {
    display: inline-flex;
    flex: none;
    gap: var(--cds-spacing-03);
    align-items: center;
    inline-size: var(--cds-spacing-10);
    font-variant-numeric: tabular-nums;
  }

  .problem-line :global(svg) {
    fill: var(--cds-support-error);
  }
</style>
