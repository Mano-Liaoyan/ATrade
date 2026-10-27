<!-- The theme button of the app shell header. A click changes the theme: System, Light, Dark, then System again.
     The icon, the accessible name, and the tooltip show the current choice. -->
<script lang="ts">
  import Asleep20 from '@carbon/icons/es/asleep/20.js';
  import Light20 from '@carbon/icons/es/light/20.js';
  import Screen20 from '@carbon/icons/es/screen/20.js';
  import { mergeProps } from 'bits-ui';
  import { Icon, Tooltip, type CarbonIcon } from '#lib/foundation/carbon';
  import {
    nextThemeChoice,
    readAppliedThemeChoice,
    readThemeChoice,
    selectThemeChoice,
    type ThemeChoice,
    watchColorScheme,
  } from './theme_choice';

  const CHOICE_ICONS: Record<ThemeChoice, CarbonIcon> = { system: Screen20, light: Light20, dark: Asleep20 };
  const CHOICE_NAMES: Record<ThemeChoice, string> = { system: 'System', light: 'Light', dark: 'Dark' };

  // src/app.html puts the saved choice on <html> before the first paint. The button reads the same saved choice.
  let choice: ThemeChoice = $state(readThemeChoice());
  const label = $derived(`Theme: ${CHOICE_NAMES[choice]}`);

  function changeTheme(): void {
    choice = nextThemeChoice(choice);
    selectThemeChoice(choice);
  }

  // The command palette can also change the theme. The button then shows the choice on <html>.
  $effect(() =>
    watchColorScheme(() => {
      choice = readAppliedThemeChoice();
    }),
  );
</script>

<Tooltip text={label} align="bottom-end">
  {#snippet trigger({ props })}
    <button
      {...mergeProps(props, { onclick: changeTheme })}
      type="button"
      class="cds--header__action cds--btn--icon-only"
      aria-label={label}
    >
      <Icon icon={CHOICE_ICONS[choice]} />
    </button>
  {/snippet}
</Tooltip>
