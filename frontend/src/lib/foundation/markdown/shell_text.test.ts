// A shell block shows each command after a prompt. Copy copies only the commands, without the prompt.
import { describe, expect, it } from 'vite-plus/test';
import { shellCopyText, shellLines } from './shell_text';

describe('shellLines', () => {
  it('makes each line a command when the block has no prompt', () => {
    expect(shellLines('cd frontend\npnpm install')).toEqual([
      { kind: 'command', text: 'cd frontend' },
      { kind: 'command', text: 'pnpm install' },
    ]);
  });

  it('removes the prompt; a line without a prompt is output; a line after a backslash continues the command', () => {
    expect(shellLines('$ ls \\\n  -la\nREADME.md\n$ pwd')).toEqual([
      { kind: 'command', text: 'ls \\' },
      { kind: 'continuation', text: '  -la' },
      { kind: 'output', text: 'README.md' },
      { kind: 'command', text: 'pwd' },
    ]);
  });

  it('keeps comment lines and blank lines as they are', () => {
    expect(shellLines('# install\npnpm install\n\npnpm test')).toEqual([
      { kind: 'comment', text: '# install' },
      { kind: 'command', text: 'pnpm install' },
      { kind: 'output', text: '' },
      { kind: 'command', text: 'pnpm test' },
    ]);
  });
});

describe('shellCopyText', () => {
  it('copies the commands without the prompt and without the output', () => {
    expect(shellCopyText('$ ls \\\n  -la\nREADME.md\n$ pwd\n/home')).toBe('ls \\\n  -la\npwd');
  });

  it('copies a block without prompts as it is', () => {
    expect(shellCopyText('# install\npnpm install')).toBe('# install\npnpm install');
  });
});
