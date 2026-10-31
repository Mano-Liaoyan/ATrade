// The lines of a diff block that the diff view cannot read (no hunk, or the fence is still open).
import { describe, expect, it } from 'vite-plus/test';
import { diffLines } from './diff_lines';

describe('diffLines', () => {
  it('gives each line its kind and keeps the + and - markers in the text', () => {
    expect(diffLines('--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n keep\n-old\n+new')).toEqual([
      { kind: 'header', text: '--- a/x.py' },
      { kind: 'header', text: '+++ b/x.py' },
      { kind: 'hunk', text: '@@ -1,2 +1,2 @@' },
      { kind: 'context', text: ' keep' },
      { kind: 'removed', text: '-old' },
      { kind: 'added', text: '+new' },
    ]);
  });
});
