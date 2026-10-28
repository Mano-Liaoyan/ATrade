<!-- PROTOTYPE (#99), throwaway: a floating bar that switches the ?variant= of the page. Dev builds only. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { PROTOTYPE_VARIANTS, readPrototypeVariant } from './prototype_variant';

  const current = $derived(readPrototypeVariant(page.url.searchParams));
  const currentIndex = $derived(PROTOTYPE_VARIANTS.findIndex((variant) => variant.key === current));

  function step(offset: number): void {
    const next = PROTOTYPE_VARIANTS.at((currentIndex + offset) % PROTOTYPE_VARIANTS.length) ?? PROTOTYPE_VARIANTS[0];
    const url = new URL(page.url.href);
    url.searchParams.set('variant', next.key);
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- same path, only the search changes.
    void goto(url, { replace: true, reset: false });
  }

  function onKeydown(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea, [contenteditable], .cm-editor') !== null && target !== null) {
      return;
    }
    if (event.key === 'ArrowLeft' && event.altKey) {
      step(-1);
    } else if (event.key === 'ArrowRight' && event.altKey) {
      step(1);
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

{#if import.meta.env.DEV}
  <div class="prototype-switcher" role="toolbar" aria-label="Prototype variant">
    <button type="button" aria-label="Previous variant (Alt ←)" onclick={() => {
        step(-1);
      }}>←</button>
    <span>{current} ({PROTOTYPE_VARIANTS[currentIndex]?.name})</span>
    <button type="button" aria-label="Next variant (Alt →)" onclick={() => {
        step(1);
      }}>→</button>
  </div>
{/if}

<style>
  .prototype-switcher {
    position: fixed;
    inset-block-end: 16px;
    inset-inline-start: 50%;
    z-index: 10000;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px;
    border-radius: 999px;
    background: #ff00aa;
    color: #ffffff;
    font: 600 12px/16px 'IBM Plex Mono', monospace;
    box-shadow: 0 2px 8px rgb(0 0 0 / 40%);
    transform: translateX(-50%);
  }

  .prototype-switcher button {
    border: 0;
    border-radius: 999px;
    inline-size: 28px;
    block-size: 28px;
    background: rgb(255 255 255 / 20%);
    color: inherit;
    cursor: pointer;
    font: inherit;
  }
</style>
