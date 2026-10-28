// The one polling loop of the pages: read, show the result, and read again after an interval while the result asks for it.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import { startPolling } from './index';

const INTERVAL_MILLISECONDS = 1000;

describe('startPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('reads at once and reads again after the interval while onResult returns true', async () => {
    const results = [1, 2, 3];
    const read = vi.fn(() => Promise.resolve(results.shift() ?? 0));
    const seen: number[] = [];

    startPolling(
      read,
      (value) => {
        seen.push(value);
        return value < 2;
      },
      INTERVAL_MILLISECONDS,
      vi.fn(),
    );
    await vi.advanceTimersByTimeAsync(0);
    expect(seen).toEqual([1]);

    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS);
    expect(seen).toEqual([1, 2]);

    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS * 3);
    expect(read).toHaveBeenCalledTimes(2);
  });

  it('after stop, gives no result and reads no more', async () => {
    const read = vi.fn(() => Promise.resolve('value'));
    const onResult = vi.fn(() => true);

    const stop = startPolling(read, onResult, INTERVAL_MILLISECONDS, vi.fn());
    stop();
    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS * 3);

    expect(onResult).not.toHaveBeenCalled();
    expect(read).toHaveBeenCalledTimes(1);
  });

  it('a failed read gives its message to onFailure and reads again after the interval', async () => {
    const read = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new Error('Network down'))
      .mockResolvedValue('value');
    const onResult = vi.fn(() => false);
    const onFailure = vi.fn();

    startPolling(read, onResult, INTERVAL_MILLISECONDS, onFailure);
    await vi.advanceTimersByTimeAsync(0);
    expect(onFailure).toHaveBeenCalledWith('Network down');
    expect(onResult).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS);
    expect(onResult).toHaveBeenCalledWith('value');
  });

  it('an error in onResult goes to onFailure, and the loop reads again', async () => {
    const read = vi.fn(() => Promise.resolve('value'));
    const onFailure = vi.fn();

    startPolling(
      read,
      () => {
        throw new Error('Bad value');
      },
      INTERVAL_MILLISECONDS,
      onFailure,
    );
    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS);

    expect(onFailure).toHaveBeenCalledWith('Bad value');
    expect(read).toHaveBeenCalledTimes(2);
  });

  it('a stop between 2 reads cancels the next read', async () => {
    const read = vi.fn(() => Promise.resolve('value'));

    const stop = startPolling(read, () => true, INTERVAL_MILLISECONDS, vi.fn());
    await vi.advanceTimersByTimeAsync(0);
    stop();
    await vi.advanceTimersByTimeAsync(INTERVAL_MILLISECONDS * 3);

    expect(read).toHaveBeenCalledTimes(1);
  });
});
