// The Carbon sequential color of a heatmap cell (the monochromatic blue palette of Carbon data visualization).
import { describe, expect, it } from 'vite-plus/test';
import { readSequentialColor } from './sequential_color';

describe('readSequentialColor', () => {
  it('gives Blue 10 with dark text for step 1 and Blue 100 with white text for step 10', () => {
    expect(readSequentialColor(1)).toEqual({ background: '#edf5ff', text: '#161616' });
    expect(readSequentialColor(10)).toEqual({ background: '#001141', text: '#ffffff' });
  });

  it('changes to white text at Blue 60', () => {
    expect(readSequentialColor(5).text).toBe('#161616');
    expect(readSequentialColor(6)).toEqual({ background: '#0f62fe', text: '#ffffff' });
  });
});
