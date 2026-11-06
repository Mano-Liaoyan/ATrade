// Calls the sweep HTTP routes and returns each answer as a result that the sweep pages can show.
import { describe, expect, it } from 'vite-plus/test';
import { deleteSweep, readSweep, readSweepParameters } from './index';

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

describe('deleteSweep', () => {
  it('sends DELETE to the sweep and reports the delete', async () => {
    let sent = '';
    const recordingFetch: typeof fetch = (path, init) => {
      sent = `${init?.method ?? 'GET'} ${path as string}`;
      return Promise.resolve(new Response(null, { status: 204 }));
    };

    expect(await deleteSweep(recordingFetch, 4)).toEqual({ kind: 'deleted' });
    expect(sent).toBe('DELETE /api/sweeps/4');
  });

  it('gives the reason when the backend refuses the delete', async () => {
    const detail = 'Parameter sweep #4 has queued or running runs. Wait for their end.';
    const refusingFetch: typeof fetch = () => Promise.resolve(new Response(JSON.stringify({ detail }), { status: 409 }));

    expect(await deleteSweep(refusingFetch, 4)).toEqual({ kind: 'failed', message: detail });
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
