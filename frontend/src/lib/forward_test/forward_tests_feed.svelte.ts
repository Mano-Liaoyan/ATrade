// The one /ws/forward-tests feed of a page: all forward tests of the last message and the socket connection state. The
// forward test page uses forwardTests for its list.
import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
import {
  FORWARD_TESTS_SOCKET_PATH,
  readForwardTestsMessage,
  type ForwardTest,
} from './forward_test_api';

export class ForwardTestsOnInstrumentsFeed {
  /** All forward tests of the last socket message, or of a page change (for example a stop request) after it. */
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
        }
      },
      onConnectionChange: (isConnected) => {
        this.isConnected = isConnected;
      },
    });
  }
}
