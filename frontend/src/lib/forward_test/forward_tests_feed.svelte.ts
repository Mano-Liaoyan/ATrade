// The one forward test list of a page: it reads the list again after each change that /ws/forward-tests pushes, and
// keeps the socket connection state. The strategy page and the comparison page use it. The forward test page reads its
// list through routes/run_workbench.svelte.ts.
import { readOnChange } from '#lib/foundation/live_socket';
import { FORWARD_TESTS_SOCKET_PATH, listForwardTests, type ForwardTest } from './forward_test_api';

export class ForwardTestsOnInstrumentsFeed {
  /** All forward tests of the last read, or of a page change (for example a stop request) after it. */
  forwardTests = $state<ForwardTest[]>([]);
  isConnected = $state(false);

  /** Opens the socket. Returns the stop function, for the return value of an $effect. */
  start(fetchFunction: typeof fetch, location: { protocol: string; host: string }): () => void {
    return readOnChange({
      socketPath: FORWARD_TESTS_SOCKET_PATH,
      read: () => listForwardTests(fetchFunction),
      onResult: (result) => {
        // A failed read keeps the last list. The next change or reconnection reads again.
        if (result.kind === 'ok') {
          this.forwardTests = result.value;
        }
      },
      onConnectionChange: (isConnected) => {
        this.isConnected = isConnected;
      },
      location,
    });
  }
}
