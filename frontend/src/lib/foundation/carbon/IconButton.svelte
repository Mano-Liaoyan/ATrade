<!-- A Carbon ghost icon-only button, size sm (32px), with a Carbon tooltip. The tooltip and the accessible name give
     the action name, for example "Maximize panel". Toolbars and panel header lines use it (spec #99, toolbar rule). -->
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
    onclick: () => void;
  }

  const { label, icon, align = 'bottom', disabled = false, onclick }: Props = $props();
</script>

<Tooltip text={label} {align}>
  {#snippet trigger({ props })}
    <button
      {...props}
      type="button"
      class={[
        'cds--btn cds--btn--ghost cds--btn--sm cds--layout--size-sm cds--btn--icon-only atrade-icon-button',
        disabled && 'cds--btn--disabled',
      ]}
      aria-label={label}
      aria-disabled={disabled ? 'true' : undefined}
      onclick={() => {
        if (!disabled) {
          onclick();
        }
      }}
    >
      <Icon {icon} class="cds--btn__icon" />
    </button>
  {/snippet}
</Tooltip>
