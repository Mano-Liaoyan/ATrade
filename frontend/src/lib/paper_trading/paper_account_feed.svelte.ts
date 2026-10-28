// The live paper account from /ws/paper-trading: the account check with the balance and the positions, the open
// orders, the filled orders by hand of today, and the socket connection state. Each page that shows the paper account
// uses this feed, so all of them show "Live updates paused" when the socket is not connected.
import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
import { PAPER_TRADING_SOCKET_PATH, readPaperAccountMessage, type PaperAccountMessage } from './paper_account';
import { readFilledManualOrders, readOpenOrdersMessage, type ManualOrder, type OpenOrder } from './paper_orders';

export class PaperAccountFeed {
  account = $state<PaperAccountMessage | null>(null);
  openOrders = $state<OpenOrder[]>([]);
  filledOrders = $state<ManualOrder[]>([]);
  isConnected = $state(false);

  /** Opens the socket and reads the filled orders. Returns the stop function, for the return value of an $effect. */
  start(fetchFunction: typeof fetch, location: { protocol: string; host: string }): () => void {
    // A fill changes the open orders, and the server sends the orders message only after a change.
    const refreshFilledOrders = async (): Promise<void> => {
      const orders = await readFilledManualOrders(fetchFunction);
      if (orders !== null) {
        this.filledOrders = orders;
      }
    };
    void refreshFilledOrders();
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
          void refreshFilledOrders();
        }
      },
      onConnectionChange: (isConnected) => {
        this.isConnected = isConnected;
      },
    });
  }
}
