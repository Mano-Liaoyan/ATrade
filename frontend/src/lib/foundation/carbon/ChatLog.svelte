<!-- Adapted from carbon-components-svelte ChatLog
     (https://github.com/carbon-design-system/carbon-components-svelte/blob/main/src/Chat/ChatLog.svelte).
     Copyright 2019 IBM. Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0).
     ATrade changes: Svelte 5, `cds--` classes, the ScrollRegion track and thumb, and the scroll rule in chat_log.ts.

     A message log with role="log". It holds ChatMessage and ChatDivider items. While the user is at the end of the
     log, the log scrolls to each new message and to each streamed part. While the user reads older messages, it does
     not scroll. -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { Snippet } from 'svelte';
  import { LogFollower } from './chat_log';

  interface Props {
    /** The accessible name of the log. */
    label: string;
    children: Snippet;
  }

  const { label, children }: Props = $props();

  let viewport: HTMLDivElement | undefined = $state();

  $effect(() => {
    if (viewport === undefined) {
      return;
    }
    const log: HTMLDivElement = viewport;
    const follower = new LogFollower();
    log.scrollTop = log.scrollHeight;
    function measure(): void {
      follower.measure({
        scrollTopPixels: log.scrollTop,
        contentHeightPixels: log.scrollHeight,
        viewportHeightPixels: log.clientHeight,
      });
    }
    // A new message, a streamed part, or the typing indicator changes the DOM of the log.
    const observer = new MutationObserver(() => {
      if (follower.followsNewContent) {
        log.scrollTop = log.scrollHeight;
      }
    });
    observer.observe(log, {
      childList: true,
      subtree: true,
      // eslint-disable-next-line @typescript-eslint/naming-convention -- readability-exception: the DOM names this field.
      characterData: true,
    });
    log.addEventListener('scroll', measure);
    return () => {
      observer.disconnect();
      log.removeEventListener('scroll', measure);
    };
  });
</script>

<ScrollRegion {label} role="log" fill bind:viewport>
  <ol class="cds--chat-log__list">
    {@render children()}
  </ol>
</ScrollRegion>

<style>
  /* Carbon has no chat log styles. Carbon tokens only. */
  .cds--chat-log__list {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: var(--cds-spacing-05);
    list-style: none;
  }
</style>
