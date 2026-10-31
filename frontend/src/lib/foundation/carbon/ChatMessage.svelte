<!-- Adapted from carbon-components-svelte ChatMessage
     (https://github.com/carbon-design-system/carbon-components-svelte/blob/main/src/Chat/ChatMessage.svelte).
     Copyright 2019 IBM. Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0).
     ATrade changes: Svelte 5, `cds--` classes, no avatar, actions, attachments, meta, or delivery status.

     One message of a ChatLog. `from="me"` is a bubble at the end. `from="them"` is text over the full width, without a
     bubble (as in the AI coding apps), so long answers, tables, and code have room. `continued` marks a
     message after a message of the same author (arrangeChatLog). `streaming` shows a caret while the text arrives.
     `typing` shows the typing indicator in place of the text. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    from: 'me' | 'them';
    /** Screen readers announce the author before the message, because the alignment does not say who writes. */
    author: string;
    continued?: boolean;
    streaming?: boolean;
    typing?: boolean;
    /** The text that screen readers announce for the typing indicator. */
    typingText?: string;
    children?: Snippet;
  }

  const {
    from,
    author,
    continued = false,
    streaming = false,
    typing = false,
    typingText = 'Typing',
    children,
  }: Props = $props();
</script>

<li
  class={[
    'cds--chat-message',
    from === 'me' && 'cds--chat-message--me',
    continued && 'cds--chat-message--continued',
    streaming && 'cds--chat-message--streaming',
  ]}
  aria-busy={streaming ? 'true' : undefined}
>
  <div class="cds--chat-message__main">
    <span class="cds--visually-hidden">{author}</span>
    {#if typing}
      <div role="status" class="cds--chat-message__bubble cds--chat-message__bubble--typing">
        <span class="cds--chat-message__dot" aria-hidden="true"></span>
        <span class="cds--chat-message__dot" aria-hidden="true"></span>
        <span class="cds--chat-message__dot" aria-hidden="true"></span>
        <span class="cds--visually-hidden">{typingText}</span>
      </div>
    {:else}
      <div class="cds--chat-message__bubble">{@render children?.()}</div>
    {/if}
  </div>
</li>

<style>
  /* Carbon has no chat message styles. Carbon tokens only: the chat bubble tokens of the Carbon v11 themes. */
  .cds--chat-message {
    display: flex;
    margin-block-start: var(--cds-spacing-05);
  }

  .cds--chat-message:first-child,
  :global(.cds--chat-divider) + .cds--chat-message {
    margin-block-start: 0;
  }

  .cds--chat-message--continued {
    margin-block-start: var(--cds-spacing-02);
  }

  .cds--chat-message--me {
    justify-content: flex-end;
  }

  .cds--chat-message__main {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
  }

  .cds--chat-message--me .cds--chat-message__main {
    flex: 0 1 auto;
    max-width: 85%;
  }

  /* A message of the other author: plain text over the full width. */
  .cds--chat-message__bubble {
    min-width: 0;
    color: var(--cds-text-primary);
    font-size: var(--cds-body-01-font-size);
    line-height: var(--cds-body-01-line-height);
    letter-spacing: var(--cds-body-01-letter-spacing);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .cds--chat-message--me .cds--chat-message__bubble {
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    background-color: var(--cds-chat-bubble-user);
    color: var(--cds-chat-bubble-user-text);
  }

  /* A blinking caret while the text arrives. */
  .cds--chat-message--streaming .cds--chat-message__bubble::after {
    display: inline-block;
    width: 0.5em;
    height: 1em;
    margin-inline-start: var(--cds-spacing-01);
    vertical-align: -0.2em;
    background-color: var(--cds-icon-secondary);
    content: '';
    animation: chat-caret 1s steps(1) infinite;
  }

  @keyframes chat-caret {
    50% {
      opacity: 0;
    }
  }

  .cds--chat-message__bubble--typing {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-02);
    padding-block: var(--cds-spacing-03);
  }

  .cds--chat-message__dot {
    width: var(--cds-spacing-02);
    height: var(--cds-spacing-02);
    border-radius: 50%;
    background-color: var(--cds-text-secondary);
    animation: chat-typing 1.2s ease-in-out infinite;
  }

  .cds--chat-message__dot:nth-child(2) {
    animation-delay: 0.15s;
  }

  .cds--chat-message__dot:nth-child(3) {
    animation-delay: 0.3s;
  }

  @keyframes chat-typing {
    0%,
    60%,
    100% {
      opacity: 0.4;
      transform: none;
    }

    30% {
      opacity: 1;
      transform: translateY(calc(-1 * var(--cds-spacing-01)));
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .cds--chat-message__dot,
    .cds--chat-message--streaming .cds--chat-message__bubble::after {
      animation: none;
    }
  }
</style>
