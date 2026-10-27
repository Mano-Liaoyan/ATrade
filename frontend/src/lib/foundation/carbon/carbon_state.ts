// The Carbon state class names for the Bits UI states. Bits UI supplies the behavior (open, highlighted, selected,
// data-state) and Carbon supplies the look, which reads only class names.

export type ButtonKind = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';
// Bits UI Tabs writes data-state="active" on the trigger of the selected tab.
export type BitsTabState = 'active' | 'inactive';

export function buttonClasses({ kind, size, iconOnly = false }: { kind: ButtonKind; size: ButtonSize; iconOnly?: boolean }): string[] {
  // The Carbon default button size is lg: it has no size class. Carbon v11 reads the height of the other sizes from
  // the layout size class.
  const sizeClasses = size === 'lg' ? [] : [`cds--btn--${size}`, `cds--layout--size-${size}`];
  return ['cds--btn', `cds--btn--${kind}`, ...sizeClasses, ...(iconOnly ? ['cds--btn--icon-only'] : [])];
}

export function textInputClasses(invalid: boolean): string[] {
  return ['cds--text-input', ...(invalid ? ['cds--text-input--invalid'] : [])];
}

export function dropdownClasses({ open, disabled }: { open: boolean; disabled: boolean }): string[] {
  return [
    'cds--dropdown',
    'cds--list-box',
    ...(open ? ['cds--list-box--expanded', 'cds--dropdown--open'] : []),
    ...(disabled ? ['cds--dropdown--disabled', 'cds--list-box--disabled'] : []),
  ];
}

export function dropdownMenuIconClasses(open: boolean): string[] {
  return ['cds--list-box__menu-icon', ...(open ? ['cds--list-box__menu-icon--open'] : [])];
}

export function dropdownMenuItemClasses({ highlighted, selected }: { highlighted: boolean; selected: boolean }): string[] {
  return [
    'cds--list-box__menu-item',
    ...(highlighted ? ['cds--list-box__menu-item--highlighted'] : []),
    ...(selected ? ['cds--list-box__menu-item--active'] : []),
  ];
}

export function contentSwitcherButtonClasses(tabState: BitsTabState): string[] {
  return ['cds--content-switcher-btn', ...(tabState === 'active' ? ['cds--content-switcher--selected'] : [])];
}
