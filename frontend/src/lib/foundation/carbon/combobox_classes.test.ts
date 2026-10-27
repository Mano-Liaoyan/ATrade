// Changes the Bits UI combobox state into the Carbon combo box classes.
import { describe, expect, it } from 'vite-plus/test';
import { toComboboxClasses, toComboboxItemClasses } from './combobox_classes';

describe('toComboboxClasses', () => {
  it('gives the closed combo box only the base classes', () => {
    expect(toComboboxClasses({ open: false, hasItems: true, invalid: false })).toEqual(['cds--combo-box', 'cds--list-box']);
  });

  it('expands the list box when it is open and has candidates', () => {
    expect(toComboboxClasses({ open: true, hasItems: true, invalid: false })).toEqual([
      'cds--combo-box',
      'cds--list-box',
      'cds--list-box--expanded',
    ]);
  });

  it('does not expand an open list box with no candidates', () => {
    expect(toComboboxClasses({ open: true, hasItems: false, invalid: false })).toEqual(['cds--combo-box', 'cds--list-box']);
  });

  it('marks an invalid combo box', () => {
    expect(toComboboxClasses({ open: false, hasItems: false, invalid: true })).toEqual([
      'cds--combo-box',
      'cds--list-box',
      'cds--combo-box--invalid',
    ]);
  });
});

describe('toComboboxItemClasses', () => {
  it('gives a plain candidate the menu item class', () => {
    expect(toComboboxItemClasses({ highlighted: false, disabled: false })).toEqual(['cds--list-box__menu-item']);
  });

  it('marks the highlighted candidate', () => {
    expect(toComboboxItemClasses({ highlighted: true, disabled: false })).toEqual([
      'cds--list-box__menu-item',
      'cds--list-box__menu-item--highlighted',
    ]);
  });

  // Carbon styles a disabled candidate by its `disabled` attribute, not by a class.
  it('never highlights a disabled candidate', () => {
    expect(toComboboxItemClasses({ highlighted: true, disabled: true })).toEqual(['cds--list-box__menu-item']);
  });
});
