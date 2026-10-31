// Calls the sweep HTTP routes and returns each answer as a result that the sweep pages can show.
import { describe, expect, it } from 'vite-plus/test';
import { readSweep, readSweepParameters } from './index';

describe('readSweep', () => {
  it('reads the sweep at its route', async () => {
    let calledPath = '';
    const recordingFetch: typeof fetch = (path) => {
      calledPath = path as string;
      return Promise.resolve(new Response(JSON.stringify({ id: 4, runs: [] }), { status: 200 }));
    };

    const result = await readSweep(recordingFetch, 4);

    expect(calledPath).toBe('/api/sweeps/4');
    expect(result).toEqual({ kind: 'ok', value: { id: 4, runs: [] } });
  });
});

describe('readSweepParameters', () => {
  it('reads the parameters of a strategy version', async () => {
    let calledPath = '';
    const recordingFetch: typeof fetch = (path) => {
      calledPath = path as string;
      return Promise.resolve(new Response(JSON.stringify({ parameters: [] }), { status: 200 }));
    };

    await readSweepParameters(recordingFetch, 7);

    expect(calledPath).toBe('/api/sweeps/parameters?strategy_version_id=7');
  });
});
