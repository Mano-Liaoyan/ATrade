// The filled orders of the paper account feed when reads overlap.
import { describe, expect, it } from 'vite-plus/test';
import { paperAccountFeed } from './paper_account_feed.svelte';

function makeResponse(orderId: number): Response {
  return new Response(JSON.stringify({ manual_orders: [{ id: orderId, filled_quantity: '1' }] }), {
    headers: { 'content-type': 'application/json' },
  });
}

describe('paperAccountFeed.refreshFilledOrders', () => {
  it('keeps the newest read when an older read answers last', async () => {
    const answers: ((response: Response) => void)[] = [];
    const fetchFunction: typeof fetch = () => new Promise((resolve) => answers.push(resolve));

    const olderRead = paperAccountFeed.refreshFilledOrders(fetchFunction);
    const newestRead = paperAccountFeed.refreshFilledOrders(fetchFunction);
    answers[1]?.(makeResponse(2));
    await newestRead;
    answers[0]?.(makeResponse(1));
    await olderRead;

    expect(paperAccountFeed.filledOrders.map((order) => order.id)).toEqual([2]);
  });
});
