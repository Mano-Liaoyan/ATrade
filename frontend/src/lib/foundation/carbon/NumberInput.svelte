<!-- Carbon number input with its label and the decrement and increment buttons. `value` is the text of the field, so a
     wrong text stays and the caller can name the problem. An invalid input shows the warning icon and the message below
     the field. The step buttons are not in the tab order (Carbon): the arrow keys of the field do the same. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import Icon from './Icon.svelte';

  interface Props {
    label: string;
    value: string;
    onValueChange: (value: string) => void;
    min?: number;
    max?: number;
    step?: number;
    /** The message that tells the user how to correct the value. The input is invalid when it is set. */
    invalidText?: string | null;
    size?: 'sm' | 'md';
  }

  const uid = $props.id();
  const { label, value, onValueChange, min, max, step = 1, invalidText = null, size = 'md' }: Props = $props();

  let input: HTMLInputElement | undefined = $state();
  const invalid = $derived(invalidText !== null);
  const inputId = $derived(`number-input-${uid}`);
  const errorId = $derived(`${inputId}-error`);

  function stepValue(direction: 'up' | 'down'): void {
    if (input === undefined) {
      return;
    }
    // stepUp and stepDown keep the value in min and max. An empty field starts at min.
    if (direction === 'up') {
      input.stepUp();
    } else {
      input.stepDown();
    }
    onValueChange(input.value);
  }
</script>

<div class="cds--form-item">
  <!-- Carbon v11 reads the field height from the layout size class (cds--layout--size-<size>). -->
  <div class={['cds--number', `cds--layout--size-${size}`]} data-invalid={invalid ? '' : undefined}>
    <label for={inputId} class="cds--label">{label}</label>
    <div class="cds--number__input-wrapper">
      <input
        bind:this={input}
        id={inputId}
        type="number"
        {value}
        {min}
        {max}
        {step}
        data-invalid={invalid ? '' : undefined}
        aria-invalid={invalid ? 'true' : undefined}
        aria-describedby={invalid ? errorId : undefined}
        oninput={(event: Event) => {
          onValueChange((event.currentTarget as HTMLInputElement).value);
        }}
      />
      {#if invalid}
        <Icon icon={WarningFilled16} class="cds--number__invalid" />
      {/if}
      <div class="cds--number__controls">
        <button
          type="button"
          class="cds--number__control-btn down-icon"
          aria-label={`Decrease ${label}`}
          tabindex="-1"
          onclick={() => {
            stepValue('down');
          }}
        >
          <Icon icon={Subtract16} />
        </button>
        <div class="cds--number__rule-divider"></div>
        <button
          type="button"
          class="cds--number__control-btn up-icon"
          aria-label={`Increase ${label}`}
          tabindex="-1"
          onclick={() => {
            stepValue('up');
          }}
        >
          <Icon icon={Add16} />
        </button>
        <div class="cds--number__rule-divider"></div>
      </div>
    </div>
    {#if invalid}
      <div id={errorId} class="cds--form-requirement">{invalidText}</div>
    {/if}
  </div>
</div>
