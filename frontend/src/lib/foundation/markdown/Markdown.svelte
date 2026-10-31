<!-- A markdown text (GFM) in Carbon styles: headings, paragraphs, lists, links, block quotes, tables, rules, and code
     blocks (shell commands, diffs, and Mermaid diagrams). The text is untrusted: no HTML of the text renders.
     The text can stream in: an open code fence shows as plain code, and a half table shows as text until it is a table
     (docs/architecture/assistant.md 25.12.6). -->
<script lang="ts">
  import MarkdownBlocks from './MarkdownBlocks.svelte';
  import { parseMarkdown } from './markdown_blocks';

  interface Props {
    text: string;
  }

  const { text }: Props = $props();

  const blocks = $derived(parseMarkdown(text));
</script>

<div class="markdown"><MarkdownBlocks {blocks} /></div>

<style>
  .markdown {
    display: flow-root;
    min-inline-size: 0;
    white-space: normal;
  }

  .markdown :global(:where(p, ul, ol, blockquote, hr, figure, .markdown-heading, .cds--data-table-container)) {
    margin-block: var(--cds-spacing-03) 0;
  }

  /* Carbon gives a paragraph the body-02 size; the text of a message is body-01, the size of the bubble. */
  .markdown :global(:where(p, li, blockquote)) {
    font-size: inherit;
    line-height: inherit;
    letter-spacing: inherit;
  }

  .markdown :global(.markdown-heading) {
    margin-block-start: var(--cds-spacing-05);
  }

  .markdown
    :global(
      :is(p, ul, ol, blockquote, hr, figure, .markdown-heading, .cds--data-table-container, .markdown-code-block):first-child
    ) {
    margin-block-start: 0;
  }

  .markdown :global(.markdown-heading--1) {
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
  }

  .markdown :global(.markdown-heading--2) {
    font-size: var(--cds-heading-02-font-size);
    font-weight: var(--cds-heading-02-font-weight);
    line-height: var(--cds-heading-02-line-height);
  }

  .markdown :global(:is(.markdown-heading--3, .markdown-heading--4, .markdown-heading--5, .markdown-heading--6)) {
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
  }

  .markdown :global(strong) {
    font-weight: 600;
  }

  .markdown :global(em) {
    font-style: italic;
  }

  .markdown :global(.markdown-list) {
    padding-inline-start: var(--cds-spacing-06);
  }

  .markdown :global(ul.markdown-list) {
    list-style: disc;
  }

  .markdown :global(ol.markdown-list) {
    list-style: decimal;
  }

  .markdown :global(.markdown-list > li + li) {
    margin-block-start: var(--cds-spacing-02);
  }

  .markdown :global(.markdown-quote) {
    padding-inline-start: var(--cds-spacing-04);
    border-inline-start: 3px solid var(--cds-border-strong-01);
    color: var(--cds-text-secondary);
  }

  .markdown :global(.markdown-rule) {
    border: 0;
    border-block-start: 1px solid var(--cds-border-subtle-01);
  }
</style>
