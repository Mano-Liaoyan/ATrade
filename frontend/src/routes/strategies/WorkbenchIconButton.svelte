<!-- PROTOTYPE (#99), throwaway: a 32px Carbon ghost icon button of a workbench toolbar. The tooltip shows the action
     name and the shortcut. The tone gives the icon color from a Carbon token; the icon shape also shows the state.
     A busy button turns its icon, does not react, and keeps its tooltip (aria-disabled, not disabled). -->
<script lang="ts">
  import { Icon, Tooltip, type CarbonIconNode } from '#lib/foundation/carbon';
  import type { IconTone } from './workbench_layout';

  interface Props {
    label: string;
    icon: CarbonIconNode;
    shortcut?: string;
    tone?: IconTone;
    busy?: boolean;
    // A small dot on the icon, for example for unsaved changes.
    marked?: boolean;
    align?: 'bottom' | 'bottom-end';
    onclick: () => void;
  }

  const {
    label,
    icon,
    shortcut,
    tone = 'neutral',
    busy = false,
    marked = false,
    align = 'bottom',
    onclick,
  }: Props = $props();

  const tooltipText = $derived(shortcut === undefined ? label : `${label} (${shortcut})`);
</script>

<Tooltip text={tooltipText} {align}>
  {#snippet trigger({ props })}
    <button
      {...props}
      type="button"
      class="cds--btn cds--btn--ghost cds--btn--sm cds--layout--size-sm cds--btn--icon-only workbench-icon-button"
      aria-label={label}
      aria-disabled={busy ? 'true' : undefined}
      onclick={() => {
        if (!busy) {
          onclick();
        }
      }}
    >
      <span class={['icon-frame', `tone-${tone}`, busy && 'busy']}>
        <Icon {icon} />
        {#if marked}
          <span class="icon-dot"></span>
        {/if}
      </span>
    </button>
  {/snippet}
</Tooltip>

<style>
  /* Carbon paints ghost button icons with --cds-icon-primary. The tone color of the button wins here. */
  .workbench-icon-button :global(svg),
  .workbench-icon-button :global(svg path) {
    fill: currentColor;
  }

  .workbench-icon-button[aria-disabled='true'] {
    cursor: not-allowed;
  }

  .icon-frame {
    position: relative;
    display: inline-flex;
  }

  .tone-neutral {
    color: var(--cds-icon-secondary);
  }

  .tone-interactive {
    color: var(--cds-interactive);
  }

  .tone-success {
    color: var(--cds-support-success);
  }

  .tone-warning {
    color: var(--cds-support-warning);
  }

  .tone-error {
    color: var(--cds-support-error);
  }

  .icon-dot {
    position: absolute;
    inset-block-start: calc(-1 * var(--cds-spacing-01));
    inset-inline-end: calc(-1 * var(--cds-spacing-01));
    inline-size: var(--cds-spacing-03);
    block-size: var(--cds-spacing-03);
    border-radius: 50%;
    background: var(--cds-interactive);
  }

  .busy {
    animation: turn 1.2s linear infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .busy {
      animation: none;
    }
  }

  @keyframes turn {
    to {
      transform: rotate(360deg);
    }
  }
</style>
