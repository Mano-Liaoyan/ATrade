// A double-click on an empty part of a panel header line maximizes the panel, like in VS Code. A double-click on a
// control of the line (a button, a tab, a link, a switcher, a field) does only what the control does.

const HEADER_CONTROLS = 'button, a, input, select, textarea, [role="tab"], [role="tablist"], [role="separator"]';

interface ClosestTarget {
  closest: (selector: string) => unknown;
}

function hasClosest(target: unknown): target is ClosestTarget {
  return typeof target === 'object' && target !== null && typeof (target as Partial<ClosestTarget>).closest === 'function';
}

export function isEmptyHeaderPart(target: unknown): boolean {
  return hasClosest(target) && target.closest(HEADER_CONTROLS) === null;
}
