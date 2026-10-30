// Public entry of foundation/carbon: the Carbon v11 styles, the IBM Plex fonts, and the general components that
// put the Carbon HTML structure on Bits UI behavior (docs/architecture.md section 13).
// Only src/lib/foundation/ imports bits-ui. Capabilities and routes use the components of this module.

// The fonts come from the font packages in the ATrade build, not from the IBM font server.
import '@ibm/plex-sans/css/ibm-plex-sans-default.min.css';
import '@ibm/plex-mono/css/ibm-plex-mono-default.min.css';
import './carbon.scss';

export { default as Tabs, type TabItem } from './Tabs.svelte';
export { default as Tag, type TagKind } from './Tag.svelte';
export { default as Tooltip, type TooltipAlignment } from './Tooltip.svelte';
export { default as TooltipProvider } from './TooltipProvider.svelte';
export { default as Button } from './Button.svelte';
export { default as TextInput } from './TextInput.svelte';
export { default as Select, type SelectItem } from './Select.svelte';
export { default as ContentSwitcher, type ContentSwitcherItem } from './ContentSwitcher.svelte';
export { default as Dialog } from './Dialog.svelte';
export type { ButtonKind, ButtonSize } from './carbon_state';
export { default as Icon } from './Icon.svelte';
export { default as IconButton, type IconTone } from './IconButton.svelte';
export type { CarbonIcon, CarbonIconNode } from './carbon_icon';
export { default as Combobox } from './Combobox.svelte';
export type { ComboboxItem } from './combobox_classes';
export { default as DataTable, type TableColumn } from './DataTable.svelte';
export { default as OverflowMenu, type OverflowMenuItem } from './OverflowMenu.svelte';
export { default as InlineNotification } from './InlineNotification.svelte';
export type { NotificationKind, NotificationMessage } from './notification_message';
export { default as Checkbox } from './Checkbox.svelte';
export { default as StatusIndicator, type StatusKind } from './StatusIndicator.svelte';
export { default as ChatLog } from './ChatLog.svelte';
export { default as ChatMessage } from './ChatMessage.svelte';
export { default as ChatDivider } from './ChatDivider.svelte';
export { arrangeChatLog, type ChatLogEntry, type ChatLogMessage } from './chat_log';
