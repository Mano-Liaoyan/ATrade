<!-- App shell: the Carbon UI shell header (product name, page navigation, the Paper tag, a divider, then the header
     actions: the Connections button, the command palette, the theme button, and the Log out button behind Cloudflare
     Access) and the main region for each page. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import {
    fetchBackendHealth,
    readServerClock,
    SERVER_TIME_TICK_MILLISECONDS,
    type BackendHealth,
  } from '#lib/foundation/backend_health';
  import { LogOutButton } from '#lib/foundation/access_session';
  import { Tag, Tooltip, TooltipProvider } from '#lib/foundation/carbon';
  import { ThemeButton } from '#lib/foundation/color_scheme';
  import { CommandPalette } from '#lib/foundation/command_palette';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import {
    fetchGatewayStatus,
    GATEWAY_STATUS_REFRESH_MILLISECONDS,
    type GatewayStatus,
  } from '#lib/ibkr';
  import {
    describePaperAccountTag,
    PAPER_TRADING_SOCKET_PATH,
    readPaperAccountMessage,
    type PaperAccountCheck,
  } from '#lib/paper_trading';
  import { listWatchlist, type WatchlistInstrument } from '#lib/watchlist';
  import HeaderConnections from './HeaderConnections.svelte';
  import { summarizeConnections } from './header_connections';
  import { createPaletteCommandGroups } from './palette_commands';

  const { children }: { children: Snippet } = $props();

  const PAGE_LINKS = [
    { label: 'Home', href: resolve('/') },
    { label: 'Screens', href: resolve('/screens/[[screenId]]', {}) },
    { label: 'Strategies', href: resolve('/strategies') },
    { label: 'Backtests', href: resolve('/backtests/[[backtestId]]', {}) },
    { label: 'Parameter sweeps', href: resolve('/sweeps/[[sweepId]]', {}) },
    { label: 'Forward tests', href: resolve('/forward-tests/[[forwardTestId]]', {}) },
    { label: 'Settings', href: resolve('/settings') },
  ];
  const HOME_HREF = resolve('/');

  let backendHealth: BackendHealth = $state({ kind: 'checking' });
  let gatewayStatus: GatewayStatus = $state({ kind: 'checking' });
  let paperAccountCheck: PaperAccountCheck | null = $state(null);
  let nowMilliseconds = $state(Date.now());
  let paletteWatchlist: WatchlistInstrument[] = $state([]);
  let paletteWatchlistReading = $state(false);
  const serverClock = $derived(readServerClock(backendHealth, nowMilliseconds));
  const connections = $derived(summarizeConnections(backendHealth, gatewayStatus, serverClock));
  const paletteCommandGroups = $derived(createPaletteCommandGroups(paletteWatchlist));

  // The palette reads the watchlist each time it opens, so it shows the instruments that the user added since.
  function readPaletteWatchlist(): void {
    paletteWatchlistReading = true;
    void listWatchlist(fetch).then((listResult) => {
      if (listResult.kind === 'ok') {
        paletteWatchlist = listResult.value;
      }
      paletteWatchlistReading = false;
    });
  }

  // A page link is current on its own page and on the pages below it. Home is current only on its own page.
  function isCurrentPage(href: string, pathname: string): boolean {
    if (href === HOME_HREF) {
      return pathname === HOME_HREF;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  $effect(() => {
    void fetchBackendHealth(fetch).then((health) => {
      backendHealth = health;
    });
  });

  $effect(() => {
    const tickTimer = setInterval(() => {
      nowMilliseconds = Date.now();
    }, SERVER_TIME_TICK_MILLISECONDS);
    return () => {
      clearInterval(tickTimer);
    };
  });

  $effect(() => {
    function refreshGatewayStatus(): void {
      void fetchGatewayStatus(fetch).then((status) => {
        gatewayStatus = status;
      });
    }
    refreshGatewayStatus();
    const refreshTimer = setInterval(refreshGatewayStatus, GATEWAY_STATUS_REFRESH_MILLISECONDS);
    return () => {
      clearInterval(refreshTimer);
    };
  });

  // The Paper tag names the checked paper account. The account check comes from /ws/paper-trading.
  $effect(() => {
    return openLiveSocket({
      url: buildSocketUrl(PAPER_TRADING_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const accountMessage = readPaperAccountMessage(message);
        if (accountMessage !== null) {
          paperAccountCheck = accountMessage.check;
        }
      },
      onConnectionChange: () => undefined,
    });
  });
</script>

<TooltipProvider>
  <header class="cds--header cds--g100" aria-label="ATrade">
    <a class="cds--header__name" href={HOME_HREF}>ATrade</a>
    <nav class="cds--header__nav app-navigation" aria-label="Pages">
      <ul class="cds--header__menu-bar">
        {#each PAGE_LINKS as link (link.href)}
          <li>
            <a
              class="cds--header__menu-item"
              href={link.href}
              aria-current={isCurrentPage(link.href, page.url.pathname) ? 'page' : undefined}
            >
              {link.label}
            </a>
          </li>
        {/each}
      </ul>
    </nav>
    <div class="cds--header__global app-header-global">
      <Tooltip text={describePaperAccountTag(paperAccountCheck)} align="bottom-end">
        {#snippet trigger({ props })}
          <Tag {...props} label="Paper" kind="blue" operational />
        {/snippet}
      </Tooltip>
      <span class="app-header-divider" aria-hidden="true"></span>
      <HeaderConnections {connections} />
      <CommandPalette groups={paletteCommandGroups} onOpen={readPaletteWatchlist} busy={paletteWatchlistReading} />
      <ThemeButton />
      <LogOutButton />
    </div>
  </header>
  <main class="app-main">
    {@render children()}
  </main>
</TooltipProvider>

<style>
  /* Carbon hides the header navigation below the lg breakpoint (1056px). ATrade is a desktop app and keeps it. */
  .app-navigation {
    display: block;
  }

  /* The Paper tag, a divider, then the header actions side by side without gaps. */
  .app-header-global {
    align-items: center;
    min-inline-size: 0;
    padding-inline-start: var(--cds-spacing-05);
  }

  /* ATrade header actions are 40px cells (Carbon uses 48px), so the icon buttons after the divider sit close. */
  .app-header-global :global(.cds--header__action) {
    inline-size: var(--cds-spacing-08);
  }

  .app-header-divider {
    inline-size: 1px;
    block-size: var(--cds-spacing-06);
    margin-inline: var(--cds-spacing-04) var(--cds-spacing-03);
    background: var(--cds-border-subtle);
  }

  /* A header tooltip is the light Carbon high-contrast bubble. On the light page, the Carbon popover drop shadow
     separates it from the page background. */
  .app-header-global :global(.cds--popover--high-contrast .cds--popover) {
    filter: var(--cds-popover-drop-shadow, drop-shadow(0 var(--cds-spacing-01) var(--cds-spacing-01) rgb(0 0 0 / 20%)));
  }

  /* The page heading of each document page. A workbench gives its headings their own style. */
  .app-main:not(:has(:global(.atrade-workbench))) :global(h1) {
    margin-block: 0 var(--cds-spacing-06);
    font-size: var(--cds-heading-04-font-size);
    font-weight: var(--cds-heading-04-font-weight);
    line-height: var(--cds-heading-04-line-height);
    letter-spacing: var(--cds-heading-04-letter-spacing);
  }

  /* The Carbon header is fixed at the top and is 3rem high. */
  .app-main {
    padding: calc(var(--cds-spacing-09) + var(--cds-spacing-06)) var(--cds-spacing-07) var(--cds-spacing-06);
  }

  /* A workbench page (foundation/workbench) is exactly the window height below the header and does not scroll as a
     page. Each region of the workbench scrolls in itself. */
  .app-main:has(:global(.atrade-workbench)) {
    box-sizing: border-box;
    block-size: 100vh;
    padding: var(--cds-spacing-09) 0 0;
    overflow: hidden;
  }
</style>
