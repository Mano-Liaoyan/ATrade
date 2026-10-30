<!-- Adapted from carbon-components-svelte ChatDivider
     (https://github.com/carbon-design-system/carbon-components-svelte/blob/main/src/Chat/ChatDivider.svelte).
     Copyright 2019 IBM. Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0).
     ATrade changes: Svelte 5, `cds--` classes, the label is a text property.

     The date divider of a ChatLog, for example "2026-10-30" before the first message of that date. -->
<script lang="ts">
  interface Props {
    label: string;
  }

  const { label }: Props = $props();
</script>

<li class="cds--chat-divider">
  <span class="cds--chat-divider__label">{label}</span>
</li>

<style>
  /* Carbon has no chat divider styles. Carbon tokens only. */
  .cds--chat-divider {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-04);
    margin-block: var(--cds-spacing-05);
    color: var(--cds-text-secondary);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
  }

  .cds--chat-divider:first-child {
    margin-block-start: 0;
  }

  .cds--chat-divider::before,
  .cds--chat-divider::after {
    flex: 1;
    height: 1px;
    background-color: var(--cds-border-subtle);
    content: '';
  }
</style>
