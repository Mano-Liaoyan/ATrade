// Changes the Bits UI combobox state into the Carbon combo box classes. Carbon CSS shows a state with a class.

// One candidate of the combo box. `value` is unique in the list and `label` is the shown text.
export interface ComboboxItem {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface ComboboxState {
  open: boolean;
  hasItems: boolean;
  invalid: boolean;
}

export interface ComboboxItemState {
  highlighted: boolean;
  disabled: boolean;
}

export function toComboboxClasses(state: ComboboxState): string[] {
  const classes = ['cds--combo-box', 'cds--list-box'];
  // Carbon shows the menu only on an expanded list box. An open list with no candidates stays closed.
  if (state.open && state.hasItems) {
    classes.push('cds--list-box--expanded');
  }
  if (state.invalid) {
    classes.push('cds--combo-box--invalid');
  }
  return classes;
}

export function toComboboxItemClasses(state: ComboboxItemState): string[] {
  const classes = ['cds--list-box__menu-item'];
  if (state.highlighted && !state.disabled) {
    classes.push('cds--list-box__menu-item--highlighted');
  }
  return classes;
}
