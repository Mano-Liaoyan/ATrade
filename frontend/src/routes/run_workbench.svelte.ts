// The state that the run pages (backtests, parameter sweeps, forward tests) share: the list, the open run, and the
// New dialog. The constructor adds the $effects, so call it while the page component starts.
import { untrack } from 'svelte';
import { goto } from '$app/navigation';
import { navigating, page } from '$app/state';
import type { RequestResult } from '#lib/foundation/http_request';
import { readOnChange } from '#lib/foundation/live_socket';

export interface RunWorkbenchOptions<Item, Detail> {
  /** The /ws/ path of the change socket of the list. */
  socketPath: string;
  list: () => Promise<RequestResult<Item[]>>;
  readDetail: (id: number) => Promise<RequestResult<Detail>>;
  /** The page address of a run. */
  href: (id: number) => string;
  /** The run id in the address, or null. */
  openId: () => number | null;
  /** True: the shown detail of this id does not change any more, so a list row change does not read it again. */
  isFinal?: (detail: Detail, id: number) => boolean;
  /**
   * True: a change on socketPath reads the open run, and a new value comes only after a change of the data. Then a
   * chart keeps its zoom. False (default): a change of the list row of the open run reads it.
   */
  readsDetailOnChange?: boolean;
  /** The address hash (with "#") that opens the New dialog. */
  startHash?: string;
}

export class RunWorkbench<Item extends { id: number }, Detail> {
  /** All runs of the last read, or of a page change after it. */
  items = $state<Item[]>([]);
  isListRead = $state(false);
  isConnected = $state(false);
  listMessage = $state('');
  detail = $state<Detail | null>(null);
  detailMessage = $state('');
  isStartDialogOpen = $state(false);
  #startHash: string | undefined;

  constructor(options: RunWorkbenchOptions<Item, Detail>) {
    this.#startHash = options.startHash;

    $effect(() =>
      readOnChange({
        socketPath: options.socketPath,
        read: options.list,
        onResult: (result) => {
          this.isListRead = true;
          if (result.kind === 'failed') {
            this.listMessage = result.message;
            return;
          }
          this.listMessage = '';
          this.items = result.value;
        },
        onConnectionChange: (isConnected) => {
          this.isConnected = isConnected;
        },
      }),
    );

    // The address without an id opens the newest run. `reset: false` keeps the page state, so an open dialog stays
    // open. A navigation that runs (for example a click on a header link) wins.
    $effect(() => {
      if (navigating.to !== null) {
        return;
      }
      const newest = this.items.reduce<Item | undefined>(
        (found, item) => (found === undefined || item.id > found.id ? item : found),
        undefined,
      );
      if (options.openId() === null && newest !== undefined) {
        // eslint-disable-next-line svelte/no-navigation-without-resolve -- options.href resolves the path.
        void goto(options.href(newest.id), { replace: true, reset: false });
      }
    });

    const openRowText = $derived(JSON.stringify(this.items.find((item) => item.id === options.openId()) ?? null));

    $effect(() => {
      const id = options.openId();
      if (id === null) {
        return;
      }
      if (options.readsDetailOnChange === true) {
        return this.#followDetail(options, id);
      }
      openRowText satisfies string;
      const shown = untrack(() => this.detail);
      if (shown !== null && options.isFinal?.(shown, id) === true) {
        return;
      }
      let isActive = true;
      void options.readDetail(id).then((result) => {
        if (!isActive) {
          return;
        }
        if (result.kind === 'failed') {
          this.detailMessage = result.message;
          return;
        }
        this.detailMessage = '';
        this.detail = result.value;
      });
      return () => {
        isActive = false;
      };
    });

    $effect(() => {
      if (page.url.hash === options.startHash) {
        this.isStartDialogOpen = true;
      }
    });
  }

  changeStartDialog = (open: boolean): void => {
    this.isStartDialogOpen = open;
    if (!open && page.url.hash === this.#startHash) {
      // Without the hash, the palette can open the dialog again.
      // eslint-disable-next-line svelte/no-navigation-without-resolve -- the current path, without its hash.
      void goto(page.url.pathname + page.url.search, { replace: true, reset: false });
    }
  };

  #followDetail(options: RunWorkbenchOptions<Item, Detail>, id: number): () => void {
    let lastDetailText = '';
    return readOnChange({
      socketPath: options.socketPath,
      read: () => options.readDetail(id),
      onResult: (result) => {
        if (result.kind === 'failed') {
          this.detailMessage = result.message;
          return;
        }
        this.detailMessage = '';
        const detailText = JSON.stringify(result.value);
        if (detailText !== lastDetailText) {
          lastDetailText = detailText;
          this.detail = result.value;
        }
      },
    });
  }
}
