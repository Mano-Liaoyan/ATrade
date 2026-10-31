<!-- Carbon text input with its label. Type "password" hides the value (a new API key). An invalid input shows the
     warning icon and the message below the field, in place of the note text. -->
<script lang="ts">
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import type { HTMLInputAttributes } from 'svelte/elements';
  import Icon from './Icon.svelte';
  import { textInputClasses } from './carbon_state';

  interface Props extends Omit<HTMLInputAttributes, 'class' | 'value' | 'type'> {
    label: string;
    // A text input, or a native date and time input with the Carbon text input look.
    type?: 'text' | 'password' | 'date' | 'datetime-local';
    value?: string;
    // The message that tells the user how to correct the value. The input is invalid when it is set.
    invalidText?: string | null;
    // The Carbon helper text below the field. The invalid message replaces it.
    noteText?: string | null;
    // Extra classes of the input element.
    class?: string;
  }

  const uid = $props.id();
  let { label, type = 'text', value = $bindable(''), invalidText = null, noteText = null, id, class: className, ...restProps }: Props = $props();

  const invalid = $derived(invalidText !== null);
  const inputId = $derived(id ?? `text-input-${uid}`);
  const errorId = $derived(`${inputId}-error`);
  const noteId = $derived(`${inputId}-note`);
</script>

<div class="cds--form-item cds--text-input-wrapper">
  <div class="cds--text-input__label-wrapper">
    <label for={inputId} class="cds--label">{label}</label>
  </div>
  <div class="cds--text-input__field-outer-wrapper">
    <div class="cds--text-input__field-wrapper" data-invalid={invalid ? '' : undefined}>
      <input
        {...restProps}
        id={inputId}
        {type}
        class={[...textInputClasses(invalid), className]}
        aria-invalid={invalid ? 'true' : undefined}
        aria-describedby={invalid ? errorId : noteText === null ? undefined : noteId}
        bind:value
      />
      {#if invalid}
        <Icon icon={WarningFilled16} class="cds--text-input__invalid-icon" />
      {/if}
    </div>
    {#if invalid}
      <div id={errorId} class="cds--form-requirement">{invalidText}</div>
    {:else if noteText !== null}
      <div id={noteId} class="cds--form__helper-text">{noteText}</div>
    {/if}
  </div>
</div>
