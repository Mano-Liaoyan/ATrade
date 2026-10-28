// Public entry of foundation/access_session: the Log out button of the app shell header. Cloudflare Access protects
// ATrade on the server (docs/architecture.md section 14). GET /api/access-session gives the logout URL only when the
// page came through Access, so a development machine shows no Log out button.

export { fetchAccessLogoutUrl } from './access_session';
export { default as LogOutButton } from './LogOutButton.svelte';
