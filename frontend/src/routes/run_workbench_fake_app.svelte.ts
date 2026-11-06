// The reactive fake of $app/state for run_workbench.svelte.test.ts.
export const navigating = $state<{ to: unknown }>({ to: null });
export const page = $state({ url: { hash: '', pathname: '/runs', search: '' } });
