<!-- A Mermaid block of a markdown text. A closed block shows the diagram (pele, loaded on demand). The colors are
     Carbon tokens in the pele CSS variables, so the diagram follows the theme without a new render. While the text
     streams in, and when pele cannot read the text, the block shows the Mermaid code. -->
<script lang="ts">
  import CodeBlock from './CodeBlock.svelte';
  import { mountMermaid, type MermaidView } from './mermaid_view';

  interface Props {
    text: string;
    closed: boolean;
  }

  const { text, closed }: Props = $props();

  const componentId = $props.id();
  const idPrefix = `mermaid-${componentId}-`;
  let container: HTMLDivElement | undefined = $state();
  let phase: 'loading' | 'shown' | 'failed' = $state('loading');

  $effect(() => {
    const source = text;
    const element = container;
    if (!closed || element === undefined) {
      return;
    }
    let view: MermaidView | undefined;
    let current = true;
    phase = 'loading';
    mountMermaid(element, source, idPrefix).then(
      (mounted) => {
        if (current) {
          view = mounted;
          phase = 'shown';
        } else {
          mounted.destroy();
        }
      },
      () => {
        if (current) {
          phase = 'failed';
        }
      },
    );
    return () => {
      current = false;
      view?.destroy();
    };
  });
</script>

{#if closed && phase !== 'failed'}
  <figure
    class={['markdown-mermaid', phase !== 'shown' && 'markdown-mermaid--loading']}
    aria-label="Mermaid diagram"
    aria-hidden={phase !== 'shown'}
  >
    <div class="markdown-mermaid__diagram" bind:this={container}></div>
  </figure>
{/if}
{#if !closed || phase !== 'shown'}
  <CodeBlock language="mermaid" {text} {closed} display="code" />
{/if}

<style>
  .markdown-mermaid {
    min-inline-size: 0;
    margin: 0;
    padding: var(--cds-spacing-04);
    overflow-x: auto;
    background-color: var(--cds-layer-01);
    box-shadow: inset 0 0 0 1px var(--cds-border-subtle-01);
    scrollbar-width: thin;
    scrollbar-color: var(--cds-icon-secondary) var(--cds-layer-accent-01);
  }

  .markdown-mermaid::-webkit-scrollbar {
    height: var(--cds-spacing-03);
  }

  .markdown-mermaid::-webkit-scrollbar-track {
    background: var(--cds-layer-accent-01);
  }

  .markdown-mermaid::-webkit-scrollbar-thumb {
    background: var(--cds-icon-secondary);
  }

  /* The diagram renders in the hidden figure; the code block shows until it is ready. */
  .markdown-mermaid--loading {
    block-size: 0;
    padding-block: 0;
    overflow: hidden;
    visibility: hidden;
  }

  /* pele reads these variables. Carbon tokens only. */
  .markdown-mermaid__diagram {
    --pele-bg: transparent;
    --pele-fg: var(--cds-text-primary);
    --pele-muted: var(--cds-text-secondary);
    --pele-line: var(--cds-border-strong-01);
    --pele-surface: var(--cds-layer-02);
    --pele-surface-alt: var(--cds-layer-accent-01);
    --pele-border: var(--cds-border-strong-01);
    --pele-accent: var(--cds-interactive);
    --pele-font: var(--cds-body-compact-01-font-family, 'IBM Plex Sans', sans-serif);
    --pele-radius: 0;
  }
</style>
