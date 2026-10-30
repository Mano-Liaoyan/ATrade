<!-- A number field of the rule builder: the Carbon small text input, right-aligned with tabular numbers. It reports
     only a finite number (a whole number when `isInteger`), so the rules never hold an empty or partial value. -->
<script lang="ts">
  interface Props {
    label: string;
    value: number;
    onValueChange: (value: number) => void;
    isInteger?: boolean;
    minimum?: number;
    maximum?: number;
    disabled?: boolean;
  }

  const { label, value, onValueChange, isInteger = true, minimum, maximum, disabled = false }: Props = $props();

  function readValue(text: string): void {
    const number = Number(text);
    if (text.trim() === '' || !Number.isFinite(number) || (isInteger && !Number.isInteger(number))) {
      return;
    }
    onValueChange(number);
  }
</script>

<input
  type="number"
  class="cds--text-input cds--text-input--sm rule-number"
  aria-label={label}
  step={isInteger ? 1 : 'any'}
  min={minimum}
  max={maximum}
  {value}
  {disabled}
  oninput={(event) => {
    readValue(event.currentTarget.value);
  }}
/>

<style>
  .rule-number {
    inline-size: var(--cds-spacing-10);
    padding-inline: var(--cds-spacing-03);
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
</style>
