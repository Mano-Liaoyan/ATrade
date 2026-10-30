<!-- Settings page: the HK instrument list editor (docs/architecture.md section 13). -->
<script lang="ts">
  import { HkInstrumentListEditor } from '#lib/market_data';
</script>

<h1>Settings</h1>
<section aria-labelledby="hk-instrument-list-heading">
  <h2 id="hk-instrument-list-heading">HK instrument list</h2>
  <HkInstrumentListEditor />
</section>

<style>
  h2 {
    margin-block: 0 var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }
</style>
