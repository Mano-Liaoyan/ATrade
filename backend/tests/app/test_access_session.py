"""Access session route of the Web app: the logout URL only behind Cloudflare Access."""

import httpx
import pytest


@pytest.mark.anyio
async def test_gives_the_logout_url_when_cloudflare_access_sent_the_request(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/access-session", headers={"Cf-Access-Jwt-Assertion": "header.payload.sig"})

    assert response.status_code == 200
    assert response.json() == {"logout_url": "/cdn-cgi/access/logout"}


@pytest.mark.anyio
async def test_gives_no_logout_url_without_cloudflare_access(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/access-session")

    assert response.status_code == 200
    assert response.json() == {"logout_url": None}
