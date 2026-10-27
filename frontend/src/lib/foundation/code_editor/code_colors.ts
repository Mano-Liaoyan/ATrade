// Code colors of the editor and the diff, for the light (Carbon g10) and the dark (Carbon g100) theme. The values are
// colors of the Carbon palette (@carbon/colors). The background is --cds-layer-01 of the theme, plain text is
// --cds-text-primary, and comments are --cds-text-secondary. Each text color has WCAG AA contrast (4.5:1 or more) on
// the background (code_colors.test.ts).
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
    background: '#ffffff', // white: g10 layer-01
    text: {
      plain: '#161616', // gray 100: g10 text-primary
      comment: '#525252', // gray 70: g10 text-secondary
      keyword: '#9f1853', // magenta 70
      string: '#0e6027', // green 70
      number: '#0043ce', // blue 70
      function: '#6929c4', // purple 70
      type: '#8a3800', // orange 70
    },
  },
  dark: {
    background: '#262626', // gray 90: g100 layer-01
    text: {
      plain: '#f4f4f4', // gray 10: g100 text-primary
      comment: '#c6c6c6', // gray 30: g100 text-secondary
      keyword: '#ff7eb6', // magenta 40
      string: '#42be65', // green 40
      number: '#78a9ff', // blue 40
      function: '#be95ff', // purple 40
      type: '#ff832b', // orange 40
    },
  },
};
