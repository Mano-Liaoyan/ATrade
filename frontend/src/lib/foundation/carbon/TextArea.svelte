<!-- Carbon text area with its label: a text of more than one line, for example a formula expression with variables.
     An invalid text area shows the warning icon and the message below the field, in place of the note text. -->
<script lang="ts">
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import type { HTMLTextareaAttributes } from 'svelte/elements';
  import Icon from './Icon.svelte';

  interface Props extends Omit<HTMLTextareaAttributes, 'class' | 'value'> {
    label: string;
    value?: string;
    // The message that tells the user how to correct the value. The text area is invalid when it is set.
    invalidText?: string | null;
    // The Carbon helper text below the field. The invalid message replaces it.
    noteText?: string | null;
    // Extra classes of the textarea element.
    class?: string;
  }

  const DEFAULT_ROWS = 4;
  const uid = $props.id();
  let { label, value = $bindable(''), invalidText = null, noteText = null, id, class: className, rows = DEFAULT_ROWS, ...restProps }: Props = $props();

  const invalid = $derived(invalidText !== null);
  const inputId = $derived(id ?? `text-area-${uid}`);
  const errorId = $derived(`${inputId}-error`);
  const noteId = $derived(`${inputId}-note`);
</script>

<div class="cds--form-item">
  <div class="cds--text-area__label-wrapper">
    <label for={inputId} class="cds--label">{label}</label>
  </div>
  <div class="cds--text-area__wrapper" data-invalid={invalid ? '' : undefined}>
    <textarea
      {...restProps}
      id={inputId}
      {rows}
      class={['cds--text-area', invalid ? 'cds--text-area--invalid' : null, className]}
      aria-invalid={invalid ? 'true' : undefined}
      aria-describedby={invalid ? errorId : noteText === null ? undefined : noteId}
      bind:value
    ></textarea>
    {#if invalid}
      <Icon icon={WarningFilled16} class="cds--text-area__invalid-icon" />
    {/if}
  </div>
  {#if invalid}
    <div id={errorId} class="cds--form-requirement">{invalidText}</div>
  {:else if noteText !== null}
    <div id={noteId} class="cds--form__helper-text">{noteText}</div>
  {/if}
</div>

<style>
  /* Carbon gives the width only to the wrapper. Without `cols`, the text area fills it. */
  textarea {
    inline-size: 100%;
  }
</style>
