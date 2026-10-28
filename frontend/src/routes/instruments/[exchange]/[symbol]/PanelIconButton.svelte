<!-- PROTOTYPE (#99), throwaway: a 32px Carbon ghost icon button for a panel header. The tooltip and the aria-label
     give the action name. -->
<script lang="ts">
  import { Icon, Tooltip, type CarbonIconNode } from '#lib/foundation/carbon';

  interface Props {
    label: string;
    icon: CarbonIconNode;
    align?: 'bottom-end' | 'left' | 'right';
    onclick: () => void;
  }

  const { label, icon, align = 'bottom-end', onclick }: Props = $props();
</script>

<Tooltip text={label} {align}>
  {#snippet trigger({ props })}
    <button
      {...props}
      type="button"
      class="cds--btn cds--btn--ghost cds--btn--sm cds--layout--size-sm cds--btn--icon-only panel-icon-button"
      aria-label={label}
      {onclick}
    >
      <Icon {icon} />
    </button>
  {/snippet}
</Tooltip>

<style>
  .panel-icon-button :global(svg) {
    fill: var(--cds-icon-secondary);
  }

  .panel-icon-button:hover :global(svg) {
    fill: var(--cds-icon-primary);
  }
</style>
