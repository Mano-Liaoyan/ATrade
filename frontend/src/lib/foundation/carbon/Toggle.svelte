<!-- Carbon small toggle: a switch button with its label at the side (the Carbon `hideLabel` form, where the side text
     is the label). The button has the role switch and aria-checked, and Space or Enter changes it. -->
<script lang="ts">
  interface Props {
    label: string;
    checked: boolean;
    onCheckedChange: (checked: boolean) => void;
  }

  const uid = $props.id();
  const { label, checked, onCheckedChange }: Props = $props();
  const buttonId = `toggle-${uid}`;
  const labelId = `toggle-label-${uid}`;
</script>

<div class="cds--toggle">
  <button
    id={buttonId}
    type="button"
    class="cds--toggle__button"
    role="switch"
    aria-checked={checked}
    aria-labelledby={labelId}
    onclick={() => {
      onCheckedChange(!checked);
    }}
  ></button>
  <label for={buttonId} class="cds--toggle__label">
    <span class="cds--toggle__label-text cds--visually-hidden">{label}</span>
    <div class="cds--toggle__appearance cds--toggle__appearance--sm">
      <div class={['cds--toggle__switch', checked && 'cds--toggle__switch--checked']}>
        <!-- The check mark of the Carbon small toggle (the same path as the Carbon React Toggle). -->
        <svg class="cds--toggle__check" width="6px" height="5px" viewBox="0 0 6 5" aria-hidden="true" focusable="false">
          <path d="M2.2 2.7L5 0 6 1 2.2 5 0 2.7 1 1.5z" />
        </svg>
      </div>
      <span id={labelId} class="cds--toggle__text">{label}</span>
    </div>
  </label>
</div>
