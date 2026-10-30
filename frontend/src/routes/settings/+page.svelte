<!-- Settings page (docs/architecture.md section 13): the source order of the bar sources and the HK instrument list
     editor. -->
<script lang="ts">
  import { HkInstrumentListEditor, SourceOrderList } from '#lib/market_data';
</script>

<div class="settings">
  <h1>Settings</h1>
  <SourceOrderList />
  <section aria-labelledby="hk-instrument-list-heading">
    <h2 id="hk-instrument-list-heading">HK instrument list</h2>
    <HkInstrumentListEditor />
  </section>
</div>

<style>
  .settings {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-07);
  }

  h2 {
    margin-block: 0 var(--cds-spacing-05);
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }
</style>
