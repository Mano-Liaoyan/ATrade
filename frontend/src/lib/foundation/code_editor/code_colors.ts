// Code colors of the editor and the diff, for the light (Carbon g10) and the dark (Carbon g100) theme. Carbon has no
// syntax color tokens, so the syntax colors come from the Carbon palette (@carbon/colors): grade 70 on g10 and grade 40
// on g100. Plain text is the text-primary token and comments are the text-secondary token of the theme
// (@carbon/themes). Each text color has WCAG AA contrast (4.5:1 or more) on the layer-01 token, the editor background
// (code_colors.test.ts).
import { blue40, blue70, green40, green70, magenta40, magenta70, orange40, orange70, purple40, purple70 } from '@carbon/colors';
import { g10, g100 } from '@carbon/themes';

export interface CodeColorScheme {
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
    text: {
      plain: g10.textPrimary,
      comment: g10.textSecondary,
      keyword: magenta70,
      string: green70,
      number: blue70,
      function: purple70,
      type: orange70,
    },
  },
  dark: {
    text: {
      plain: g100.textPrimary,
      comment: g100.textSecondary,
      keyword: magenta40,
      string: green40,
      number: blue40,
      function: purple40,
      type: orange40,
    },
  },
};
