<!-- The conversation log of the assistant side column (docs/architecture/assistant.md 25.12.1): the messages, the
     tool steps (one StatusIndicator line each), the diff cards, and the metric cards, in a ChatLog. Each AI assistant
     message shows its model and its credential name. A click on a diff card opens CodeDiff in the editor panel. Keep
     opens the new version in the editor, and Discard adds the discarded mark (25.5.2). -->
<script lang="ts">
  import { describeToolStep, type DiffItem, type LogItem } from '#lib/assistant';
  import { arrangeChatLog, Button, ChatDivider, ChatLog, ChatMessage, StatusIndicator } from '#lib/foundation/carbon';
  import AssistantMetricCard from './AssistantMetricCard.svelte';

  export type DiffChoice = 'kept' | 'discarded';

  interface Props {
    items: readonly LogItem[];
    isRunning: boolean;
    /** The choice of each diff card in this page, by its item ID. */
    diffChoices: ReadonlyMap<number, DiffChoice>;
    onOpenDiff: (item: DiffItem) => void;
    onKeep: (item: DiffItem) => void;
    onDiscard: (item: DiffItem) => void;
  }

  const { items, isRunning, diffChoices, onOpenDiff, onKeep, onDiscard }: Props = $props();

  const entries = $derived(
    arrangeChatLog(
      items.map((item) => ({
        author: item.kind === 'message' ? item.role : 'tool',
        sentAtUtc: item.sentAtUtc,
        item,
      })),
    ),
  );
  const last = $derived(items.at(-1));
  const isTyping = $derived(isRunning && !(last?.kind === 'message' && last.streaming));
</script>

<ChatLog label="Conversation messages">
  {#each entries as entry (entry.kind === 'divider' ? `divider-${entry.dateUtc}` : entry.message.item.id)}
    {#if entry.kind === 'divider'}
      <ChatDivider label={entry.dateUtc} />
    {:else}
      {@const item = entry.message.item}
      {#if item.kind === 'message'}
        <ChatMessage
          from={item.role === 'user' ? 'me' : 'them'}
          author={item.role === 'user' ? 'You' : 'AI assistant'}
          continued={entry.continued}
          streaming={item.streaming}
        >{item.text}{#if item.model !== null}<span class="message-model"
              >{item.model} · {item.credentialName}</span
            >{/if}</ChatMessage
        >
      {:else if item.kind === 'tool_step'}
        {@const step = describeToolStep(item)}
        <li class="log-item"><StatusIndicator label={step.label} kind={step.kind} /></li>
      {:else if item.kind === 'diff'}
        {@const choice = diffChoices.get(item.id)}
        <li class="log-item">
          <!-- The whole card opens the diff; the button in it is the keyboard way. -->
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
          <div
            class="cds--tile assistant-card diff-card"
            onclick={() => {
              onOpenDiff(item);
            }}
          >
            <button type="button" class="cds--link diff-card__name" aria-label={`Open the diff of v${String(item.versionNumber)}`}>
              v{item.versionNumber - 1} → v{item.versionNumber}
            </button>
            {#if choice === 'discarded'}
              <StatusIndicator label="Discarded" kind="neutral" />
            {:else if choice === 'kept'}
              <StatusIndicator label="Kept" kind="success" />
            {:else}
              <div class="diff-card__buttons">
                <Button
                  kind="primary"
                  size="sm"
                  onclick={(event: MouseEvent) => {
                    event.stopPropagation();
                    onKeep(item);
                  }}>Keep</Button
                >
                <Button
                  kind="secondary"
                  size="sm"
                  onclick={(event: MouseEvent) => {
                    event.stopPropagation();
                    onDiscard(item);
                  }}>Discard</Button
                >
              </div>
            {/if}
          </div>
        </li>
      {:else}
        <li class="log-item"><AssistantMetricCard backtestId={item.backtestId} /></li>
      {/if}
    {/if}
  {/each}
  {#if isTyping}
    <ChatMessage from="them" author="AI assistant" typing typingText="The AI assistant writes" />
  {/if}
</ChatLog>

<style>
  .log-item {
    display: flex;
    margin-block-start: var(--cds-spacing-03);
    min-inline-size: 0;
  }

  .message-model {
    display: block;
    margin-block-start: var(--cds-spacing-02);
    color: var(--cds-text-secondary);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
  }

  .assistant-card {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    min-inline-size: 0;
    padding: var(--cds-spacing-04);
  }

  .diff-card {
    cursor: pointer;
  }

  .diff-card:hover {
    background: var(--cds-layer-hover-01);
  }

  .diff-card__name {
    align-self: flex-start;
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }

  .diff-card__buttons {
    display: flex;
    gap: var(--cds-spacing-03);
  }
</style>
