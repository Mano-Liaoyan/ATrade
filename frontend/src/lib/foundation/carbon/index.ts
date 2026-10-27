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
