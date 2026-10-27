// Public entry of foundation/color_scheme: tells a component when the light or dark color tokens change.
// The tokens on :root follow prefers-color-scheme (src/routes/+layout.svelte). CSS takes a change at once, but a
// canvas chart reads the colors only when it draws, so it must read them again (docs/architecture.md 13.1).

const DARK_SCHEME_QUERY = '(prefers-color-scheme: dark)';

/** Calls `onChange` after each change of the color scheme. Returns the function that ends the watch. */
export function watchColorScheme(onChange: () => void): () => void {
  const darkSchemeQuery = window.matchMedia(DARK_SCHEME_QUERY);
  darkSchemeQuery.addEventListener('change', onChange);
  return () => {
    darkSchemeQuery.removeEventListener('change', onChange);
  };
}
