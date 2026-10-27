<!-- An icon of @carbon/icons, drawn from its descriptor. The icon is decoration: the control around it has the name. -->
<script lang="ts">
  import type { CarbonIconNode } from '@carbon/icons/es/*';

  interface Props {
    icon: CarbonIconNode;
    class?: string;
  }

  const { icon, class: className }: Props = $props();
</script>

<svg {...icon.attrs} class={className} aria-hidden="true" focusable="false">
  {#each icon.content ?? [] as node, index (index)}
    {#if node.elem === 'path'}
      <path {...node.attrs} />
    {:else if node.elem === 'circle'}
      <circle {...node.attrs} />
    {:else if node.elem === 'rect'}
      <rect {...node.attrs} />
    {/if}
  {/each}
</svg>
