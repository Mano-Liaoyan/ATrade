<!-- A Carbon ghost icon-only button, size sm (32px), with a Carbon tooltip. The tooltip and the accessible name give
     the action name, for example "Maximize panel". Toolbars and panel header lines use it (spec #99, toolbar rule).
     A toolbar button can show its state: `tone` gives the icon a Carbon token color, `marked` adds a dot (for example
     for unsaved changes), and `busy` turns the icon. The icon shape always changes with the state too, so the color is
     never the only sign. `kind` "primary" or "danger" gives the main action of a line, for example Send and Stop of
     the AI assistant composer. -->
<script module lang="ts">
  /** The icon color: icon-secondary (neutral, grey), icon-interactive (blue), or a support color. */
  export type IconTone = 'neutral' | 'interactive' | 'success' | 'warning' | 'error';
</script>

<script lang="ts">
  import type { CarbonIconNode } from './carbon_icon';
  import Icon from './Icon.svelte';
  import Tooltip from './Tooltip.svelte';

  interface Props {
    label: string;
    icon: Pick<CarbonIconNode, 'attrs' | 'content'>;
    /** The side of the tooltip. A button at the right end of a line uses bottom-end, so the tooltip stays in the window. */
    align?: 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
    /** A disabled button stays focusable and keeps its tooltip, so `label` must say why, for example
     "Start forward test: not available for 1 day bars". A click does nothing. */
    disabled?: boolean;
    /** The shortcut keys, for example "Ctrl+S". The tooltip shows them after the label. */
    shortcut?: string;
    /** Without a tone, the icon has the Carbon ghost button color. */
    tone?: IconTone;
    /** A dot on the icon. The label must also say it, for example "Save version, unsaved changes". */
    marked?: boolean;
    /** The icon turns. Use it with `disabled` and a label that says what runs. */
    busy?: boolean;
    kind?: 'ghost' | 'primary' | 'danger';
    /** The ID of a visible text that says more, for example why the button is disabled. */
    describedBy?: string;
    onclick: () => void;
  }

  const {
    label,
    icon,
    align = 'bottom',
    disabled = false,
    shortcut,
    tone,
    marked = false,
    busy = false,
    kind = 'ghost',
    describedBy,
    onclick,
  }: Props = $props();

  const tooltipText = $derived(shortcut === undefined ? label : `${label} (${shortcut})`);
</script>

<Tooltip text={tooltipText} {align}>
  {#snippet trigger({ props })}
    <button
      {...props}
      type="button"
      class={[
        `cds--btn cds--btn--${kind} cds--btn--sm cds--layout--size-sm cds--btn--icon-only atrade-icon-button`,
        disabled && !busy && 'cds--btn--disabled',
        busy && 'atrade-icon-button--busy',
        tone !== undefined && `atrade-icon-button--${tone}`,
      ]}
      aria-label={label}
      aria-describedby={describedBy}
      aria-disabled={disabled ? 'true' : undefined}
      aria-keyshortcuts={shortcut?.replaceAll('Ctrl', 'Control').replaceAll('Cmd', 'Meta')}
      onclick={() => {
        if (!disabled) {
          onclick();
        }
      }}
    >
      <Icon {icon} class="cds--btn__icon" />
      {#if marked}
        <span class="atrade-icon-button__dot"></span>
      {/if}
    </button>
  {/snippet}
</Tooltip>

<style>
  /* A tone gives the icon its token. Carbon paints the icon (and its paths) of a ghost icon-only button with
     --cds-icon-primary, so the tone sets that token on the button. A disabled button keeps the Carbon disabled color. */
  .atrade-icon-button--neutral:not(.cds--btn--disabled) {
    --cds-icon-primary: var(--cds-icon-secondary);
  }

  .atrade-icon-button--interactive:not(.cds--btn--disabled) {
    --cds-icon-primary: var(--cds-icon-interactive);
  }

  .atrade-icon-button--success:not(.cds--btn--disabled) {
    --cds-icon-primary: var(--cds-support-success);
  }

  .atrade-icon-button--warning:not(.cds--btn--disabled) {
    --cds-icon-primary: var(--cds-support-warning);
  }

  .atrade-icon-button--error:not(.cds--btn--disabled) {
    --cds-icon-primary: var(--cds-support-error);
  }

  /* A busy button does not react to a click, but it keeps its tone, so the running state shows. */
  .atrade-icon-button--busy {
    cursor: not-allowed;
  }

  .atrade-icon-button--busy :global(svg) {
    animation: atrade-icon-turn 1.2s linear infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .atrade-icon-button--busy :global(svg) {
      animation: none;
    }
  }

  @keyframes atrade-icon-turn {
    to {
      transform: rotate(360deg);
    }
  }

  .atrade-icon-button__dot {
    position: absolute;
    inset-block-start: var(--cds-spacing-02);
    inset-inline-end: var(--cds-spacing-02);
    inline-size: var(--cds-spacing-03);
    block-size: var(--cds-spacing-03);
    border-radius: 50%;
    background: var(--cds-icon-interactive);
    pointer-events: none;
  }
</style>
