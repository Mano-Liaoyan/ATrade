<!-- App shell: header with the product name, the backend status, and the IB Gateway status, and the main region for each page. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { resolve } from '$app/paths';
  import {
    describeBackendHealth,
    fetchBackendHealth,
    SERVER_TIME_TICK_MILLISECONDS,
    type BackendHealth,
  } from '#lib/foundation/backend_health';
  import {
    describeGatewayStatus,
    fetchGatewayStatus,
    GATEWAY_STATUS_REFRESH_MILLISECONDS,
    type GatewayStatus,
  } from '#lib/ibkr';

  const { children }: { children: Snippet } = $props();

  let backendHealth: BackendHealth = $state({ kind: 'checking' });
  let gatewayStatus: GatewayStatus = $state({ kind: 'checking' });
  let nowMilliseconds = $state(Date.now());

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
</script>

<div class="app-shell">
  <header class="app-header">
    <span class="product-name">ATrade</span>
    <nav class="app-navigation">
      <a href={resolve('/')}>Home</a>
      <a href={resolve('/strategies')}>Strategies</a>
      <a href={resolve('/backtests')}>Backtests</a>
      <a href={resolve('/forward-tests')}>Forward tests</a>
    </nav>
    <span class="header-statuses">
      <span class="backend-status" role="status" aria-label="Backend status">{describeBackendHealth(backendHealth, nowMilliseconds)}</span>
      <span
        class="gateway-status"
        class:gateway-unreachable={gatewayStatus.kind === 'unreachable'}
        role="status"
        aria-label="IB Gateway status"
      >
        {describeGatewayStatus(gatewayStatus)}
      </span>
    </span>
  </header>
  <main class="app-main">
    {@render children()}
  </main>
</div>

<style>
  :global(:root) {
    --color-background: #f6f7f9;
    --color-surface: #ffffff;
    --color-text: #1b1f24;
    --color-muted: #59636e;
    --color-border: #d0d7de;
    --color-warning: #9a6700;
    --color-accent: #0969da;
    /* Code editor and code diff (src/lib/foundation/code_editor/code_theme.ts). */
    --color-code-active-line: #eaeef280;
    --color-code-selection: #0969da33;
    --color-diff-removed-line: #ffebe9;
    --color-diff-removed-text: #ff818266;
    --color-diff-removed-mark: #cf222e;
    --color-diff-added-line: #dafbe1;
    --color-diff-added-text: #4ac26b66;
    --color-diff-added-mark: #1a7f37;
    color-scheme: light dark;
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  }

  @media (prefers-color-scheme: dark) {
    :global(:root) {
      --color-background: #0d1117;
      --color-surface: #161b22;
      --color-text: #e6edf3;
      --color-muted: #8d96a0;
      --color-border: #30363d;
      --color-warning: #d29922;
      --color-accent: #4493f8;
      --color-code-active-line: #6e768126;
      --color-code-selection: #4493f84d;
      --color-diff-removed-line: #f8514926;
      --color-diff-removed-text: #f8514966;
      --color-diff-removed-mark: #f85149;
      --color-diff-added-line: #2ea04326;
      --color-diff-added-text: #2ea04366;
      --color-diff-added-mark: #3fb950;
    }
  }

  :global(body) {
    margin: 0;
    background: var(--color-background);
    color: var(--color-text);
  }

  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  .app-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem clamp(1rem, 3vw, 2.5rem);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .product-name {
    font-weight: 700;
    font-size: 1.125rem;
  }

  .app-navigation {
    display: flex;
    gap: 1rem;
    margin-right: auto;
  }

  .header-statuses {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.25rem 1rem;
  }

  .backend-status,
  .gateway-status {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .gateway-unreachable {
    color: var(--color-warning);
    font-weight: 600;
  }

  /* The side gutter grows with the window, so page content does not sit near the window edge on wide screens. */
  .app-main {
    flex: 1;
    padding: 1.25rem clamp(1rem, 3vw, 2.5rem);
  }
</style>
