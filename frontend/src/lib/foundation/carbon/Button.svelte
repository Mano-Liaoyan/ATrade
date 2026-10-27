<!-- Carbon button. The text says what the button does, for example "Send paper order". -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import { buttonClasses, type ButtonKind, type ButtonSize } from './carbon_state';

  interface Props extends Omit<HTMLButtonAttributes, 'class'> {
    kind?: ButtonKind;
    size?: ButtonSize;
    ref?: HTMLButtonElement | null;
    class?: string;
    children: Snippet;
  }

  let {
    kind = 'primary',
    size = 'lg',
    type = 'button',
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: Props = $props();
</script>

<button bind:this={ref} {type} {...restProps} class={[...buttonClasses({ kind, size }), className]}>
  {@render children()}
</button>
