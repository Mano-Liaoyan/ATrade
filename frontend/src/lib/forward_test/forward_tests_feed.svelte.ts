// The one /ws/forward-tests feed of a page: all forward tests of the last message, the running forward tests on
// instruments, and the socket connection state. A page with the paper order form uses onInstruments: a running forward
// test blocks paper orders by hand on its instrument. The forward test page uses forwardTests for its list.
import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
import {
  FORWARD_TESTS_SOCKET_PATH,
  listForwardTestsOnInstruments,
  readForwardTestsMessage,
  type ForwardTest,
} from './forward_test_api';

export class ForwardTestsOnInstrumentsFeed {
  /** All forward tests of the last socket message. */
  forwardTests = $state<ForwardTest[]>([]);
  onInstruments = $state<{ label: string; symbol: string; exchange: string }[]>([]);
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
