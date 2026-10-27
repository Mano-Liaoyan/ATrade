<!-- A Carbon icon from @carbon/icons, for example `import Light20 from '@carbon/icons/es/light/20.js'`.
     Without `label` the icon is decorative and hidden from assistive technology. -->
<script lang="ts">
  import type { CarbonIconNode } from './carbon_icon';

  interface Props {
    icon: Pick<CarbonIconNode, 'attrs' | 'content'>;
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
