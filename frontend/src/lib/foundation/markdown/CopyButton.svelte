<!-- The Copy button of a code block. After a click it says "Copied" (or "Not copied" when the browser refuses the
     clipboard) for 2 seconds. -->
<script lang="ts">
  import { Button } from '#lib/foundation/carbon';

  interface Props {
    /** The text that Copy puts on the clipboard. */
    text: string;
  }

  const { text }: Props = $props();

  const RESET_MILLISECONDS = 2000;
  let phase: 'ready' | 'copied' | 'failed' = $state('ready');
  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      phase = 'copied';
    } catch {
      phase = 'failed';
    }
    clearTimeout(resetTimer);
    resetTimer = setTimeout(() => {
      phase = 'ready';
    }, RESET_MILLISECONDS);
  }

  $effect(() => () => {
    clearTimeout(resetTimer);
  });
</script>

<Button kind="ghost" size="sm" onclick={() => void copy()}
  >{phase === 'copied' ? 'Copied' : phase === 'failed' ? 'Not copied' : 'Copy'}</Button
>
