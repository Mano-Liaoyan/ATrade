// The blocks of a markdown text (GFM), for the Markdown component. The text is untrusted (an AI assistant message):
// the blocks hold only text, never HTML, so the component renders them with Svelte text nodes. Raw HTML stays text.
// A link keeps only an http, https, or mailto address.
import { Lexer, type Token, type Tokens } from 'marked';

export type MarkdownInline =
  | { kind: 'text'; text: string }
  | { kind: 'strong'; children: MarkdownInline[] }
  | { kind: 'emphasis'; children: MarkdownInline[] }
  | { kind: 'deleted'; children: MarkdownInline[] }
  | { kind: 'code'; text: string }
  /** `href` is null when the address is not http, https, or mailto: the component shows only the text. */
  | { kind: 'link'; href: string | null; children: MarkdownInline[] }
  | { kind: 'break' };

export type CodeDisplay = 'code' | 'shell' | 'diff' | 'mermaid';

export interface TableColumn {
  align: 'left' | 'center' | 'right';
  /** All body cells of the column are numbers: right aligned, tabular numbers. */
  isNumber: boolean;
}

export type MarkdownBlock =
  /** `level` is 1 to 6. */
  | { kind: 'heading'; level: number; children: MarkdownInline[] }
  | { kind: 'paragraph'; children: MarkdownInline[] }
  | { kind: 'list'; ordered: boolean; start: number; items: MarkdownBlock[][] }
  | { kind: 'quote'; blocks: MarkdownBlock[] }
  | {
      kind: 'table';
      columns: TableColumn[];
      header: MarkdownInline[][];
      rows: MarkdownInline[][][];
    }
  | {
      kind: 'code';
      /** The language of the fence, in lower case. Empty when the fence has none. */
      language: string;
      text: string;
      /** False while the closing fence has not arrived (the text streams in). */
      closed: boolean;
      display: CodeDisplay;
    }
  | { kind: 'rule' };

const MAX_HEADING_LEVEL = 6;
const SAFE_LINK = /^(?:https?:\/\/|mailto:)/i;
const SHELL_LANGUAGES = new Set(['bash', 'sh', 'zsh', 'shell', 'console', 'shellsession', 'shell-session', 'terminal']);
const DIFF_LANGUAGES = new Set(['diff', 'patch', 'udiff']);
const OPENING_FENCE = /^ {0,3}(`{3,}|~{3,})/;
const CLOSING_FENCE = /^ {0,3}(`{3,}|~{3,})\s*$/;
// A number cell: an optional sign or currency, digits with separators, decimals, and an optional unit (%, x, bp).
const NUMBER_CELL = /^[+\-−]?[$€£¥]?\d[\d,_ ]*(?:\.\d+)?\s?(?:%|x|bp|k|m|b)?$/i;
const UNIFIED_DIFF_HUNK = /^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@/m;
const UNIFIED_DIFF_START = /^(?:diff --git |--- |Index: )/;

/** Returns the address when the browser may open it, else null. */
export function safeHref(href: string): string | null {
  const trimmed = href.trim();
  return SAFE_LINK.test(trimmed) ? trimmed : null;
}

/** True when a code block without a diff language is a unified diff (file headers and a hunk). */
export function isUnifiedDiff(text: string): boolean {
  return UNIFIED_DIFF_START.test(text) && UNIFIED_DIFF_HUNK.test(text);
}

function codeDisplay(language: string, text: string): CodeDisplay {
  if (language === 'mermaid') {
    return 'mermaid';
  }
  if (DIFF_LANGUAGES.has(language) || (language === '' && isUnifiedDiff(text))) {
    return 'diff';
  }
  if (SHELL_LANGUAGES.has(language)) {
    return 'shell';
  }
  return 'code';
}

function isClosedFence(raw: string): boolean {
  const lines = raw.trimEnd().split('\n');
  const openFence = OPENING_FENCE.exec(lines[0] ?? '')?.[1];
  const closeFence = lines.length > 1 ? CLOSING_FENCE.exec(lines.at(-1) ?? '')?.[1] : undefined;
  if (openFence === undefined || closeFence === undefined) {
    return false;
  }
  return closeFence.startsWith(openFence.charAt(0)) && closeFence.length >= openFence.length;
}

const ENTITIES: Record<string, string> = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };

