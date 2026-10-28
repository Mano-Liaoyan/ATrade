// Public entry of foundation/polling: the one polling loop of the pages (lists of backtests, details of a running test).
// A page starts it in an $effect and returns the stop function, so a navigation or a new read ends the old loop.

/**
 * Calls `read` at once. Each result goes to `onResult`; when `onResult` returns true, `read` runs again after
 * `intervalMilliseconds`. A read that throws or rejects, or an `onResult` that throws, gives its message to
 * `onFailure` (the page shows it, AGENTS.md State) and the loop reads again after the interval. The returned function
 * stops the loop: no result and no failure reach the callbacks after it.
 */
export function startPolling<T>(
  read: () => Promise<T>,
  onResult: (value: T) => boolean,
  intervalMilliseconds: number,
  onFailure: (message: string) => void,
): () => void {
  let isActive = true;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function readOnce(): Promise<void> {
    let readsAgain: boolean;
    try {
      const value = await read();
      if (!isActive) {
        return;
      }
      readsAgain = onResult(value);
    } catch (error: unknown) {
      if (!isActive) {
        return;
      }
      onFailure(error instanceof Error ? error.message : String(error));
      readsAgain = true;
    }
    if (readsAgain) {
      timer = setTimeout(() => void readOnce(), intervalMilliseconds);
    }
  }

  void readOnce();
  return () => {
    isActive = false;
    clearTimeout(timer);
  };
}
