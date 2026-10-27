// Public entry of foundation/color_scheme: the theme choice of the header theme button, and the watch that tells a
// component when the light or dark color tokens change (docs/architecture.md section 13).
// The tokens on :root follow prefers-color-scheme, and data-theme="light" or "dark" on <html> overrides it
// (foundation/carbon/carbon.scss). CSS takes a change at once, but a canvas chart and the code editor read the colors
// only when they draw, so they must read them again.

export {
  applyThemeChoice,
  isDarkColorScheme,
  nextThemeChoice,
  readAppliedThemeChoice,
  readThemeChoice,
  saveThemeChoice,
  selectThemeChoice,
  THEME_STORAGE_KEY,
  type ThemeChoice,
  watchColorScheme,
} from './theme_choice';
export { default as ThemeButton } from './ThemeButton.svelte';
