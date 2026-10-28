<!-- The one empty state of all pages: a short word or two in place of an empty table, list, or panel, for example
     "No trades". No sentence and no full stop: the place around it gives the context (AGENTS.md, Copy). With `role`
     "status", screen readers read a change, for example "Loading". -->
<script lang="ts">
  const { text, role }: { text: string; role?: 'status' } = $props();
</script>

<p class="empty-text" {role}>{text}</p>

<style>
  .empty-text {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }
</style>
