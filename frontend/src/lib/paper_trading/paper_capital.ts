// Reads the paper capital: the paper account balance, or the local value of the settings when IBKR is not connected.
import type { components } from '#lib/api';

type PaperCapitalResponse = components['schemas']['PaperCapitalResponse'];

const PAPER_CAPITAL_PATH = '/api/paper-trading/paper-capital';

export async function readPaperCapital(fetchFunction: typeof fetch): Promise<string | null> {
  try {
    const response = await fetchFunction(PAPER_CAPITAL_PATH);
    if (!response.ok) {
      return null;
    }
    const paperCapital = (await response.json()) as PaperCapitalResponse;
    return paperCapital.paper_capital_usd;
  } catch {
    return null;
  }
}
