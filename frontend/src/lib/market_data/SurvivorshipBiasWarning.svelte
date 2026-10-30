<!-- The one survivorship bias warning of all pages: a Carbon warning with its icon and the warning color
     (docs/architecture/market_data.md section 8.10). The backtest page shows it now. The screen page and the
     multi-instrument backtest form use it too. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
</script>

<InlineNotification
  kind="warning"
  title="The universe has survivorship bias: instruments that stopped trading are missing."
  lowContrast
/>
