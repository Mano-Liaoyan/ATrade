<!-- The custom indicators of the Settings page (docs/architecture/indicator.md section 23.10): a table, and dialogs that
     create, change, and delete. The backend checks each save: a problem shows at its field. A custom indicator of the AI
     assistant has a Keep button until the user keeps it, then a "Kept" status icon. /ws/custom-indicators pushes each
     change, also from the AI assistant. The table scrolls in its own ScrollRegion. -->
<script lang="ts">
  import Checkmark16 from '@carbon/icons/es/checkmark/16.js';
  import Edit16 from '@carbon/icons/es/edit/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { Button, DataTable, Dialog, IconButton, InlineNotification, Select, StatusIndicator, TextInput, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import type { RequestResult } from '#lib/foundation/http_request';
  import { readOnChange } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    CUSTOM_INDICATORS_SOCKET_PATH,
    deleteCustomIndicator,
    keepCustomIndicator,
    listCustomIndicators,
    saveCustomIndicator,
    type CustomIndicator,
    type CustomIndicatorFields,
    type CustomIndicatorProblems,
  } from './custom_indicators';

  const COLUMNS: TableColumn[] = [
    { header: 'Name' },
    { header: 'Expression' },
    { header: 'Keep', isMenu: true },
    { header: 'Change', isMenu: true },
    { header: 'Delete', isMenu: true },
  ];
  const PLACEMENT_ITEMS = [
    { value: 'own', label: 'Own pane' },
    { value: 'price', label: 'Price pane' },
  ];
  const EXPRESSION_NOTE = 'open high low close volume, + - * / **, mean max min sum std lag abs log, catalog keys: close / sma(50) - 1';
  const NEW_FIELDS: CustomIndicatorFields = { name: '', expression: '', chart_placement: 'own', value_description: '' };

  let indicators = $state<CustomIndicator[] | null>(null);
  let readFailedMessage = $state<string | null>(null);
  let isDialogOpen = $state(false);
  // The row that the dialog changes. Null: the dialog creates a new one.
  let editedId = $state<number | null>(null);
  let fields = $state<CustomIndicatorFields>({ ...NEW_FIELDS });
  let problems = $state<CustomIndicatorProblems>({});
  let saveMessage = $state<string | null>(null);
  let isSaving = $state(false);
  let toDelete = $state<CustomIndicator | null>(null);
  let deleteMessage = $state<string | null>(null);
  let isDeleting = $state(false);
  let keepMessage = $state<string | null>(null);
  let form = $state<HTMLFormElement>();

  function showIndicators(result: RequestResult<CustomIndicator[]>): void {
    if (result.kind === 'failed') {
      readFailedMessage = result.message;
      return;
    }
    readFailedMessage = null;
    indicators = result.value;
  }

  async function readIndicators(): Promise<void> {
    showIndicators(await listCustomIndicators(fetch));
  }

  $effect(() =>
    readOnChange({
      socketPath: CUSTOM_INDICATORS_SOCKET_PATH,
      read: () => listCustomIndicators(fetch),
      onResult: showIndicators,
    }),
  );

  function openDialog(indicator: CustomIndicator | null): void {
    editedId = indicator?.custom_indicator_id ?? null;
    const { name, expression, chart_placement, value_description } = indicator ?? NEW_FIELDS;
    fields = { name, expression, chart_placement, value_description };
    problems = {};
    saveMessage = null;
    isDialogOpen = true;
  }

  async function save(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    isSaving = true;
    const result = await saveCustomIndicator(fetch, editedId, $state.snapshot(fields));
    isSaving = false;
    if (result.kind === 'refused') {
      problems = result.problems;
      return;
    }
    if (result.kind === 'failed') {
      saveMessage = result.message;
      return;
    }
    isDialogOpen = false;
    await readIndicators();
  }

  async function keepIndicator(indicator: CustomIndicator): Promise<void> {
    const result = await keepCustomIndicator(fetch, indicator.custom_indicator_id);
    keepMessage = result.kind === 'failed' ? result.message : null;
    await readIndicators();
  }

  async function deleteIndicator(indicator: CustomIndicator): Promise<void> {
    isDeleting = true;
    const result = await deleteCustomIndicator(fetch, indicator.custom_indicator_id);
    isDeleting = false;
    if (result.kind === 'failed') {
      deleteMessage = result.message;
      return;
    }
    toDelete = null;
    await readIndicators();
  }
</script>

