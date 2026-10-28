// Public entry of foundation/polling: the one polling loop of the pages (lists of backtests, details of a running test).
// A page starts it in an $effect and returns the stop function, so a navigation or a new read ends the old loop.

/**
 * Calls `read` at once. Each result goes to `onResult`; when `onResult` returns true, `read` runs again after
 * `intervalMilliseconds`. The returned function stops the loop: no result reaches `onResult` after it.
 */
export function startPolling<T>(
  read: () => Promise<T>,
  onResult: (value: T) => boolean,
  intervalMilliseconds: number,
): () => void {
  let isActive = true;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function readOnce(): Promise<void> {
    const value = await read();
    if (!isActive) {
      return;
    }
    if (onResult(value)) {
      timer = setTimeout(() => void readOnce(), intervalMilliseconds);
    }
  }

  void readOnce();
  return () => {
    isActive = false;
    clearTimeout(timer);
  };
}
