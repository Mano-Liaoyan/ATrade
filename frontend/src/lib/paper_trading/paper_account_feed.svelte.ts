// The live paper account from /ws/paper-trading: the account check with the balance and the positions, the open
// orders, the filled orders by hand of today, and the socket connection state. This is one module object: the layout
// starts it, and the pages only read it, so the app has one socket. Each page that shows the paper account uses this
// feed, so all of them show "Live updates paused" when the socket is not connected.
import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
import { PAPER_TRADING_SOCKET_PATH, readPaperAccountMessage, type PaperAccountMessage } from './paper_account';
import { readFilledManualOrders, readOpenOrdersMessage, type ManualOrder, type OpenOrder } from './paper_orders';

class PaperAccountFeed {
  account = $state<PaperAccountMessage | null>(null);
  openOrders = $state<OpenOrder[]>([]);
  filledOrders = $state<ManualOrder[]>([]);
  isConnected = $state(false);

  /** Reads the filled orders. A page that shows them calls this each time it opens. */
  async refreshFilledOrders(fetchFunction: typeof fetch): Promise<void> {
    const orders = await readFilledManualOrders(fetchFunction);
    if (orders !== null) {
      this.filledOrders = orders;
    }
  }

  /** Opens the socket. Returns the stop function, for the return value of an $effect. */
  start(fetchFunction: typeof fetch, location: { protocol: string; host: string }): () => void {
    return openLiveSocket({
      url: buildSocketUrl(PAPER_TRADING_SOCKET_PATH, location),
      onMessage: (message) => {
        const accountMessage = readPaperAccountMessage(message);
        if (accountMessage !== null) {
          this.account = accountMessage;
        }
        const ordersMessage = readOpenOrdersMessage(message);
        if (ordersMessage !== null) {
          this.openOrders = ordersMessage;
          // A fill changes the open orders, and the server sends the orders message only after a change.
          void this.refreshFilledOrders(fetchFunction);
        }
      },
      onConnectionChange: (isConnected) => {
        this.isConnected = isConnected;
      },
    });
  }
}

export const paperAccountFeed = new PaperAccountFeed();
