// The lines of a shell code block. A block with prompts ("$ " or "% ") shows commands and their output; a block
// without prompts is all commands. Copy copies the commands without the prompt and without the output.

export interface ShellLine {
  /** `continuation` follows a command line that ends with a backslash. */
  kind: 'command' | 'continuation' | 'comment' | 'output';
  /** The line text without the prompt. */
  text: string;
}

const PROMPT = /^[$%] /;

export function shellLines(text: string): ShellLine[] {
  const lines = text.split('\n');
  const hasPrompts = lines.some((line) => PROMPT.test(line));
  const result: ShellLine[] = [];
  let continues = false;
  for (const line of lines) {
    let shellLine: ShellLine;
    if (continues) {
      shellLine = { kind: 'continuation', text: line };
    } else if (hasPrompts) {
      shellLine = PROMPT.test(line) ? { kind: 'command', text: line.replace(PROMPT, '') } : { kind: 'output', text: line };
    } else if (line.trim() === '') {
      shellLine = { kind: 'output', text: line };
    } else if (line.trimStart().startsWith('#')) {
      shellLine = { kind: 'comment', text: line };
    } else {
      shellLine = { kind: 'command', text: line };
    }
    continues = shellLine.kind !== 'output' && shellLine.kind !== 'comment' && line.endsWith('\\');
    result.push(shellLine);
  }
  return result;
}

/** The text that Copy puts on the clipboard. */
export function shellCopyText(text: string): string {
  if (!text.split('\n').some((line) => PROMPT.test(line))) {
    return text;
  }
  return shellLines(text)
    .filter((line) => line.kind === 'command' || line.kind === 'continuation')
    .map((line) => line.text)
    .join('\n');
}
