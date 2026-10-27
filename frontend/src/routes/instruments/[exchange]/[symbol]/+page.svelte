<!-- Instrument page: a watchlist instrument opens here. It is a placeholder until the bar chart ticket (#65) adds
     the chart of the instrument to this page. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';

  const symbol = $derived(page.params['symbol'] ?? '');
  const exchange = $derived(page.params['exchange'] ?? '');
  const currency = $derived(page.url.searchParams.get('currency') ?? '');
</script>

<h1>{symbol} / {exchange} / {currency}</h1>
<p>The bar chart of this instrument is not available yet.</p>
<a href={resolve('/')}>Back to the watchlist</a>
