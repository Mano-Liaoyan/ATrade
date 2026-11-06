// Public entry of the language server connection of the editor. This entry is separate from #lib/strategy because
// @codemirror/lsp-client has no sideEffects field: through the #lib/strategy barrel, it adds CodeMirror to each page.
export { connectStrategyLanguageServer, type LanguageServerConnection } from './strategy_language_server';
