<!-- The inline parts of a markdown block. Text is a Svelte text node, so no HTML of the message renders. A link with
     an address that is not http, https, or mailto shows only its text. A link opens in a new tab. -->
<script lang="ts">
  import Self from './MarkdownInline.svelte';
  import type { MarkdownInline } from './markdown_blocks';

  interface Props {
    inlines: readonly MarkdownInline[];
  }

  const { inlines }: Props = $props();
</script>

<!-- eslint-disable svelte/no-navigation-without-resolve -- a link is an external address (http, https, or mailto) of the message. -->
{#each inlines as inline, index (index)}
  {#if inline.kind === 'text'}{inline.text}{:else if inline.kind === 'strong'}<strong
      ><Self inlines={inline.children} /></strong
    >{:else if inline.kind === 'emphasis'}<em><Self inlines={inline.children} /></em>{:else if inline.kind === 'deleted'}<del
      ><Self inlines={inline.children} /></del
    >{:else if inline.kind === 'code'}<code class="markdown-code">{inline.text}</code>{:else if inline.kind === 'break'}<br
    />{:else if inline.href === null}<Self inlines={inline.children} />{:else}<a
      class="cds--link"
      href={inline.href}
      target="_blank"
      rel="noreferrer noopener"><Self inlines={inline.children} /></a
    >{/if}
{/each}
<!-- eslint-enable svelte/no-navigation-without-resolve -->

<style>
  .markdown-code {
    padding: 0 var(--cds-spacing-01);
    background-color: var(--cds-layer-accent-01);
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    font-size: var(--cds-code-01-font-size);
  }
</style>
