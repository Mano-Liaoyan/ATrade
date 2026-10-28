// PROTOTYPE (#99), throwaway: the ?variant= keys of the workbench prototype.
// "workbench" is the default, so links between prototype pages need no search parameter.

export const PROTOTYPE_VARIANTS = [
  { key: 'workbench', name: '#99' },
  { key: 'current', name: 'PR #98' },
] as const;

export type PrototypeVariant = (typeof PROTOTYPE_VARIANTS)[number]['key'];

export function readPrototypeVariant(searchParams: Pick<URLSearchParams, 'get'>): PrototypeVariant {
  return searchParams.get('variant') === 'current' ? 'current' : 'workbench';
}
