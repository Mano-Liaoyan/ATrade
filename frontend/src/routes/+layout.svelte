<!-- App shell: header with the product name and the backend status, and the main region for each page. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { resolve } from '$app/paths';
  import { describeBackendHealth, fetchBackendHealth, type BackendHealth } from '#lib/foundation/backend_health';

  const { children }: { children: Snippet } = $props();

  let backendHealth: BackendHealth = $state({ kind: 'checking' });

  $effect(() => {
    void fetchBackendHealth(fetch).then((health) => {
      backendHealth = health;
    });
  });
</script>

<div class="app-shell">
  <header class="app-header">
    <span class="product-name">ATrade</span>
    <nav class="app-navigation">
      <a href={resolve('/')}>Home</a>
      <a href={resolve('/strategies')}>Strategies</a>
    </nav>
    <span class="backend-status" role="status">{describeBackendHealth(backendHealth)}</span>
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
    padding: 0.75rem 1rem;
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

  .backend-status {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .app-main {
    flex: 1;
    padding: 1rem;
  }
</style>
