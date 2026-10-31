<!-- A code block of a markdown text: the code and a Copy icon button at the top end. The language is the accessible
     name of the block; no label shows. A closed code block with a known language shows in the file view of
     @pierre/diffs (syntax colors, loaded on demand); an open block (the text still streams in) shows plain text, so the
     lines do not flicker. A shell block shows each command after a "$" prompt that Copy does not copy, with the syntax
     colors of the same highlighter. A diff block shows each line with its
     + or - marker and the line color (the plain diff view of DiffBlock). -->
<script lang="ts">
  import CopyButton from './CopyButton.svelte';
  import { highlightCode, highlightLanguage, type CodeToken } from './code_highlight';
  import { loadFileView, type DiffView } from './diff_view';
  import { diffLines } from './diff_lines';
  import { shellCopyText, shellLines } from './shell_text';

  interface Props {
    language: string;
    text: string;
    closed: boolean;
    display: 'code' | 'shell' | 'diff';
  }

  const { language, text, closed, display }: Props = $props();

  const label = $derived(language === '' ? 'code' : language);

  interface Line {
    kind: 'code' | 'command' | 'continuation' | 'comment' | 'output' | 'header' | 'hunk' | 'added' | 'removed' | 'context';
    text: string;
  }

  const lines: Line[] = $derived(
    display === 'shell'
      ? shellLines(text)
      : display === 'diff'
        ? diffLines(text)
        : text.split('\n').map((line) => ({ kind: 'code' as const, text: line })),
  );
  const copyText = $derived(display === 'shell' ? shellCopyText(text) : text);

  // The tokens belong to one text: a later text shows plain until its own tokens arrive.
  let highlighted: { text: string; tokens: CodeToken[][] } | undefined = $state();
  const highlightText = $derived(lines.map((line) => line.text).join('\n'));
  const tokens = $derived(highlighted?.text === highlightText ? highlighted.tokens : undefined);

  // A closed code block renders in the hidden file view; the plain text shows until the file view is ready.
  const fileLanguage = $derived(display === 'code' && closed ? highlightLanguage(language) : null);
  let fileContainer: HTMLDivElement | undefined = $state();
  let fileShown = $state(false);

  $effect(() => {
    const source = text;
    const element = fileContainer;
    const name = fileLanguage;
    if (name === null || element === undefined) {
      return;
    }
    let view: DiffView | undefined;
    let current = true;
    loadFileView().then(
      (createView) => {
        if (current) {
          view = createView(element, source, name);
          fileShown = true;
        }
      },
      () => {
        // The block stays plain text when the file view does not load.
      },
    );
    return () => {
      current = false;
      view?.destroy();
      fileShown = false;
    };
  });

  $effect(() => {
    const source = highlightText;
    if (!closed || display !== 'shell' || highlightLanguage(language) === null) {
      return;
    }
    let current = true;
    highlightCode(source, language).then(
      (result) => {
        if (current && result !== null) {
          highlighted = { text: source, tokens: result };
        }
      },
      () => {
        // The block stays plain text when a grammar does not load.
      },
    );
    return () => {
      current = false;
    };
  });
</script>

<figure class={['markdown-code-block', `markdown-code-block--${display}`]} aria-label={label}>
  <div class="markdown-code-block__copy"><CopyButton text={copyText} /></div>
  {#if fileLanguage !== null}
    <div
      class={['markdown-diffs-view', 'markdown-code-block__file', !fileShown && 'markdown-code-block__file--hidden']}
      aria-hidden={!fileShown}
      bind:this={fileContainer}
    ></div>
  {/if}
  {#if !fileShown}<pre class="markdown-code-block__code"><code
      >{#each lines as line, index (index)}<span class={['markdown-code-block__line', `markdown-code-block__line--${line.kind}`]}
          >{#if line.kind === 'command'}<span class="markdown-code-block__prompt" aria-hidden="true">$ </span
            >{/if}{#if tokens !== undefined && line.kind !== 'output'}{#each tokens[index] ?? [] as token, tokenIndex (tokenIndex)}<span
                style:color={token.color}>{token.text}</span
              >{/each}{:else}{line.text}{/if}</span
        >{/each}</code
    ></pre>{/if}
</figure>

<style>
  .markdown-code-block {
    position: relative;
    min-inline-size: 0;
    margin: 0;
    background-color: var(--cds-layer-01);
    box-shadow: inset 0 0 0 1px var(--cds-border-subtle-01);
  }

  .markdown-code-block__copy {
    position: absolute;
    z-index: 1;
    inset-block-start: 1px;
    inset-inline-end: 1px;
    background-color: var(--cds-layer-01);
  }

  .markdown-code-block__file {
    min-inline-size: 0;
  }

  .markdown-code-block__file--hidden {
    block-size: 0;
    overflow: hidden;
    visibility: hidden;
  }

  .markdown-code-block__code {
    margin: 0;
    padding: var(--cds-spacing-03) 0;
    overflow-x: auto;
    color: var(--diffs-foreground);
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    letter-spacing: var(--cds-code-01-letter-spacing);
    white-space: pre;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-icon-secondary) var(--cds-layer-accent-01);
  }

  .markdown-code-block__code::-webkit-scrollbar {
    height: var(--cds-spacing-03);
  }

  .markdown-code-block__code::-webkit-scrollbar-track {
    background: var(--cds-layer-accent-01);
  }

  .markdown-code-block__code::-webkit-scrollbar-thumb {
    background: var(--cds-icon-secondary);
  }

  .markdown-code-block__code code {
    display: inline-block;
    min-inline-size: 100%;
  }

  .markdown-code-block__line {
    display: block;
    min-block-size: 1lh;
    padding-inline: var(--cds-spacing-04) var(--cds-spacing-08);
  }

  .markdown-code-block__prompt,
  .markdown-code-block__line--output,
  .markdown-code-block__line--comment {
    color: var(--cds-text-secondary);
  }

  .markdown-code-block__prompt {
    user-select: none;
  }

  .markdown-code-block__line--header,
  .markdown-code-block__line--hunk {
    color: var(--cds-text-secondary);
  }

  .markdown-code-block__line--added {
    background-color: color-mix(in srgb, var(--cds-support-success) 15%, transparent);
  }

  .markdown-code-block__line--removed {
    background-color: color-mix(in srgb, var(--cds-support-error) 15%, transparent);
  }
</style>
