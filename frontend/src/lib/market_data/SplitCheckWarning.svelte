<!-- The warning of a backtest that used instruments that waited for the IBKR stock split check: a Carbon warning with
     its icon and the warning color (docs/architecture/backtest.md section 10.12). The tooltip tells what can be
     wrong. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
</script>

<InlineNotification
  kind="warning"
  title="IBKR stock split check not done"
  tooltip="Some instruments waited for the IBKR stock split check. Their bars before a stock split can have the old prices."
  lowContrast
/>