<section class="editor" aria-labelledby="custom-indicators-heading">
  <div class="heading-row">
    <h2 id="custom-indicators-heading">Custom indicators</h2>
    <Button
      size="sm"
      onclick={() => {
        openDialog(null);
      }}>New custom indicator</Button
    >
  </div>
  {#if keepMessage !== null}
    <InlineNotification kind="error" title="Custom indicator not kept" subtitle={keepMessage} lowContrast />
  {/if}
  {#if readFailedMessage !== null}
    <InlineNotification kind="error" title="Custom indicators not read" subtitle={readFailedMessage} lowContrast />
  {:else if indicators === null}
    <EmptyText text="Loading" role="status" />
  {:else if indicators.length === 0}
    <EmptyText text="No custom indicators" />
  {:else}
    {@const listedIndicators = indicators}
    <ScrollRegion label="Custom indicators table" maxHeight="24rem">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each listedIndicators as indicator (indicator.custom_indicator_id)}
            <tr>
              <th scope="row">
                {#if indicator.kept && indicator.assistant_conversation_id !== null}
                  <StatusIndicator label="Kept" kind="success" />
                {/if}
                {indicator.name}
              </th>
              <td class="expression">{indicator.expression}</td>
              <td class="cds--table-column-menu">
                {#if !indicator.kept}
                  <IconButton
                    label={`Keep ${indicator.name}`}
                    icon={Checkmark16}
                    align="left"
                    onclick={() => {
                      void keepIndicator(indicator);
                    }}
                  />
                {/if}
              </td>
              <td class="cds--table-column-menu">
                <IconButton
                  label={`Change ${indicator.name}`}
                  icon={Edit16}
                  align="left"
                  onclick={() => {
                    openDialog(indicator);
                  }}
                />
              </td>
              <td class="cds--table-column-menu">
                <IconButton
                  label={`Delete ${indicator.name}`}
                  icon={TrashCan16}
                  align="left"
                  onclick={() => {
                    deleteMessage = null;
                    toDelete = indicator;
                  }}
                />
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</section>

<Dialog
  open={isDialogOpen}
  onOpenChange={(open: boolean) => {
    isDialogOpen = open;
  }}
  title={editedId === null ? 'New custom indicator' : 'Change custom indicator'}
  size="md"
  primaryText={isSaving ? 'Saving…' : 'Save custom indicator'}
  busy={isSaving}
  onPrimary={() => form?.requestSubmit()}
>
  <form
    class="fields"
    aria-label="Custom indicator"
    bind:this={form}
    onsubmit={(event) => {
      void save(event);
    }}
  >
    <TextInput label="Name" bind:value={fields.name} invalidText={problems['name'] ?? null} autocomplete="off" />
    <TextInput
      label="Expression"
      class="expression"
      bind:value={fields.expression}
      invalidText={problems['expression'] ?? null}
      noteText={EXPRESSION_NOTE}
      autocomplete="off"
      spellcheck="false"
    />
    <Select
      label="Chart pane"
      items={PLACEMENT_ITEMS}
      value={fields.chart_placement}
      onValueChange={(value: string) => {
        fields.chart_placement = value;
      }}
    />
    <TextInput label="Value description" bind:value={fields.value_description} invalidText={problems['value_description'] ?? null} autocomplete="off" />
  </form>
  {#if saveMessage !== null}
    <InlineNotification kind="error" lowContrast title="Custom indicator not saved" subtitle={saveMessage} />
  {/if}
</Dialog>

<Dialog
  open={toDelete !== null}
  onOpenChange={(open: boolean) => {
    if (!open) {
      toDelete = null;
    }
  }}
  title={`Delete ${toDelete?.name ?? ''}`}
  primaryText={isDeleting ? 'Deleting…' : 'Delete custom indicator'}
  primaryKind="danger"
  busy={isDeleting}
  onPrimary={() => {
    if (toDelete !== null) {
      void deleteIndicator(toDelete);
    }
  }}
>
  {#if deleteMessage !== null}
    <InlineNotification kind="error" lowContrast title="Custom indicator not deleted" subtitle={deleteMessage} />
  {/if}
</Dialog>

<style>
  .editor {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    max-inline-size: 60rem;
  }

  .heading-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--cds-spacing-05);
  }

  h2 {
    margin: 0;
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }

  .fields {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding-block-end: var(--cds-spacing-05);
  }

  .expression,
  .fields :global(.expression) {
    font-family: var(--cds-code-02-font-family);
    overflow-wrap: anywhere;
  }
</style>
