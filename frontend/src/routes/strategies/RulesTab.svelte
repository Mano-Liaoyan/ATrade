<!-- The "Rules" tab of the strategy editor panel (docs/architecture/strategy.md section 9.8.5). Left: the rule builder
     with the Settings, Entry, and Exit blocks. Right: the read-only code from the rules. After each rule change, the tab
     asks the backend for the code (POST /api/strategy-rules/code), highlights the changed lines, and scrolls the code
     region (not the page) to the first one. Each side scrolls in its own ScrollRegion. Above the blocks is the warning
     of section 9.8.4 when the code of the open version changed after the rules. -->
<script lang="ts">
  import { untrack } from 'svelte';
  import { Checkbox, ContentSwitcher, InlineNotification, Select } from '#lib/foundation/carbon';
  import { CodeEditor } from '#lib/foundation/code_editor';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    findChangedLines,
    generateRulesCode,
    RANK_DIRECTION_CHOICES,
    REBALANCE_CHOICES,
    type RankDirection,
    type RebalancePeriod,
    type RightOperand,
    type RuleExits,
    type RuleGroup,
    type StrategyRules,
    type UniverseSettings,
  } from '#lib/strategy';
  import RuleGroupEditor from './RuleGroupEditor.svelte';
  import RuleNumberInput from './RuleNumberInput.svelte';
  import RuleOperand from './RuleOperand.svelte';

  interface Props {
    rules: StrategyRules;
    onRulesChange: (rules: StrategyRules) => void;
    // "Code of vN changed. Rules are from vM." (section 9.8.4), or null.
    warning?: string | null;
  }

  const { rules, onRulesChange, warning = null }: Props = $props();

  type PositionKind = 'fixed_shares' | 'percent_of_equity';
  const POSITION_ITEMS: { value: PositionKind; label: string }[] = [
    { value: 'fixed_shares', label: 'Shares' },
    { value: 'percent_of_equity', label: '% of equity' },
  ];
  const EMPTY_GROUP: RuleGroup = { type: 'group', match: 'any_of', items: [] };
  const MAXIMUM_PERCENT = 100;
  // The first value of a field whose rules have no value yet.
  const START_VALUES = { stopLossPercent: 5, takeProfitPercent: 10, exitAfterBars: 20, shares: 10, equityPercent: 90 };

  // The value of an exit item that is not selected. The field keeps it, so a new selection gets it again.
  let stopLossPercent = $state(untrack(() => rules.exits.stop_loss_percent) ?? START_VALUES.stopLossPercent);
  let takeProfitPercent = $state(untrack(() => rules.exits.take_profit_percent) ?? START_VALUES.takeProfitPercent);
  let exitAfterBars = $state(untrack(() => rules.exits.exit_after_bars) ?? START_VALUES.exitAfterBars);
  let shares = $state(untrack(() => (rules.settings.position_size.type === 'fixed_shares' ? rules.settings.position_size.shares : START_VALUES.shares)));
  let equityPercent = $state(
    untrack(() => (rules.settings.position_size.type === 'percent_of_equity' ? rules.settings.position_size.percent : START_VALUES.equityPercent)),
  );

  let code = $state('');
  let changedLines: number[] = $state([]);
  let codeRegion: HTMLDivElement | undefined = $state();
  let codeEditor: { scrollLineIntoRegion: (line: number, region: HTMLElement) => void } | undefined = $state();
  let requestNumber = 0;

  // Decided (#173): each rule change asks for the code at once. An answer to an older request is dropped. The
  // highlight compares with the code before the change.
  $effect(() => {
    const requestedRules = rules;
    requestNumber += 1;
    const thisRequest = requestNumber;
    void generateRulesCode(fetch, requestedRules).then((result) => {
      if (thisRequest !== requestNumber || result.kind === 'failed') {
        return;
      }
      const previousCode = untrack(() => code);
      if (result.value === previousCode) {
        return;
      }
      changedLines = findChangedLines(previousCode, result.value);
      code = result.value;
      const firstLine = changedLines[0];
      if (firstLine !== undefined && codeRegion !== undefined) {
        codeEditor?.scrollLineIntoRegion(firstLine, codeRegion);
      }
    });
  });

  function changeExits(change: Partial<RuleExits>): void {
    onRulesChange({ ...rules, exits: { ...rules.exits, ...change } });
  }

  // The universe mode (section 9.8.6): the rules hold `settings.universe`. It replaces the position size.
  const universe = $derived(rules.settings.universe);

  function changeUniverse(change: Partial<UniverseSettings>): void {
    if (universe == null) {
      return;
    }
    onRulesChange({ ...rules, settings: { ...rules.settings, universe: { ...universe, ...change } } });
  }

  function changePositionKind(kind: PositionKind): void {
    const positionSize =
      kind === 'fixed_shares' ? { type: kind, shares } : { type: kind, percent: equityPercent };
    onRulesChange({ ...rules, settings: { ...rules.settings, position_size: positionSize } });
  }