/** marked escapes some characters in text tokens. Svelte escapes text again, so the blocks hold the plain text. */
function decodeEntities(text: string): string {
  return text.replace(/&(?:amp|lt|gt|quot|#39);/g, (entity) => ENTITIES[entity] ?? entity);
}

type InlineConverter = (token: Token) => MarkdownInline;

const INLINE_CONVERTERS: Partial<Record<string, InlineConverter>> = {
  strong: (token) => ({ kind: 'strong', children: inlines((token as Tokens.Strong).tokens) }),
  em: (token) => ({ kind: 'emphasis', children: inlines((token as Tokens.Em).tokens) }),
  del: (token) => ({ kind: 'deleted', children: inlines((token as Tokens.Del).tokens) }),
  codespan: (token) => ({ kind: 'code', text: decodeEntities((token as Tokens.Codespan).text) }),
  br: () => ({ kind: 'break' }),
  link: (token) => {
    const link = token as Tokens.Link;
    return { kind: 'link', href: safeHref(link.href), children: inlines(link.tokens) };
  },
  // No image loads from an untrusted message: the image is a link with its alternative text.
  image: (token) => {
    const image = token as Tokens.Image;
    return { kind: 'link', href: safeHref(image.href), children: [{ kind: 'text', text: image.text !== '' ? image.text : image.href }] };
  },
  text: (token) => ({ kind: 'text', text: decodeEntities((token as Tokens.Text).text) }),
  escape: (token) => ({ kind: 'text', text: decodeEntities((token as Tokens.Escape).text) }),
};

/** Raw HTML and unknown tokens stay text. */
function toInline(token: Token): MarkdownInline {
  return INLINE_CONVERTERS[token.type]?.(token) ?? { kind: 'text', text: token.raw };
}

function inlines(tokens: readonly Token[] | undefined): MarkdownInline[] {
  const result: MarkdownInline[] = [];
  for (const token of tokens ?? []) {
    // A text token can hold inline tokens (the text of a tight list item).
    const nested = token.type === 'text' ? (token as Tokens.Text).tokens : undefined;
    for (const inline of nested !== undefined && nested.length > 0 ? inlines(nested) : [toInline(token)]) {
      const previous = result.at(-1);
      // marked splits text at some characters; one text node per run keeps the blocks simple.
      if (inline.kind === 'text' && previous?.kind === 'text') {
        previous.text += inline.text;
      } else {
        result.push(inline);
      }
    }
  }
  return result;
}

function plainText(children: readonly MarkdownInline[]): string {
  return children
    .map((child) => {
      switch (child.kind) {
        case 'text':
        case 'code':
          return child.text;
        case 'break':
          return ' ';
        default:
          return plainText(child.children);
      }
    })
    .join('');
}

function tableBlock(table: Tokens.Table): MarkdownBlock {
  const header = table.header.map((cell) => inlines(cell.tokens));
  const rows = table.rows.map((row) => row.map((cell) => inlines(cell.tokens)));
  const columns = header.map((_, index): TableColumn => {
    const cells = rows.map((row) => plainText(row[index] ?? []).trim()).filter((cell) => cell !== '');
    const isNumber = cells.length > 0 && cells.every((cell) => NUMBER_CELL.test(cell));
    const align = table.align[index] ?? null;
    return { align: isNumber ? 'right' : (align ?? 'left'), isNumber };
  });
  return { kind: 'table', columns, header, rows };
}

function codeBlock(code: Tokens.Code): MarkdownBlock {
  const language = (code.lang ?? '').trim().split(/\s+/)[0]?.toLowerCase() ?? '';
  const closed = code.codeBlockStyle === 'indented' || isClosedFence(code.raw);
  return { kind: 'code', language, text: code.text, closed, display: codeDisplay(language, code.text) };
}

type BlockConverter = (token: Token) => MarkdownBlock | null;

const BLOCK_CONVERTERS: Partial<Record<string, BlockConverter>> = {
  space: () => null,
  heading: (token) => {
    const heading = token as Tokens.Heading;
    return {
      kind: 'heading',
      level: Math.min(Math.max(heading.depth, 1), MAX_HEADING_LEVEL),
      children: inlines(heading.tokens),
    };
  },
  paragraph: (token) => ({ kind: 'paragraph', children: inlines((token as Tokens.Paragraph).tokens) }),
  // A text block in a tight list item.
  text: (token) => ({ kind: 'paragraph', children: inlines([token]) }),
  hr: () => ({ kind: 'rule' }),
  blockquote: (token) => ({ kind: 'quote', blocks: blocks((token as Tokens.Blockquote).tokens) }),
  list: (token) => {
    const list = token as Tokens.List;
    return {
      kind: 'list',
      ordered: list.ordered,
      start: typeof list.start === 'number' ? list.start : 1,
      items: list.items.map((item) => blocks(item.tokens)),
    };
  },
  table: (token) => tableBlock(token as Tokens.Table),
  code: (token) => codeBlock(token as Tokens.Code),
};

/** Raw HTML and unknown tokens stay text. */
function toBlock(token: Token): MarkdownBlock | null {
  const converter = BLOCK_CONVERTERS[token.type];
  if (converter !== undefined) {
    return converter(token);
  }
  const text = token.raw.trim();
  return text === '' ? null : { kind: 'paragraph', children: [{ kind: 'text', text }] };
}

function blocks(tokens: readonly Token[]): MarkdownBlock[] {
  return tokens.map(toBlock).filter((block) => block !== null);
}

/** The blocks of a markdown text. A streamed text can end in an open code fence or a half table. */
export function parseMarkdown(text: string): MarkdownBlock[] {
  return blocks(new Lexer({ gfm: true }).lex(text));
}
