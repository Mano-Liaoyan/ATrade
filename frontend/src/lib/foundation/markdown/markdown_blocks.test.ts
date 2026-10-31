// The blocks of an AI assistant message: markdown text, with sanitized links, tables, and code blocks that can be
// shell commands, diffs, or Mermaid diagrams. The text streams in, so a block can be incomplete.
import { describe, expect, it } from 'vite-plus/test';
import { parseMarkdown } from './markdown_blocks';

describe('parseMarkdown', () => {
  it('reads a heading and a paragraph with bold and italic text', () => {
    expect(parseMarkdown('### Result\n\nThe **Sharpe ratio** is *high*.')).toEqual([
      { kind: 'heading', level: 3, children: [{ kind: 'text', text: 'Result' }] },
      {
        kind: 'paragraph',
        children: [
          { kind: 'text', text: 'The ' },
          { kind: 'strong', children: [{ kind: 'text', text: 'Sharpe ratio' }] },
          { kind: 'text', text: ' is ' },
          { kind: 'emphasis', children: [{ kind: 'text', text: 'high' }] },
          { kind: 'text', text: '.' },
        ],
      },
    ]);
  });

  it('keeps raw HTML as text', () => {
    expect(parseMarkdown('<img src=x onerror=alert(1)>\n\nA <b>bold</b> word')).toEqual([
      { kind: 'paragraph', children: [{ kind: 'text', text: '<img src=x onerror=alert(1)>' }] },
      { kind: 'paragraph', children: [{ kind: 'text', text: 'A <b>bold</b> word' }] },
    ]);
  });

  it('keeps only http, https, and mailto links, and no image loads', () => {
    const [paragraph] = parseMarkdown(
      '[docs](https://example.com/a) [bad](javascript:alert(1)) [data](data:text/html,x) ![chart](https://example.com/c.png)',
    );
    expect(paragraph).toEqual({
      kind: 'paragraph',
      children: [
        { kind: 'link', href: 'https://example.com/a', children: [{ kind: 'text', text: 'docs' }] },
        { kind: 'text', text: ' ' },
        { kind: 'link', href: null, children: [{ kind: 'text', text: 'bad' }] },
        { kind: 'text', text: ' ' },
        { kind: 'link', href: null, children: [{ kind: 'text', text: 'data' }] },
        { kind: 'text', text: ' ' },
        { kind: 'link', href: 'https://example.com/c.png', children: [{ kind: 'text', text: 'chart' }] },
      ],
    });
  });

  it('reads a GFM table; a column of numbers is right aligned', () => {
    expect(parseMarkdown('| Symbol | Return |\n|---|---|\n| AAPL | 12.5% |\n| MSFT | -3,200 |')).toEqual([
      {
        kind: 'table',
        columns: [
          { align: 'left', isNumber: false },
          { align: 'right', isNumber: true },
        ],
        header: [[{ kind: 'text', text: 'Symbol' }], [{ kind: 'text', text: 'Return' }]],
        rows: [
          [[{ kind: 'text', text: 'AAPL' }], [{ kind: 'text', text: '12.5%' }]],
          [[{ kind: 'text', text: 'MSFT' }], [{ kind: 'text', text: '-3,200' }]],
        ],
      },
    ]);
  });

  it('shows a half table that streams in as text, without an error', () => {
    expect(parseMarkdown('| Symbol | Ret')).toEqual([{ kind: 'paragraph', children: [{ kind: 'text', text: '| Symbol | Ret' }] }]);
  });

  it('marks a code fence that is not closed yet', () => {
    expect(parseMarkdown('Run:\n\n```python\nprint(1)\n')).toEqual([
      { kind: 'paragraph', children: [{ kind: 'text', text: 'Run:' }] },
      { kind: 'code', language: 'python', text: 'print(1)', closed: false, display: 'code' },
    ]);
    expect(parseMarkdown('```python\nprint(1)\n```')).toEqual([
      { kind: 'code', language: 'python', text: 'print(1)', closed: true, display: 'code' },
    ]);
    expect(parseMarkdown('```')).toEqual([{ kind: 'code', language: '', text: '', closed: false, display: 'code' }]);
  });

  it('gives each code block its display: shell, diff, Mermaid, or code', () => {
    const displays = (text: string): string[] =>
      parseMarkdown(text).flatMap((block) => (block.kind === 'code' ? [block.display] : []));
    expect(displays('```bash\nls\n```\n\n```console\n$ ls\n```\n\n```zsh\nls\n```')).toEqual(['shell', 'shell', 'shell']);
    expect(displays('```diff\n-a\n+b\n```')).toEqual(['diff']);
    expect(displays('```\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n```')).toEqual(['diff']);
    expect(displays('```mermaid\nflowchart LR\n  A --> B\n```')).toEqual(['mermaid']);
    expect(displays('```\n-a\n+b\n```')).toEqual(['code']);
  });
});
