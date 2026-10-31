// The diff view of a markdown diff block: FileDiff of @pierre/diffs (the vanilla JavaScript API; its React API is not
// used). The page loads the library only when a closed diff block needs it.
import type { FileDiffMetadata } from '@pierre/diffs';

export interface DiffView {
  destroy: () => void;
}

/**
 * Shows the diff in the element, with `headerEnd` at the end of the file header line. Returns undefined when the text
 * has no file diff with a hunk.
 */
export type CreateDiffView = (element: HTMLElement, text: string, headerEnd: HTMLElement) => DiffView | undefined;

const THEME_NAME = 'atrade-carbon';
let loaded: Promise<CreateDiffView> | undefined;

async function load(): Promise<CreateDiffView> {
  const { FileDiff, parsePatchFiles, registerCustomCSSVariableTheme } = await import('@pierre/diffs');
  // The theme colors are the --diffs-token-* variables of markdown.scss, so a theme change needs no new render.
  registerCustomCSSVariableTheme(THEME_NAME, {});
  return (element, text, headerEnd) => {
    let fileDiff: FileDiffMetadata | undefined;
    try {
      fileDiff = parsePatchFiles(text, undefined, true).flatMap((patch) => patch.files)[0];
    } catch {
      return undefined;
    }
    if (fileDiff === undefined || fileDiff.hunks.length === 0) {
      return undefined;
    }
    const view = new FileDiff({
      theme: THEME_NAME,
      diffStyle: 'unified',
      diffIndicators: 'classic',
      overflow: 'scroll',
      hunkSeparators: 'simple',
      renderHeaderMetadata: () => headerEnd,
    });
    view.render({ fileDiff, containerWrapper: element });
    return {
      destroy: () => {
        view.cleanUp();
        element.replaceChildren();
      },
    };
  };
}

export function loadDiffView(): Promise<CreateDiffView> {
  loaded ??= load();
  return loaded;
}
