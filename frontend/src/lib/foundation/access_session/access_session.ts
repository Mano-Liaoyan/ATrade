// Reads GET /api/access-session. The backend gives the logout URL only when the page came through Cloudflare Access.

import type { components } from '#lib/api';

type AccessSessionResponse = components['schemas']['AccessSessionResponse'];

const ACCESS_SESSION_PATH = '/api/access-session';

/** Returns null when the page did not come through Cloudflare Access or the backend did not answer. */
export async function fetchAccessLogoutUrl(fetchFunction: typeof fetch): Promise<string | null> {
  let response: Response;
  try {
    response = await fetchFunction(ACCESS_SESSION_PATH);
  } catch {
    return null;
  }
  if (!response.ok) {
    return null;
  }
  const session = (await response.json()) as AccessSessionResponse;
  return session.logout_url;
}
