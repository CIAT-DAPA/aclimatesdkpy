# tests/test_aclimate_client.py
"""Unit tests for the AClimate async API client."""

from __future__ import annotations

import importlib
import os
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest


@pytest.fixture()
def client_module():
    """Imports the client module from the package or local module path."""
    try:
        return importlib.import_module("aclimatesdkpy.aclimate_client")
    except ModuleNotFoundError:
        return importlib.import_module("aclimate_client")


class FakeResponse:
    """Minimal async HTTP response double."""

    def __init__(self, status_code: int, payload: dict[str, Any] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or str(self._payload)

    def json(self) -> dict[str, Any]:
        """Returns the configured JSON payload."""
        return self._payload


class FakeAsyncHTTPClient:
    """Minimal httpx.AsyncClient double with queued responses."""

    def __init__(self, *, get_responses=None, post_responses=None) -> None:
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []
        self.closed = False

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Records GET calls and returns the next queued response."""
        self.get_calls.append({"url": url, **kwargs})
        return self.get_responses.pop(0)

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """Records POST calls and returns the next queued response."""
        self.post_calls.append({"url": url, **kwargs})
        return self.post_responses.pop(0)

    async def aclose(self) -> None:
        """Marks the fake client as closed."""
        self.closed = True


@pytest.fixture()
def reset_global_client_state(client_module):
    """Resets singleton client state before and after each test."""
    client_module._client = None
    client_module._client_started = False
    yield
    client_module._client = None
    client_module._client_started = False

@pytest.mark.asyncio
async def test_get_client_token_uses_constructor_credentials_when_arguments_are_omitted(
    client_module, monkeypatch
):
    """Validates fallback to constructor credentials for client-token authentication."""

    class FakeTokenResponse:
        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> dict[str, Any]:
            return data

    monkeypatch.setattr(client_module, "TokenResponse", FakeTokenResponse)

    fake_http = FakeAsyncHTTPClient(
        post_responses=[FakeResponse(200, {"access_token": "constructor-token"})]
    )

    client = client_module.AClimateClient(
        client_id="constructor-id",
        client_secret="constructor-secret",
        base_url="https://example.test",
    )
    client._http = fake_http

    result = await client.get_client_token()

    assert result == {"access_token": "constructor-token"}
    assert fake_http.post_calls[0]["json"] == {
        "client_id": "constructor-id",
        "client_secret": "constructor-secret",
    }


@pytest.mark.asyncio
async def test_fetch_token_raises_auth_error_when_credentials_are_missing(client_module):
    """Validates that token fetching requires client credentials."""
    client = client_module.AClimateClient()

    with pytest.raises(client_module.AClimateAuthError):
        await client._fetch_token()


def test_set_token_from_response_accepts_access_token_and_sets_expiration(client_module):
    """Validates token extraction and expiration calculation."""
    client = client_module.AClimateClient()
    before = time.monotonic()

    client._set_token_from_response({"access_token": "abc", "expires_in": 120})

    assert client._token == "abc"
    assert client._token_expires_at > before


def test_set_token_from_response_accepts_token_alias(client_module):
    """Validates token extraction from the legacy token key."""
    client = client_module.AClimateClient()

    client._set_token_from_response({"token": "legacy-token"})

    assert client._token == "legacy-token"


def test_set_token_from_response_raises_auth_error_without_token(client_module):
    """Validates auth failure when no token exists in the response."""
    client = client_module.AClimateClient()

    with pytest.raises(client_module.AClimateAuthError):
        client._set_token_from_response({"expires_in": 300})


@pytest.mark.asyncio
async def test_ensure_token_fetches_new_token_when_token_is_missing(client_module):
    """Validates lazy token fetching when no token is available."""
    client = client_module.AClimateClient()
    client._fetch_token = AsyncMock(side_effect=lambda: setattr(client, "_token", "fresh-token"))

    token = await client._ensure_token()

    assert token == "fresh-token"
    client._fetch_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_public_filters_none_values(client_module):
    """Validates that public POST requests omit None values."""
    fake_http = FakeAsyncHTTPClient(
        post_responses=[FakeResponse(200, {"access_token": "public-token"})]
    )
    client = client_module.AClimateClient(base_url="https://example.test")
    client._http = fake_http

    await client._post_public("/auth/get-client-token", {"client_id": "id", "client_secret": None})

    assert fake_http.post_calls[0]["json"] == {"client_id": "id"}


@pytest.mark.asyncio
async def test_post_public_raises_auth_error_for_http_error(client_module):
    """Validates auth error handling for failed public auth requests."""
    fake_http = FakeAsyncHTTPClient(post_responses=[FakeResponse(401, text="Unauthorized")])
    client = client_module.AClimateClient(base_url="https://example.test")
    client._http = fake_http

    with pytest.raises(client_module.AClimateAuthError):
        await client._post_public("/auth/login", {"username": "bad", "password": "bad"})


@pytest.mark.asyncio
async def test_get_sends_bearer_token_and_filters_none_params(client_module):
    """Validates authenticated GET request behavior."""
    fake_http = FakeAsyncHTTPClient(get_responses=[FakeResponse(200, {"ok": True})])
    client = client_module.AClimateClient(base_url="https://example.test", access_token="ready-token")
    client._http = fake_http

    result = await client.get("/countries", name="Colombia", optional=None)

    assert result == {"ok": True}
    assert fake_http.get_calls[0]["url"] == "https://example.test/countries"
    assert fake_http.get_calls[0]["params"] == {"name": "Colombia"}
    assert fake_http.get_calls[0]["headers"] == {"Authorization": "Bearer ready-token"}


@pytest.mark.asyncio
async def test_get_refreshes_token_after_unauthorized_response(client_module):
    """Validates token refresh and retry after a 401 response."""
    fake_http = FakeAsyncHTTPClient(
        get_responses=[
            FakeResponse(401, text="Unauthorized"),
            FakeResponse(200, {"ok": True}),
        ]
    )
    client = client_module.AClimateClient(base_url="https://example.test", access_token="expired-token")
    client._http = fake_http

    async def fake_fetch_token() -> None:
        client._token = "refreshed-token"
        client._token_expires_at = time.monotonic() + 300

    client._fetch_token = AsyncMock(side_effect=fake_fetch_token)

    result = await client.get("/secure")

    assert result == {"ok": True}
    assert len(fake_http.get_calls) == 2
    assert fake_http.get_calls[0]["headers"] == {"Authorization": "Bearer expired-token"}
    assert fake_http.get_calls[1]["headers"] == {"Authorization": "Bearer refreshed-token"}


@pytest.mark.asyncio
async def test_get_raises_api_error_for_failed_response(client_module):
    """Validates API error handling for failed authenticated GET requests."""
    fake_http = FakeAsyncHTTPClient(get_responses=[FakeResponse(500, text="Server error")])
    client = client_module.AClimateClient(base_url="https://example.test", access_token="token")
    client._http = fake_http

    with pytest.raises(client_module.AClimateAPIError):
        await client.get("/broken")


@pytest.mark.asyncio
async def test_post_sends_bearer_token_and_payload(client_module):
    """Validates authenticated POST request behavior."""
    fake_http = FakeAsyncHTTPClient(post_responses=[FakeResponse(200, {"created": True})])
    client = client_module.AClimateClient(base_url="https://example.test", access_token="token")
    client._http = fake_http

    result = await client.post("/geoserver/point-data", {"latitude": 1.2, "longitude": -75.1})

    assert result == {"created": True}
    assert fake_http.post_calls[0]["url"] == "https://example.test/geoserver/point-data"
    assert fake_http.post_calls[0]["json"] == {"latitude": 1.2, "longitude": -75.1}
    assert fake_http.post_calls[0]["headers"] == {"Authorization": "Bearer token"}


@pytest.mark.asyncio
async def test_post_refreshes_token_after_unauthorized_response(client_module):
    """Validates token refresh and retry after a POST 401 response."""
    fake_http = FakeAsyncHTTPClient(
        post_responses=[
            FakeResponse(401, text="Unauthorized"),
            FakeResponse(200, {"ok": True}),
        ]
    )
    client = client_module.AClimateClient(base_url="https://example.test", access_token="expired-token")
    client._http = fake_http

    async def fake_fetch_token() -> None:
        client._token = "new-token"
        client._token_expires_at = time.monotonic() + 300

    client._fetch_token = AsyncMock(side_effect=fake_fetch_token)

    result = await client.post("/secure", {"value": 1})

    assert result == {"ok": True}
    assert fake_http.post_calls[1]["headers"] == {"Authorization": "Bearer new-token"}


@pytest.mark.asyncio
async def test_post_raises_api_error_for_failed_response(client_module):
    """Validates API error handling for failed authenticated POST requests."""
    fake_http = FakeAsyncHTTPClient(post_responses=[FakeResponse(400, text="Bad request")])
    client = client_module.AClimateClient(base_url="https://example.test", access_token="token")
    client._http = fake_http

    with pytest.raises(client_module.AClimateAPIError):
        await client.post("/invalid", {"bad": True})


@pytest.mark.asyncio
async def test_post_geoserver_point_data_delegates_to_authenticated_post(client_module):
    """Validates the geoserver point-data convenience method."""
    client = client_module.AClimateClient()
    client.post = AsyncMock(return_value={"value": 42})

    result = await client.post_geoserver_point_data(
        latitude=4.65,
        longitude=-74.08,
        variable="rainfall",
    )

    assert result == {"value": 42}
    client.post.assert_awaited_once_with(
        "/geoserver/point-data",
        {"latitude": 4.65, "longitude": -74.08, "variable": "rainfall"},
    )


@pytest.mark.asyncio
async def test_get_available_periods_delegates_to_authenticated_get(client_module):
    """Validates the available-periods convenience method."""
    client = client_module.AClimateClient()
    client.get = AsyncMock(return_value=["2024-01", "2024-02"])

    result = await client.get_available_periods(country_id=1, temporality=None)

    assert result == ["2024-01", "2024-02"]
    client.get.assert_awaited_once_with("/periods/available", country_id=1, temporality=None)


@pytest.mark.asyncio
async def test_context_manager_creates_and_closes_http_client(monkeypatch, client_module):
    """Validates async context manager lifecycle behavior."""
    fake_http = FakeAsyncHTTPClient()

    monkeypatch.setattr(client_module.httpx, "AsyncClient", lambda **_: fake_http)

    async with client_module.AClimateClient(timeout=5.0) as client:
        assert client._http is fake_http

    assert fake_http.closed is True
    assert client._http is None


@pytest.mark.asyncio
async def test_get_client_creates_singleton_using_environment_credentials(
    monkeypatch, client_module, reset_global_client_state
):
    """Validates singleton client creation with environment-provided credentials."""
    monkeypatch.setenv("ACLIMATE_CLIENT_ID", "singleton-client-id")
    monkeypatch.setenv("ACLIMATE_CLIENT_SECRET", "singleton-client-secret")

    fake_http = FakeAsyncHTTPClient()
    monkeypatch.setattr(client_module.httpx, "AsyncClient", lambda **_: fake_http)

    client = await client_module.get_client(
        base_url="https://example.test",
        client_id=os.environ["ACLIMATE_CLIENT_ID"],
        client_secret=os.environ["ACLIMATE_CLIENT_SECRET"],
        timeout=10.0,
    )

    same_client = await client_module.get_client()

    assert same_client is client
    assert client._client_id == "singleton-client-id"
    assert client._client_secret == "singleton-client-secret"
    assert client.base_url == "https://example.test"


@pytest.mark.asyncio
async def test_close_client_closes_and_resets_singleton(client_module, reset_global_client_state):
    """Validates singleton client cleanup."""
    fake_http = FakeAsyncHTTPClient()
    client = client_module.AClimateClient()
    client._http = fake_http

    client_module._client = client
    client_module._client_started = True

    await client_module.close_client()

    assert fake_http.closed is True
    assert client_module._client is None
    assert client_module._client_started is False

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "args", "expected_path", "expected_params"),
    [
        ("get_countries", (), "/countries", {}),
        ("get_countries_by_name", ("Colombia",), "/countries/by-name", {"name": "Colombia"}),
        ("get_admin1_by_country_ids", ([1, 2],), "/admin1/by-country-ids", {"country_ids": "1,2"}),
        ("get_locations_by_machine_name", ("colombia-cali",), "/locations/by-machine-name", {"machine_name": "colombia-cali"}),
        ("get_locations_by_id", (10,), "/locations/by-id", {"id": 10}),
        (
            "get_locations_by_country_ids_with_data",
            ([1, 2],),
            "/locations/by-country-ids-with-data",
            {"country_ids": "1,2", "days": 0},
        ),
        ("get_historical_daily_minmax_by_location", (10,), "/historical-daily/minmax-by-location", {"location_id": 10}),
        (
            "get_historical_daily_by_date_range_all_measures",
            ([10, 20], "2024-01-01", "2024-01-31"),
            "/historical-daily/by-date-range-all-measures",
            {"location_ids": "10,20", "start_date": "2024-01-01", "end_date": "2024-01-31"},
        ),
        (
            "get_historical_monthly_by_date_range_all_measures",
            ([10, 20], "2024-01-01", "2024-12-31"),
            "/historical-monthly/by-date-range-all-measures",
            {"location_ids": "10,20", "start_date": "2024-01-01", "end_date": "2024-12-31"},
        ),
        ("get_historical_monthly_minmax_by_location", (10,), "/historical-monthly/minmax-by-location", {"location_id": 10}),
        ("get_climatology_minmax_by_location", (10,), "/climatology/minmax-by-location", {"location_id": 10}),
        (
            "get_climatology_by_month_range_location_ids_all_measures",
            ([10, 20], 1, 12),
            "/climatology/by-month-range-location-ids-all-measures",
            {"location_ids": "10,20", "start_month": 1, "end_month": 12},
        ),
        ("get_indicator_by_location_id", (10,), "/indicator/by-location-id", {"location_id": 10}),
        (
            "get_indicator_by_location_date_period",
            (10, "2024-01-01", "2024-01-31", "daily"),
            "/indicator/by-location-date-period",
            {"location_id": 10, "start_date": "2024-01-01", "end_date": "2024-01-31", "period": "daily"},
        ),
        ("get_indicator_minmax_by_location", (10,), "/indicator/minmax-by-location", {"location_id": 10}),
        ("get_indicators_by_category_id", (5,), "/indicator-mng/by-category-id", {"category_id": 5}),
        (
            "get_indicators_by_country",
            (1,),
            "/indicator-mng/by-country",
            {"country_id": 1, "temporality": None, "category_id": None, "type": "CLIMATE"},
        ),
        (
            "get_indicator_categories_by_category",
            (5,),
            "/indicator-category-mng/by-category",
            {"category_id": 5},
        ),
        (
            "get_indicator_categories_by_country",
            (1,),
            "/indicator-category-mng/by-country",
            {"country_id": 1},
        ),
        (
            "get_indicator_features_by_indicator_and_country",
            (7, 1),
            "/indicator-features/by-indicator-and-country",
            {"indicator_id": 7, "country_id": 1, "type": None},
        ),
    ],
)
async def test_endpoint_wrapper_methods_delegate_to_get_with_expected_parameters(
    monkeypatch,
    client_module,
    method_name,
    args,
    expected_path,
    expected_params,
):
    """Validates endpoint wrapper methods delegate to GET with the expected path and parameters."""

    class FakeTypeAdapter:
        def __init__(self, annotation):
            self.annotation = annotation

        def validate_python(self, value):
            return value

    class FakeModel:
        @classmethod
        def model_validate(cls, value):
            return value

    monkeypatch.setattr(client_module, "TypeAdapter", FakeTypeAdapter)
    monkeypatch.setattr(client_module, "IndicatorCategory", FakeModel)

    client = client_module.AClimateClient()
    client.get = AsyncMock(return_value=[])

    method = getattr(client, method_name)

    result = await method(*args)

    assert result == []
    client.get.assert_awaited_once_with(expected_path, **expected_params)


@pytest.mark.asyncio
async def test_get_locations_by_country_ids_with_data_allows_custom_days(monkeypatch, client_module):
    """Validates custom days are forwarded when requesting locations with data."""

    class FakeTypeAdapter:
        def __init__(self, annotation):
            self.annotation = annotation

        def validate_python(self, value):
            return value

    monkeypatch.setattr(client_module, "TypeAdapter", FakeTypeAdapter)

    client = client_module.AClimateClient()
    client.get = AsyncMock(return_value=[])

    result = await client.get_locations_by_country_ids_with_data(country_ids=1, days=15)

    assert result == []
    client.get.assert_awaited_once_with(
        "/locations/by-country-ids-with-data",
        country_ids="1",
        days=15,
    )


@pytest.mark.asyncio
async def test_get_indicators_by_country_forwards_optional_filters(monkeypatch, client_module):
    """Validates optional indicator filters are forwarded correctly."""

    class FakeTypeAdapter:
        def __init__(self, annotation):
            self.annotation = annotation

        def validate_python(self, value):
            return value

    monkeypatch.setattr(client_module, "TypeAdapter", FakeTypeAdapter)

    client = client_module.AClimateClient()
    client.get = AsyncMock(return_value=[])

    result = await client.get_indicators_by_country(
        country_id=1,
        temporality="DAILY",
        category_id=3,
        type="AGROCLIMATIC",
    )

    assert result == []
    client.get.assert_awaited_once_with(
        "/indicator-mng/by-country",
        country_id=1,
        temporality="DAILY",
        category_id=3,
        type="AGROCLIMATIC",
    )