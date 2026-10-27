<!-- Carbon tag. An operational tag is a button, for example the trigger of a tooltip. -->
<script module lang="ts">
  export type TagKind = 'blue' | 'cool-gray' | 'cyan' | 'gray' | 'green' | 'magenta' | 'purple' | 'red' | 'teal' | 'warm-gray';
</script>

<script lang="ts">
  import type { HTMLAttributes } from 'svelte/elements';

  interface Props extends HTMLAttributes<HTMLElement> {
    label: string;
    kind?: TagKind;
    size?: 'sm' | 'md' | 'lg';
    operational?: boolean;
  }

  const { label, kind = 'gray', size = 'md', operational = false, ...restProps }: Props = $props();

  const classes = $derived([
    'cds--tag',
    `cds--tag--${kind}`,
    size !== 'md' && `cds--tag--${size}`,
    operational && 'cds--tag--operational',
  ]);
</script>

{#if operational}
  <button type="button" {...restProps} class={classes}><span class="cds--tag__label">{label}</span></button>
{:else}
  <span {...restProps} class={classes}><span class="cds--tag__label">{label}</span></span>
{/if}
