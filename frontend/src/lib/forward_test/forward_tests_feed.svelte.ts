// The running forward tests on instruments from /ws/forward-tests, and the socket connection state. A page with the
// paper order form uses it: a running forward test blocks paper orders by hand on its instrument. `forwardTests` is
// the full list of the last message, for example for the Stop forward test button of the strategy page.
import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
import {
  FORWARD_TESTS_SOCKET_PATH,
  listForwardTestsOnInstruments,
  readForwardTestsMessage,
  type ForwardTest,
} from './forward_test_api';

export class ForwardTestsOnInstrumentsFeed {
  onInstruments = $state<{ label: string; symbol: string; exchange: string }[]>([]);
  forwardTests = $state<ForwardTest[]>([]);
  isConnected = $state(false);

  /** Opens the socket. Returns the stop function, for the return value of an $effect. */
  start(location: { protocol: string; host: string }): () => void {
    return openLiveSocket({
      url: buildSocketUrl(FORWARD_TESTS_SOCKET_PATH, location),
      onMessage: (message) => {
        const forwardTests = readForwardTestsMessage(message);
        if (forwardTests !== null) {
          this.forwardTests = forwardTests;
          this.onInstruments = listForwardTestsOnInstruments(forwardTests);
        }
      },
      onConnectionChange: (isConnected) => {
        this.isConnected = isConnected;
      },
    });
  }
}
