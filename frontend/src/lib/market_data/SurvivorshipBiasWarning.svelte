<!-- The one survivorship bias warning of all pages: a Carbon warning with its icon and the warning color
     (docs/architecture/market_data.md section 8.10). The title is short. The tooltip tells what is missing. The
     backtest page, the screen page, and the multi-instrument backtest form use it. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
</script>

<InlineNotification
  kind="warning"
  title="Survivorship bias"
  tooltip="Instruments that stopped trading are missing from the universe."
  lowContrast
/>
