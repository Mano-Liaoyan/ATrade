<!-- The Copy icon button of a code block. After a click, the icon changes for 2 seconds: a checkmark ("Copied"), or a
     warning icon ("Not copied") when the browser refuses the clipboard. The state is in the icon, its accessible
     name, and its tooltip; no text shows next to it. -->
<script lang="ts">
  import Checkmark16 from '@carbon/icons/es/checkmark/16.js';
  import Copy16 from '@carbon/icons/es/copy/16.js';
  import WarningAlt16 from '@carbon/icons/es/warning--alt/16.js';
  import { IconButton } from '#lib/foundation/carbon';

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

<IconButton
  label={phase === 'copied' ? 'Copied' : phase === 'failed' ? 'Not copied' : 'Copy'}
  icon={phase === 'copied' ? Checkmark16 : phase === 'failed' ? WarningAlt16 : Copy16}
  tone={phase === 'copied' ? 'success' : phase === 'failed' ? 'error' : undefined}
  align="left"
  onclick={() => void copy()}
/>
