<!-- Carbon checkbox: a native checkbox with its label. hideLabel keeps the label for screen readers only, for
     example in the selection column of a data table. -->
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
