<!-- The blocks of a markdown text. A list item and a block quote hold blocks, so this component renders itself. -->
<script lang="ts">
  import CodeBlock from './CodeBlock.svelte';
  import DiffBlock from './DiffBlock.svelte';
  import MarkdownInline from './MarkdownInline.svelte';
  import MarkdownTable from './MarkdownTable.svelte';
  import MermaidBlock from './MermaidBlock.svelte';
  import Self from './MarkdownBlocks.svelte';
  import type { MarkdownBlock } from './markdown_blocks';

  interface Props {
    blocks: readonly MarkdownBlock[];
  }

  const { blocks }: Props = $props();
</script>

{#each blocks as block, index (index)}
  {#if block.kind === 'heading'}
    <svelte:element this={`h${String(block.level)}`} class={['markdown-heading', `markdown-heading--${String(block.level)}`]}
      ><MarkdownInline inlines={block.children} /></svelte:element
    >
  {:else if block.kind === 'paragraph'}
    <p><MarkdownInline inlines={block.children} /></p>
  {:else if block.kind === 'list'}
    <svelte:element this={block.ordered ? 'ol' : 'ul'} class="markdown-list" start={block.ordered ? block.start : undefined}>
      {#each block.items as item, itemIndex (itemIndex)}
        <li><Self blocks={item} /></li>
      {/each}
    </svelte:element>
  {:else if block.kind === 'quote'}
    <blockquote class="markdown-quote"><Self blocks={block.blocks} /></blockquote>
  {:else if block.kind === 'table'}
    <MarkdownTable columns={block.columns} header={block.header} rows={block.rows} />
  {:else if block.kind === 'rule'}
    <hr class="markdown-rule" />
  {:else if block.display === 'diff'}
    <DiffBlock language={block.language} text={block.text} closed={block.closed} />
  {:else if block.display === 'mermaid'}
    <MermaidBlock text={block.text} closed={block.closed} />
  {:else}
    <CodeBlock language={block.language} text={block.text} closed={block.closed} display={block.display} />
  {/if}
{/each}