</script>

<div class="rules-tab">
  <div class="rules-tab__builder">
    <ScrollRegion label="Rule builder" fill>
      <div class="rules-tab__blocks">
        {#if warning !== null}
          <InlineNotification kind="warning" lowContrast title={warning} />
        {/if}
        <section class="cds--tile rules-block" aria-labelledby="rules-settings">
          <h3 id="rules-settings" class="rules-block__heading">Settings</h3>
          <div class="rules-block__fields">
            {#if universe != null}
              <div class="rules-field">
                <span class="cds--label">Rebalance</span>
                <span class="rules-switcher">
                  <Select
                    label="Rebalance"
                    hideLabel
                    size="sm"
                    items={REBALANCE_CHOICES}
                    value={universe.rebalance_period}
                    onValueChange={(rebalance_period: RebalancePeriod) => {
                      changeUniverse({ rebalance_period });
                    }}
                  />
                </span>
              </div>
              <div class="rules-field">
                <span class="cds--label">Hold</span>
                <span class="rules-item">
                  <RuleNumberInput
                    label="Hold"
                    value={universe.hold_count}
                    minimum={1}
                    onValueChange={(hold_count: number) => {
                      changeUniverse({ hold_count });
                    }}
                  />
                  <span class="rules-unit">instruments</span>
                </span>
              </div>
              <div class="rules-field">
                <span class="cds--label">Rank by</span>
                <span class="rules-item">
                  <RuleOperand
                    label="Rank by"
                    side="rank"
                    operand={universe.rank_indicator}
                    onOperandChange={(operand: RightOperand) => {
                      if (operand.type === 'indicator') {
                        changeUniverse({ rank_indicator: operand });
                      }
                    }}
                  />
                  <Select
                    label="Rank order"
                    hideLabel
                    size="sm"
                    items={RANK_DIRECTION_CHOICES}
                    value={universe.rank_direction}
                    onValueChange={(rank_direction: RankDirection) => {
                      changeUniverse({ rank_direction });
                    }}
                  />
                </span>
              </div>
            {:else}
            <div class="rules-field">
              <span class="cds--label">Position size</span>
              <span class="rules-switcher">
                <ContentSwitcher
                  label="Position size"
                  size="sm"
                  items={POSITION_ITEMS}
                  value={rules.settings.position_size.type}
                  onValueChange={changePositionKind}
                />
              </span>
            </div>
            {#if rules.settings.position_size.type === 'fixed_shares'}
              <div class="rules-field">
                <span class="cds--label">Shares per trade</span>
                <span class="rules-item">
                  <RuleNumberInput
                    label="Shares per trade"
                    value={rules.settings.position_size.shares}
                    minimum={1}
                    onValueChange={(value: number) => {
                      shares = value;
                      changePositionKind('fixed_shares');
                    }}
                  />
                  <span class="rules-unit">shares</span>
                </span>
              </div>
            {:else}
              <div class="rules-field">
                <span class="cds--label">Equity per trade</span>
                <span class="rules-item">
                  <RuleNumberInput
                    label="Equity per trade"
                    value={rules.settings.position_size.percent}
                    isInteger={false}
                    minimum={0}
                    maximum={MAXIMUM_PERCENT}
                    onValueChange={(value: number) => {
                      equityPercent = value;
                      changePositionKind('percent_of_equity');
                    }}
                  />
                  <span class="rules-unit">%</span>
                </span>
              </div>
            {/if}
            {/if}
          </div>
        </section>

        <section class="cds--tile rules-block" aria-labelledby="rules-entry">
          <h3 id="rules-entry" class="rules-block__heading">{universe != null ? 'Entry filter' : 'Entry'}</h3>
          <RuleGroupEditor
            label={universe != null ? 'Entry filter' : 'Entry'}
            group={rules.entry}
            onGroupChange={(entry) => {
              onRulesChange({ ...rules, entry: entry as RuleGroup });
            }}
          />
        </section>

        <section class="cds--tile rules-block" aria-labelledby="rules-exit">
          <h3 id="rules-exit" class="rules-block__heading">Exit</h3>
          <span class="rules-item">
            <Checkbox
              label="Stop loss"
              checked={rules.exits.stop_loss_percent != null}
              onCheckedChange={(checked: boolean) => {
                changeExits({ stop_loss_percent: checked ? stopLossPercent : null });
              }}
            />
            <RuleNumberInput
              label="Stop loss percent"
              value={stopLossPercent}
              isInteger={false}
              disabled={rules.exits.stop_loss_percent == null}
              onValueChange={(value: number) => {
                stopLossPercent = value;
                changeExits({ stop_loss_percent: value });
              }}
            />
            <span class="rules-unit">% below entry</span>
          </span>
          <span class="rules-item">
            <Checkbox
              label="Take profit"
              checked={rules.exits.take_profit_percent != null}
              onCheckedChange={(checked: boolean) => {
                changeExits({ take_profit_percent: checked ? takeProfitPercent : null });
              }}
            />
            <RuleNumberInput
              label="Take profit percent"
              value={takeProfitPercent}
              isInteger={false}
              disabled={rules.exits.take_profit_percent == null}
              onValueChange={(value: number) => {
                takeProfitPercent = value;
                changeExits({ take_profit_percent: value });
              }}
            />
            <span class="rules-unit">% above entry</span>
          </span>
          <span class="rules-item">
            <Checkbox
              label="Time exit after"
              checked={rules.exits.exit_after_bars != null}
              onCheckedChange={(checked: boolean) => {
                changeExits({ exit_after_bars: checked ? exitAfterBars : null });
              }}
            />
            <RuleNumberInput
              label="Time exit bars"
              value={exitAfterBars}
              minimum={1}
              disabled={rules.exits.exit_after_bars == null}
              onValueChange={(value: number) => {
                exitAfterBars = value;
                changeExits({ exit_after_bars: value });
              }}
            />
            <span class="rules-unit">bars</span>
          </span>
          <Checkbox
            label="Exit when the entry conditions are no longer true"
            checked={rules.exits.exit_when_entry_is_false}
            onCheckedChange={(checked: boolean) => {
              changeExits({ exit_when_entry_is_false: checked });
            }}
          />
          <Checkbox
            label="Exit conditions"
            checked={rules.exits.exit_group != null}
            onCheckedChange={(checked: boolean) => {
              changeExits({ exit_group: checked ? EMPTY_GROUP : null });
            }}
          />
          {#if rules.exits.exit_group != null}
            <RuleGroupEditor
              label="Exit"
              group={rules.exits.exit_group}
              onGroupChange={(exitGroup) => {
                changeExits({ exit_group: exitGroup as RuleGroup });
              }}
            />
          {/if}
        </section>
      </div>
    </ScrollRegion>
  </div>
  <div class="rules-tab__code">
    <ScrollRegion label="Code from the rules" fill bind:viewport={codeRegion}>
      <CodeEditor
        bind:this={codeEditor}
        {code}
        label="Code from the rules"
        readOnly
        highlightedLines={changedLines}
        onCodeChange={() => {}}
      />
    </ScrollRegion>
  </div>
</div>

<style>
  .rules-tab {
    display: flex;
    block-size: 100%;
    min-block-size: 0;
  }

  .rules-tab__builder {
    flex: 1.1 1 0;
    min-inline-size: 0;
    background: var(--cds-background);
  }

  .rules-tab__code {
    flex: 1 1 0;
    min-inline-size: 0;
    border-inline-start: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .rules-tab__blocks {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-05);
  }

  .rules-block {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-04);
    border: 1px solid var(--cds-border-subtle-01);
  }

  .rules-block__heading {
    margin: 0;
    font-size: var(--cds-heading-compact-02-font-size, 1rem);
    font-weight: var(--cds-heading-compact-02-font-weight, 600);
    line-height: var(--cds-heading-compact-02-line-height, 1.375);
  }

  .rules-block__fields {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: var(--cds-spacing-05);
  }

  .rules-field {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
  }

  .rules-switcher {
    inline-size: calc(var(--cds-spacing-13) + var(--cds-spacing-09));
  }

  .rules-item {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .rules-unit {
    color: var(--cds-text-secondary);
  }

  /* The scroll region gives the border and the scroll track: the editor has none of its own. */
  .rules-tab__code :global(.code-editor) {
    border: 0;
  }
</style>
