// Code colors of the editor and the diff, for the light and the dark color scheme. The values follow the GitHub
// Primer syntax colors, so they match the app color tokens in src/routes/+layout.svelte (--color-surface is the
// background). Each text color has WCAG AA contrast (4.5:1 or more) on the background (code_colors.test.ts).
export interface CodeColorScheme {
  background: string;
  text: {
    plain: string;
    comment: string;
    keyword: string;
    string: string;
    number: string;
    function: string;
    type: string;
  };
}

export const CODE_COLORS: { light: CodeColorScheme; dark: CodeColorScheme } = {
  light: {
    background: '#ffffff',
    text: {
      plain: '#1b1f24',
      comment: '#59636e',
      keyword: '#cf222e',
      string: '#0a3069',
      number: '#0550ae',
      function: '#6639ba',
      type: '#953800',
    },
  },
  dark: {
    background: '#161b22',
    text: {
      plain: '#e6edf3',
      comment: '#8d96a0',
      keyword: '#ff7b72',
      string: '#a5d6ff',
      number: '#79c0ff',
      function: '#d2a8ff',
      type: '#ffa657',
    },
  },
};
