<!-- The settings of one chart indicator (docs/architecture/indicator.md section 23.9.5): a popover at its legend row.
     One number field for each parameter, then one group for each line: the 14 palette colors, "Line style", and
     "Width" (a histogram has the colors only). "Reset to defaults" gives the catalog defaults, solid lines, and
     width 2, and keeps the colors. "Apply" is disabled while a field is invalid; it applies the draft and closes the
     popover. Escape closes it without a change. -->
<script lang="ts">
  import { untrack } from 'svelte';
  import { Button, ContentSwitcher, NumberInput, Popover, type ContentSwitcherItem } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { CHART_PALETTE_SIZE, isHistogramLine, readPaletteColor, readPaletteColorName } from './chart_indicator_styles';
  import type { ChartIndicator, ChartIndicatorDefinition, ChartLineStyle } from './chart_indicators';
  import {
    applySettingsDraft,
    checkSettingsDraft,
    createSettingsDraft,
    formatLineLabel,
    formatParameterLabel,
    hasSettingsProblems,
    resetSettingsDraft,
  } from './indicator_settings';

  interface Props {
    anchor: HTMLElement;
    definition: ChartIndicatorDefinition;
    indicator: ChartIndicator;
    /** The dark palette for the color fields. */
    dark: boolean;
    onApply: (indicator: ChartIndicator) => void;
    onClose: () => void;
  }

  const { anchor, definition, indicator, dark, onApply, onClose }: Props = $props();

  const uid = $props.id();
  let draft = $state(untrack(() => createSettingsDraft(indicator)));
  const problems = $derived(checkSettingsDraft(definition, draft));
  // The step buttons of a float parameter, for example Bollinger Bands k.
  const FLOAT_STEP = 0.1;
  const colors = Array.from({ length: CHART_PALETTE_SIZE }, (_, index) => index + 1);

  const STYLE_ITEMS: ContentSwitcherItem<ChartLineStyle>[] = [
    { value: 'solid', label: 'Solid' },
    { value: 'dashed', label: 'Dashed' },
    { value: 'dotted', label: 'Dotted' },
  ];
  const WIDTH_ITEMS: ContentSwitcherItem<string>[] = ['1', '2', '3', '4'].map((width) => ({
    value: width,
    label: width,
    accessibleLabel: `${width} px`,
  }));

  function apply(): void {
    if (!hasSettingsProblems(problems)) {
      onApply(applySettingsDraft(indicator, definition, draft));
    }
  }
</script>

<Popover
  open
  onOpenChange={(open: boolean) => {
    if (!open) {
      onClose();
    }
  }}
  {anchor}
  label={definition.name}
>
  <form
    class="indicator-settings"
    onsubmit={(event: SubmitEvent) => {
      event.preventDefault();
      apply();
    }}
  >
    <h2 class="settings-heading">{definition.name}</h2>
    <!-- The fields scroll between the heading and the buttons, with a visible track. -->
    <ScrollRegion label={`Settings of ${definition.name}`} maxHeight="min(28rem, 60vh)">
      <div class="settings-fields">
        {#each definition.parameters as parameter (parameter.name)}
          <NumberInput
            label={formatParameterLabel(parameter.name)}
            size="sm"
            value={draft.parameters[parameter.name] ?? ''}
            min={parameter.minimum}
            max={parameter.maximum}
            step={parameter.value_type === 'int' ? 1 : FLOAT_STEP}
            invalidText={problems[parameter.name] ?? null}
            onValueChange={(value: string) => {
              draft.parameters[parameter.name] = value;
            }}
          />
        {/each}
        {#each draft.lines as line, lineIndex (line.output)}
          {@const lineLabel = formatLineLabel(definition, line.output)}
          <fieldset class="line-group">
            <legend class="line-heading">{lineLabel}</legend>
            <div class="color-swatches" role="radiogroup" aria-label="Color">
              {#each colors as color (color)}
                <span class="color-swatch">
                  <input
                    type="radio"
                    name={`line-color-${uid}-${String(lineIndex)}`}
                    value={color}
                    checked={line.color === color}
                    aria-label={readPaletteColorName(color, dark)}
                    onchange={() => {
                      line.color = color;
                    }}
                  />
                  <span class="swatch-fill" style:background-color={readPaletteColor(color, dark)}></span>
                </span>
              {/each}
            </div>
            {#if !isHistogramLine(definition.key, line.output)}
              <div class="line-field">
                <span class="cds--label" aria-hidden="true">Line style</span>
                <ContentSwitcher
                  label="Line style"
                  size="sm"
                  items={STYLE_ITEMS}
                  value={line.style}
                  onValueChange={(style: ChartLineStyle) => {
                    line.style = style;
                  }}
                />
              </div>
              <div class="line-field">
                <span class="cds--label" aria-hidden="true">Width</span>
                <ContentSwitcher
                  label="Width"
                  size="sm"
                  items={WIDTH_ITEMS}
                  value={String(line.width)}
                  onValueChange={(width: string) => {
                    line.width = Number(width);
                  }}
                />
              </div>
            {/if}
          </fieldset>
        {/each}
      </div>
    </ScrollRegion>
    <div class="settings-buttons">
      <Button
        kind="ghost"
        size="sm"
        onclick={() => {
          draft = resetSettingsDraft(definition, draft);
        }}>Reset to defaults</Button
      >
      <Button kind="primary" size="sm" type="submit" disabled={hasSettingsProblems(problems)}>Apply</Button>
    </div>
  </form>
</Popover>

<style>
  .indicator-settings {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-05);
  }

  .settings-fields {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding-inline-end: var(--cds-spacing-03);
  }

  .settings-heading {
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
  }

  .line-group {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    margin: 0;
    padding: 0;
    border: 0;
  }

  .line-heading {
    margin-block-end: var(--cds-spacing-03);
    padding: 0;
    color: var(--cds-text-primary);
    font-size: var(--cds-label-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
  }

  .color-swatches {
    display: grid;
    grid-template-columns: repeat(7, var(--cds-spacing-06));
    gap: var(--cds-spacing-03);
  }

  .color-swatch {
    position: relative;
    display: block;
    inline-size: var(--cds-spacing-06);
    block-size: var(--cds-spacing-06);
  }

  /* The native radio takes the clicks and the keyboard over the swatch. */
  .color-swatch input {
    position: absolute;
    inset: 0;
    z-index: 1;
    margin: 0;
    opacity: 0;
    cursor: pointer;
  }

  .swatch-fill {
    display: block;
    inline-size: 100%;
    block-size: 100%;
  }

  .color-swatch input:checked + .swatch-fill {
    box-shadow:
      inset 0 0 0 2px var(--cds-background),
      0 0 0 2px var(--cds-border-inverse);
  }

  .color-swatch input:focus-visible + .swatch-fill {
    outline: 2px solid var(--cds-focus);
    outline-offset: var(--cds-spacing-02);
  }

  .line-field {
    display: flex;
    flex-direction: column;
  }

  .settings-buttons {
    display: flex;
    justify-content: flex-end;
    gap: var(--cds-spacing-03);
  }
</style>
