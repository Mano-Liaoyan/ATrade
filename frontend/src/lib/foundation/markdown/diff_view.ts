// The diff view of a markdown diff block (FileDiff of @pierre/diffs) and the file view of a markdown code block (File
// of @pierre/diffs). Both load the library on demand (diffs_library.ts) and use its Carbon theme.
import type { FileDiffMetadata } from '@pierre/diffs';
import { DIFFS_THEME_NAME, loadDiffsLibrary } from './diffs_library';

export interface DiffView {
  destroy: () => void;
}

/**
 * Shows the diff in the element, with `headerEnd` at the end of the file header line. Returns undefined when the text
 * has no file diff with a hunk.
 */
export type CreateDiffView = (element: HTMLElement, text: string, headerEnd: HTMLElement) => DiffView | undefined;

/** Shows the code in the element with syntax colors: no file header and no line numbers. */
export type CreateFileView = (element: HTMLElement, text: string, language: string) => DiffView;

let diffViewLoad: Promise<CreateDiffView> | undefined;
let fileViewLoad: Promise<CreateFileView> | undefined;

async function loadDiff(): Promise<CreateDiffView> {
  const { FileDiff, parsePatchFiles } = await loadDiffsLibrary();
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
      theme: DIFFS_THEME_NAME,
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

async function loadFile(): Promise<CreateFileView> {
  const { File } = await loadDiffsLibrary();
  return (element, text, language) => {
    const view = new File({
      theme: DIFFS_THEME_NAME,
      overflow: 'scroll',
      disableFileHeader: true,
      disableLineNumbers: true,
    });
    view.render({ file: { name: `code.${language}`, contents: text, lang: language }, containerWrapper: element });
    return {
      destroy: () => {
        view.cleanUp();
        element.replaceChildren();
      },
    };
  };
}

export function loadDiffView(): Promise<CreateDiffView> {
  diffViewLoad ??= loadDiff();
  return diffViewLoad;
}

export function loadFileView(): Promise<CreateFileView> {
  fileViewLoad ??= loadFile();
  return fileViewLoad;
}
