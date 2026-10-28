<!-- The Log out button of the app shell header. It is a link to the Cloudflare Access logout URL, and it shows only
     when the page came through Cloudflare Access. -->
<script lang="ts">
  import Logout20 from '@carbon/icons/es/logout/20.js';
  import { Icon, Tooltip } from '#lib/foundation/carbon';
  import { fetchAccessLogoutUrl } from './access_session';

  const LABEL = 'Log out';

  let logoutUrl: string | null = $state(null);

  $effect(() => {
    void fetchAccessLogoutUrl(fetch).then((url) => {
      logoutUrl = url;
    });
  });
</script>

{#if logoutUrl !== null}
  <Tooltip text={LABEL} align="bottom-end">
    {#snippet trigger({ props })}
      <a {...props} href={logoutUrl} class="cds--header__action cds--btn--icon-only" aria-label={LABEL}>
        <Icon icon={Logout20} />
      </a>
    {/snippet}
  </Tooltip>
{/if}
