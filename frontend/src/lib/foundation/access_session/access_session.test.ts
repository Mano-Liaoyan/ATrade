// Reads GET /api/access-session: the logout URL only when the page came through Cloudflare Access.
import { describe, expect, it } from 'vite-plus/test';
import { fetchAccessLogoutUrl } from './access_session';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('fetchAccessLogoutUrl', () => {
  it('gives the logout URL behind Cloudflare Access', async () => {
    const logoutUrl = await fetchAccessLogoutUrl(respondWith(200, { logout_url: '/cdn-cgi/access/logout' }));

    expect(logoutUrl).toBe('/cdn-cgi/access/logout');
  });

  it('gives null without Cloudflare Access', async () => {
    const logoutUrl = await fetchAccessLogoutUrl(respondWith(200, { logout_url: null }));

    expect(logoutUrl).toBeNull();
  });

  it('gives null when a proxy answers 502', async () => {
    const logoutUrl = await fetchAccessLogoutUrl(respondWith(502, 'Bad Gateway'));

    expect(logoutUrl).toBeNull();
  });

  it('gives null when the request fails', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    expect(await fetchAccessLogoutUrl(failingFetch)).toBeNull();
  });
});
