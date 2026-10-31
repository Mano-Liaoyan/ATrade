// Syntax highlight of the markdown code blocks with shiki. The page loads shiki and each language only when a closed
// code block needs it, so the first page load does not grow. The theme colors are CSS variables (markdown.scss), so a
// theme change needs no new highlight.
import type { HighlighterCore, LanguageInput, ThemeRegistrationRaw } from 'shiki/core';

export interface CodeToken {
  text: string;
  /** A CSS color: a var() of markdown.scss. */
  color: string | undefined;
}

type LanguageLoader = () => Promise<{ default: LanguageInput }>;

const LANGUAGE_LOADERS: Record<string, LanguageLoader> = {
  python: () => import('shiki/langs/python.mjs'),
  shellscript: () => import('shiki/langs/shellscript.mjs'),
  json: () => import('shiki/langs/json.mjs'),
  yaml: () => import('shiki/langs/yaml.mjs'),
  sql: () => import('shiki/langs/sql.mjs'),
  typescript: () => import('shiki/langs/typescript.mjs'),
  javascript: () => import('shiki/langs/javascript.mjs'),
  toml: () => import('shiki/langs/toml.mjs'),
};

const LANGUAGE_NAMES: Record<string, string> = {
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

const variable = (name: string): string => `var(--diffs-${name})`;

const CARBON_CODE_THEME: ThemeRegistrationRaw = {
  name: 'atrade-carbon',
  type: 'dark',
  fg: variable('foreground'),
  bg: 'transparent',
  settings: [
    { settings: { foreground: variable('foreground'), background: 'transparent' } },
    { scope: ['comment', 'punctuation.definition.comment'], settings: { foreground: variable('token-comment') } },
    { scope: ['keyword', 'storage', 'keyword.control', 'keyword.operator.word'], settings: { foreground: variable('token-keyword') } },
    { scope: ['string', 'string.quoted'], settings: { foreground: variable('token-string') } },
    { scope: ['constant.numeric', 'constant.language', 'constant.character'], settings: { foreground: variable('token-constant') } },
    { scope: ['entity.name.function', 'support.function', 'meta.function-call'], settings: { foreground: variable('token-function') } },
    { scope: ['entity.name.type', 'entity.name.class', 'support.type', 'support.class'], settings: { foreground: variable('token-type') } },
  ],
};

let highlighter: Promise<HighlighterCore> | undefined;
const loadedLanguages = new Map<string, Promise<void>>();

async function loadHighlighter(): Promise<HighlighterCore> {
  const [{ createHighlighterCore }, { createJavaScriptRegexEngine }] = await Promise.all([
    import('shiki/core'),
    import('shiki/engine/javascript'),
  ]);
  return createHighlighterCore({ themes: [CARBON_CODE_THEME], langs: [], engine: createJavaScriptRegexEngine() });
}

/** The shiki language of a fence language, or null when ATrade loads no grammar for it. */
export function highlightLanguage(language: string): string | null {
  return LANGUAGE_NAMES[language] ?? null;
}

/** The tokens of each line, or null when the language has no grammar. */
export async function highlightCode(text: string, language: string): Promise<CodeToken[][] | null> {
  const name = highlightLanguage(language);
  const loader = name === null ? undefined : LANGUAGE_LOADERS[name];
  if (name === null || loader === undefined) {
    return null;
  }
  highlighter ??= loadHighlighter();
  const core = await highlighter;
  let loaded = loadedLanguages.get(name);
  if (loaded === undefined) {
    loaded = loader().then((module) => core.loadLanguage(module.default));
    loadedLanguages.set(name, loaded);
  }
  await loaded;
  return core
    .codeToTokensBase(text, { lang: name, theme: 'atrade-carbon' })
    .map((line) => line.map((token) => ({ text: token.content, color: token.color })));
}
