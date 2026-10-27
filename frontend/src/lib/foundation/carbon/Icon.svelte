<!-- One @carbon/icons icon as inline SVG. Import the icon from `@carbon/icons/es/<name>/<size>.js`.
     The icon is decorative (aria-hidden) unless it has a `label`. -->
<script lang="ts">
  import type { CarbonIcon } from './icon_types';

  interface Props {
    icon: CarbonIcon;
    label?: string;
    class?: string;
  }

  const { icon, label, class: className }: Props = $props();
</script>

<svg
  {...icon.attrs}
  class={className}
  focusable="false"
  aria-hidden={label === undefined ? 'true' : undefined}
  aria-label={label}
  role={label === undefined ? undefined : 'img'}
>
  {#each icon.content ?? [] as node, index (index)}
    <svelte:element this={node.elem} {...node.attrs} />
  {/each}
</svg>
