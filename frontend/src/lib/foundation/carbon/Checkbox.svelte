<!-- Carbon checkbox: a native checkbox with its label. hideLabel keeps the label for screen readers only, for
     example in the selection column of a data table. The native checkbox is transparent and on top of the label, so a
     pointer click goes to the checkbox itself. -->
<script lang="ts">
  interface Props {
    label: string;
    checked: boolean;
    onCheckedChange: (checked: boolean) => void;
    hideLabel?: boolean;
    disabled?: boolean;
  }

  const uid = $props.id();
  const { label, checked, onCheckedChange, hideLabel = false, disabled = false }: Props = $props();
  const inputId = `checkbox-${uid}`;
</script>

<div class="cds--checkbox-wrapper cds--checkbox--inline">
  <input
    id={inputId}
    type="checkbox"
    class="cds--checkbox"
    {checked}
    {disabled}
    onchange={(event) => {
      onCheckedChange(event.currentTarget.checked);
    }}
  />
  <label for={inputId} class="cds--checkbox-label">
    <span class={['cds--checkbox-label-text', hideLabel && 'cds--visually-hidden']}>{label}</span>
  </label>
</div>

<style>
  /* Carbon makes the native checkbox 1 pixel and draws the box on the label. Here the transparent native checkbox
     covers the label (cds--checkbox--inline is position: relative), so the pointer reaches the checkbox. The label still draws the box, the check, and the focus. */
  .cds--checkbox {
    z-index: 1;
    margin: 0;
    clip: auto;
    cursor: pointer;
    opacity: 0;
    inset: 0;
    inline-size: 100%;
    block-size: 100%;
  }

  .cds--checkbox:disabled {
    cursor: not-allowed;
  }
</style>
