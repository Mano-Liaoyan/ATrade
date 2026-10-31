<!-- The conversation log of the assistant side column (docs/architecture/assistant.md 25.12.1): the messages (an AI
     assistant message renders its markdown, 25.12.6), the
     tool steps (one line each: a status icon before the title, for example "Backtest #42", with the status in its
     tooltip; 2 or more consecutive steps are one group "<n> tool steps" with one status icon, open while a step runs,
     and a click opens or closes it), the diff cards, the metric cards, and the condition cards, in a ChatLog. Each AI assistant
     message shows its model and its credential name. A click on a diff card opens CodeDiff in the editor panel of the
     strategy page. Keep opens the new version in the editor, and Discard adds the discarded mark (25.5.2). After the choice, a status
     icon "Kept" or "Discarded" stands before the card title. -->
<script lang="ts">
  import ChevronDown16 from '@carbon/icons/es/chevron--down/16.js';
  import ChevronRight16 from '@carbon/icons/es/chevron--right/16.js';
  import { SvelteMap } from 'svelte/reactivity';
  import { describeToolStep, describeToolStepGroup, groupToolSteps, type DiffItem, type LogItem } from '#lib/assistant';
  import { arrangeChatLog, Button, ChatDivider, ChatLog, ChatMessage, Icon, StatusIndicator } from '#lib/foundation/carbon';
  import { Markdown } from '#lib/foundation/markdown';
  import AssistantMetricCard from './AssistantMetricCard.svelte';
  import AssistantScreenCard from './AssistantScreenCard.svelte';
  import type { DiffChoice } from './assistant_session.svelte';

  interface Props {
    items: readonly LogItem[];
    isRunning: boolean;
    /** The choice of each diff card of the open conversation, by its item ID. */
    diffChoices: ReadonlyMap<number, DiffChoice>;
    onOpenDiff: (item: DiffItem) => void;
    onKeep: (item: DiffItem) => void;
    onDiscard: (item: DiffItem) => void;
    /** The choice of each screen of the condition cards, by its screen ID. */
    screenChoices: ReadonlyMap<number, DiffChoice>;
    onKeepScreen: (screenId: number) => void;
    onDiscardScreen: (screenId: number) => void;
  }

  const { items, isRunning, diffChoices, onOpenDiff, onKeep, onDiscard, screenChoices, onKeepScreen, onDiscardScreen }: Props =
    $props();

  const entries = $derived(
    groupToolSteps(
      arrangeChatLog(
        items.map((item) => ({
          author: item.kind === 'message' ? item.role : 'tool',
          sentAtUtc: item.sentAtUtc,
          item,
        })),
      ),
    ),
  );
  // The open or closed choice of the user for each tool step group, by the group ID. Without a choice, a group is open
  // while a step runs.
  const groupChoices = new SvelteMap<number, boolean>();

  function entryKey(entry: (typeof entries)[number]): string {
    if (entry.kind === 'divider') {
      return `divider-${entry.dateUtc}`;
    }
    return entry.kind === 'tool_steps' ? `steps-${String(entry.id)}` : `item-${String(entry.message.item.id)}`;
  }
  const last = $derived(items.at(-1));
  const isTyping = $derived(isRunning && !(last?.kind === 'message' && last.streaming));
</script>

<ChatLog label="Conversation messages">
  {#each entries as entry (entryKey(entry))}
    {#if entry.kind === 'divider'}
      <ChatDivider label={entry.dateUtc} />
    {:else if entry.kind === 'tool_steps'}
      {@const group = describeToolStepGroup(entry.steps)}
      {@const isOpen = groupChoices.get(entry.id) ?? group.isRunning}
      <li class="log-item step-group">
        <div class="step-line">
          <StatusIndicator label={group.status} kind={group.kind} />
          <button
            type="button"
            class="step-group__toggle"
            aria-expanded={isOpen}
            onclick={() => {
              groupChoices.set(entry.id, !isOpen);
            }}
          >
            <Icon icon={isOpen ? ChevronDown16 : ChevronRight16} />
            {group.title}
          </button>
        </div>
        {#if isOpen}
          <ol class="step-group__steps">
            {#each entry.steps as item (item.id)}
              {@const step = describeToolStep(item)}
              <li class="step-line"><StatusIndicator label={step.status} kind={step.kind} />{step.title}</li>
            {/each}
          </ol>
        {/if}
      </li>
    {:else}
      {@const item = entry.message.item}
      {#if item.kind === 'message'}
        <ChatMessage
          from={item.role === 'user' ? 'me' : 'them'}
          author={item.role === 'user' ? 'You' : 'AI assistant'}
          continued={entry.continued}
          streaming={item.streaming}
        >{#if item.role === 'user'}{item.text}{:else}<Markdown text={item.text} />{/if}{#if item.modelLine !== null}<span
              class="message-model">{item.modelLine}</span
            >{/if}</ChatMessage
        >
      {:else if item.kind === 'tool_step'}
        {@const step = describeToolStep(item)}
        <li class="log-item step-line"><StatusIndicator label={step.status} kind={step.kind} />{step.title}</li>
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
            <div class="diff-card__title">
              {#if choice === 'discarded'}
                <StatusIndicator label="Discarded" kind="neutral" />
              {:else if choice === 'kept'}
                <StatusIndicator label="Kept" kind="success" />
              {/if}
              <button type="button" class="cds--link diff-card__name" aria-label={`Open the diff of v${String(item.versionNumber)}`}>
                v{item.versionNumber - 1} → v{item.versionNumber}
              </button>
            </div>
            {#if choice === undefined}
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
      {:else if item.kind === 'screen'}
        <li class="log-item">
          <AssistantScreenCard
            {item}
            choice={screenChoices.get(item.screenId)}
            onKeep={onKeepScreen}
            onDiscard={onDiscardScreen}
          />
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
  .step-group {
    flex-direction: column;
  }

  .step-line {
    display: flex;
    align-items: center;
  }

  .step-group__toggle {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    gap: var(--cds-spacing-03);
    padding: 0;
    border: 0;
    background: none;
    color: var(--cds-icon-secondary);
    font: inherit;
    cursor: pointer;
  }

  .step-group__toggle:focus-visible {
    outline: 2px solid var(--cds-focus);
  }

  .step-group__steps {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
    margin: var(--cds-spacing-02) 0 0;
    padding: 0 0 0 var(--cds-spacing-07);
    list-style: none;
  }

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

  .diff-card__title {
    display: flex;
    align-items: center;
  }

  .diff-card__name {
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
