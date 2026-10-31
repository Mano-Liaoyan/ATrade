// The languages of the markdown code blocks with syntax colors, and the colors of a shell block. The highlighter is
// the shared highlighter of @pierre/diffs (diffs_library.ts), the one highlighter of all markdown code: a code block
// shows in the file view of @pierre/diffs (diff_view.ts), and a shell block uses the tokens of this module, because
// its "$" prompts and output lines are not part of the code. The theme colors are CSS variables (markdown.scss), so a
// theme change needs no new highlight.
import type { SupportedLanguages } from '@pierre/diffs';
import { DIFFS_THEME_NAME, loadDiffsLibrary } from './diffs_library';

export interface CodeToken {
  text: string;
  /** A CSS color: a var() of markdown.scss. */
  color: string | undefined;
}

const LANGUAGE_NAMES: Record<string, SupportedLanguages> = {
  python: 'python',
  py: 'python',
  bash: 'shellscript',
  sh: 'shellscript',
  zsh: 'shellscript',
  shell: 'shellscript',
  console: 'shellscript',
  shellsession: 'shellscript',
  'shell-session': 'shellscript',
  terminal: 'shellscript',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  sql: 'sql',
  typescript: 'typescript',
  ts: 'typescript',
  javascript: 'javascript',
  js: 'javascript',
  toml: 'toml',
};

/** The highlighter language of a fence language, or null when ATrade shows the block without syntax colors. */
export function highlightLanguage(language: string): SupportedLanguages | null {
  return LANGUAGE_NAMES[language] ?? null;
}

/** The tokens of each line, or null when the language has no syntax colors. */
export async function highlightCode(text: string, language: string): Promise<CodeToken[][] | null> {
  const name = highlightLanguage(language);
  if (name === null) {
    return null;
  }
  const { getSharedHighlighter } = await loadDiffsLibrary();
  const highlighter = await getSharedHighlighter({ themes: [DIFFS_THEME_NAME], langs: [name] });
  return highlighter
    .codeToTokens(text, { lang: name, theme: DIFFS_THEME_NAME })
    .tokens.map((line) => line.map((token) => ({ text: token.content, color: token.color })));
}
