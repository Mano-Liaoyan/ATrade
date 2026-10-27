// The Bits UI states (open, highlighted, selected, data-state) become the Carbon state class names.
import { describe, expect, it } from 'vite-plus/test';
import {
  buttonClasses,
  contentSwitcherButtonClasses,
  dropdownClasses,
  dropdownMenuIconClasses,
  dropdownMenuItemClasses,
  textInputClasses,
} from './carbon_state';

describe('dropdownClasses', () => {
  it('has only the base classes when the select is closed', () => {
    expect(dropdownClasses({ open: false, disabled: false })).toEqual(['cds--dropdown', 'cds--list-box']);
  });

  it('expands the list box and opens the dropdown when Bits UI opens the select', () => {
    expect(dropdownClasses({ open: true, disabled: false })).toEqual([
      'cds--dropdown',
      'cds--list-box',
      'cds--list-box--expanded',
      'cds--dropdown--open',
    ]);
  });

  it('shows the disabled state', () => {
    expect(dropdownClasses({ open: false, disabled: true })).toEqual([
      'cds--dropdown',
      'cds--list-box',
      'cds--dropdown--disabled',
      'cds--list-box--disabled',
    ]);
  });
});

describe('dropdownMenuIconClasses', () => {
  it('turns the chevron when the select is open', () => {
    expect(dropdownMenuIconClasses(false)).toEqual(['cds--list-box__menu-icon']);
    expect(dropdownMenuIconClasses(true)).toEqual(['cds--list-box__menu-icon', 'cds--list-box__menu-icon--open']);
  });
});

describe('dropdownMenuItemClasses', () => {
  it('marks the highlighted item and the selected item', () => {
    expect(dropdownMenuItemClasses({ highlighted: false, selected: false })).toEqual(['cds--list-box__menu-item']);
    expect(dropdownMenuItemClasses({ highlighted: true, selected: false })).toEqual([
      'cds--list-box__menu-item',
      'cds--list-box__menu-item--highlighted',
    ]);
    expect(dropdownMenuItemClasses({ highlighted: true, selected: true })).toEqual([
      'cds--list-box__menu-item',
      'cds--list-box__menu-item--highlighted',
      'cds--list-box__menu-item--active',
    ]);
  });
});

describe('contentSwitcherButtonClasses', () => {
  it('selects the button of the active Bits UI tab', () => {
    expect(contentSwitcherButtonClasses('active')).toEqual(['cds--content-switcher-btn', 'cds--content-switcher--selected']);
    expect(contentSwitcherButtonClasses('inactive')).toEqual(['cds--content-switcher-btn']);
  });
});

describe('buttonClasses', () => {
  it('writes the kind and the size', () => {
    expect(buttonClasses({ kind: 'primary', size: 'lg' })).toEqual(['cds--btn', 'cds--btn--primary']);
    // Carbon v11 reads the button height from the layout size class.
    expect(buttonClasses({ kind: 'secondary', size: 'md' })).toEqual([
      'cds--btn',
      'cds--btn--secondary',
      'cds--btn--md',
      'cds--layout--size-md',
    ]);
    expect(buttonClasses({ kind: 'ghost', size: 'sm', iconOnly: true })).toEqual([
      'cds--btn',
      'cds--btn--ghost',
      'cds--btn--sm',
      'cds--layout--size-sm',
      'cds--btn--icon-only',
    ]);
  });
});

describe('textInputClasses', () => {
  it('marks an invalid input', () => {
    expect(textInputClasses(false)).toEqual(['cds--text-input']);
    expect(textInputClasses(true)).toEqual(['cds--text-input', 'cds--text-input--invalid']);
  });
});
