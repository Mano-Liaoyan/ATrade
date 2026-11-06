"""A value that PostgreSQL or the file system cannot take gets a 422 from the shared layer, not a 500. The requests
come from generated requests on the OpenAPI document."""

import logging

import httpx
import pytest

ABOVE_64_BITS = 2**64
NUL_TEXT = "a\x00b"
BARS_QUERY = {
    "symbol": NUL_TEXT,
    "exchange": "NASDAQ",
    "currency": "USD",
    "bar_period": "1-DAY",
    "start_utc": "2025-01-01T00:00:00Z",
    "end_utc": "2025-02-01T00:00:00Z",
}


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/market-data/bars", BARS_QUERY),
        ("/api/assistant/conversations", {"strategy_id": ABOVE_64_BITS}),
    ],
)
@pytest.mark.anyio
async def test_a_query_value_is_refused(web_client: httpx.AsyncClient, path: str, params: dict[str, str | int]) -> None:
    response = await web_client.get(path, params=params)

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY, response.text
    assert "cannot store" in response.json()["detail"][0]["msg"]


@pytest.mark.anyio
async def test_a_body_value_is_refused(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategies", json={"name": NUL_TEXT})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY, response.text


@pytest.mark.anyio
async def test_a_refused_value_logs_its_traceback(
    web_client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="atrade.foundation.error_response")

    await web_client.post("/api/strategies", json={"name": NUL_TEXT})

    records = [record for record in caplog.records if "PostgreSQL refused" in record.getMessage()]
    assert records
    assert records[0].exc_info is not None


@pytest.mark.parametrize("path", ["/a%00b", "/_app/a%00b"])
@pytest.mark.anyio
async def test_a_page_path_is_refused(web_client: httpx.AsyncClient, path: str) -> None:
    response = await web_client.get(path)

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY, response.text
