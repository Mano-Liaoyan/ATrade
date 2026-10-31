<!-- The status of an item: the status icon alone, before the item title (UI rule: a status icon stands alone, without a
     word). `label` is the accessible name and the tooltip text, for example "Finished". A text that the user must read
     to act, for example an error or the reason that a control is disabled, is a StatusMessage or an
     InlineNotification, not a StatusIndicator. -->
<script lang="ts">
  import StatusIcon from './StatusIcon.svelte';
  import type { StatusKind } from './status_icon';

  interface Props {
    kind: StatusKind;
    label: string;
    align?: 'top' | 'top-start' | 'top-end' | 'bottom' | 'bottom-start' | 'bottom-end' | 'left' | 'right';
  }

  const { kind, label, align = 'bottom' }: Props = $props();
</script>

<StatusIcon {kind} {label} {align} inline />
