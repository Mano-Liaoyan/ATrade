// A double-click on an empty part of a panel header line maximizes the panel. A double-click on a control does not.
import { describe, expect, it } from 'vite-plus/test';
import { isEmptyHeaderPart } from './index';

interface FakeElement {
  closest: (selector: string) => FakeElement | null;
}

function createTarget(isInControl: boolean): FakeElement {
  return { closest: () => (isInControl ? createTarget(true) : null) };
}

describe('isEmptyHeaderPart', () => {
  it('accepts a target that is not in a control', () => {
    expect(isEmptyHeaderPart(createTarget(false))).toBe(true);
  });

  it('refuses a target in a button, a tab, a link, or a switcher', () => {
    expect(isEmptyHeaderPart(createTarget(true))).toBe(false);
  });

  it('refuses a target that is not an element', () => {
    expect(isEmptyHeaderPart(null)).toBe(false);
  });
});
