<!-- An icon of @carbon/icons as inline SVG. The icon is decoration: the control that holds it has the name. -->
<script lang="ts">
  import type { CarbonIconDescriptor } from './carbon_icon';

  interface Props {
    icon: CarbonIconDescriptor;
    class?: string;
  }

  const { icon, class: className }: Props = $props();
</script>

<svg {...icon.attrs} class={className} aria-hidden="true" focusable="false">
  {#each icon.content ?? [] as element, index (index)}
    <svelte:element this={element.elem} {...element.attrs} />
  {/each}
</svg>
