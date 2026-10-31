// The one load of @pierre/diffs (the vanilla JavaScript API; its React API is not used) for all markdown code: the
// diff view, the file view of a code block, and the tokens of a shell block. All three use the shared highlighter of
// @pierre/diffs and one theme, so the page has one highlighter. The page loads the library only when a closed block
// needs it.
// The theme colors are the --diffs-* variables of markdown.scss, so a theme change needs no new render.

type DiffsLibrary = typeof import('@pierre/diffs');

export const DIFFS_THEME_NAME = 'atrade-carbon';

let loaded: Promise<DiffsLibrary> | undefined;

export function loadDiffsLibrary(): Promise<DiffsLibrary> {
  loaded ??= import('@pierre/diffs').then((library) => {
    library.registerCustomCSSVariableTheme(DIFFS_THEME_NAME, {});
    return library;
  });
  return loaded;
}
