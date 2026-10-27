// The commands of the global command palette (foundation/command_palette). A command only opens a page or a form, or
// changes the theme. No command sends a paper order or starts a backtest or a forward test.
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { selectThemeChoice, type ThemeChoice } from '#lib/foundation/color_scheme';
import type { PaletteCommand, PaletteCommandGroup } from '#lib/foundation/command_palette';
import { formatWatchlistInstrument, type WatchlistInstrument } from '#lib/watchlist';
import { createInstrumentHref } from './instrument_href';

/** The id of the start form on the backtests page. The palette goes to it and puts the focus in it. */
export const START_BACKTEST_FORM_ID = 'start-backtest';
/** The id of the start form on the forward tests page. */
export const START_FORWARD_TEST_FORM_ID = 'start-forward-test';

const FORM_FIELDS = 'input, select, textarea, button';

// Each href of this file comes from resolve().
function goToResolvedHref(href: string): Promise<void> {
  // eslint-disable-next-line svelte/no-navigation-without-resolve -- The callers resolve the href.
  return goto(href);
}

function goToPage(label: string, href: string): PaletteCommand {
  return {
    label: `Go to ${label}`,
    run: () => {
      void goToResolvedHref(href);
    },
  };
}

function openForm(label: string, pageHref: string, formId: string): PaletteCommand {
  return {
    label,
    run: () => {
      void goToResolvedHref(`${pageHref}#${formId}`).then(() => {
        document.getElementById(formId)?.querySelector<HTMLElement>(FORM_FIELDS)?.focus();
      });
    },
  };
}

function useTheme(choice: ThemeChoice): PaletteCommand {
  return {
    label: `Use the ${choice} theme`,
    keywords: ['theme'],
    run: () => {
      selectThemeChoice(choice);
    },
  };
}

function openInstrumentPage(instrument: WatchlistInstrument): PaletteCommand {
  return goToHref(formatWatchlistInstrument(instrument), createInstrumentHref(instrument));
}

function goToHref(label: string, href: string): PaletteCommand {
  return {
    label,
    keywords: ['watchlist'],
    run: () => {
      void goToResolvedHref(href);
    },
  };
}

/** The command groups of the palette. The watchlist group shows the watchlist instruments that the palette read. */
export function createPaletteCommandGroups(watchlistInstruments: WatchlistInstrument[]): PaletteCommandGroup[] {
  const groups: PaletteCommandGroup[] = [
    {
      heading: 'Pages',
      commands: [
        goToPage('Home', resolve('/')),
        goToPage('Strategies', resolve('/strategies')),
        goToPage('Backtests', resolve('/backtests')),
        goToPage('Forward tests', resolve('/forward-tests')),
      ],
    },
    {
      heading: 'Forms',
      commands: [
        openForm('Open the backtest form', resolve('/backtests'), START_BACKTEST_FORM_ID),
        openForm('Open the forward test form', resolve('/forward-tests'), START_FORWARD_TEST_FORM_ID),
      ],
    },
  ];
  if (watchlistInstruments.length > 0) {
    groups.push({ heading: 'Watchlist', commands: watchlistInstruments.map(openInstrumentPage) });
  }
  groups.push({ heading: 'Theme', commands: [useTheme('system'), useTheme('light'), useTheme('dark')] });
  return groups;
}
