// A UTC time from the backend as text.
import { describe, expect, it } from 'vite-plus/test';
import { formatUtcTime } from './index';

describe('formatUtcTime', () => {
  it('shows the date and the time in UTC to the second', () => {
    expect(formatUtcTime('2026-01-02T03:06:00Z')).toBe('2026-01-02 03:06:00 UTC');
    expect(formatUtcTime('2026-01-02T05:06:07+02:00')).toBe('2026-01-02 03:06:07 UTC');
  });
});
