// The lines of a diff block for the plain diff view: while the fence is open, and when the diff view of
// @pierre/diffs cannot read the diff. Each line keeps its + or - marker, so the change does not show by color only.

export interface DiffLine {
  kind: 'header' | 'hunk' | 'added' | 'removed' | 'context';
  text: string;
}

const HEADER = /^(?:diff --git |index |--- |\+\+\+ |new file mode |deleted file mode |similarity index |rename (?:from|to) )/;

export function diffLines(text: string): DiffLine[] {
  return text.split('\n').map((line): DiffLine => {
    if (HEADER.test(line)) {
      return { kind: 'header', text: line };
    }
    if (line.startsWith('@@')) {
      return { kind: 'hunk', text: line };
    }
    if (line.startsWith('+')) {
      return { kind: 'added', text: line };
    }
    if (line.startsWith('-')) {
      return { kind: 'removed', text: line };
    }
    return { kind: 'context', text: line };
  });
}
