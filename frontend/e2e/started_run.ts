// A run page opens the newest run of the list, so its address has another run until the page opens the started run.
// So a test reads the ID of a started run from the answer of the start request. Call this before the click that starts it.
import type { Page } from '@playwright/test';

export async function waitForStartedRunId(page: Page, startPath: string): Promise<string> {
  const response = await page.waitForResponse((answer) => answer.request().method() === 'POST' && answer.url().endsWith(startPath));
  return String(((await response.json()) as { id: number }).id);
}
