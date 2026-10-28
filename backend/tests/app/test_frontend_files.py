"""The Web app serves the built SPA: files, the fallback page, and nothing outside the build directory."""

import httpx
import pytest


@pytest.mark.anyio
async def test_serves_app_shell_at_root(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "app-shell" in response.text


@pytest.mark.anyio
async def test_serves_app_shell_for_a_page_path(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/backtests/42")

    assert response.status_code == 200
    assert "app-shell" in response.text


@pytest.mark.anyio
async def test_serves_built_asset_file(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/_app/start.js")

    assert response.status_code == 200
    assert response.text == "console.log('start');"


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/", "/backtests/42", "/_app/start.js"])
async def test_tells_proxies_not_to_change_frontend_files(web_client: httpx.AsyncClient, path: str) -> None:
    response = await web_client.get(path)

    assert response.headers["cache-control"] == "no-transform"


@pytest.mark.anyio
async def test_unknown_api_path_returns_not_found(
    web_client: httpx.AsyncClient,
) -> None:
    response = await web_client.get("/api/no-such-route")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.anyio
async def test_does_not_serve_files_outside_build_directory(
    web_client: httpx.AsyncClient,
) -> None:
    response = await web_client.get("/%2E%2E/secret.txt")

    assert "outside the build directory" not in response.text
