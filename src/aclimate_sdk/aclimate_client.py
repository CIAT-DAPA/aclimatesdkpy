from __future__ import annotations

import asyncio
import atexit
import logging
import time
from typing import Any, Iterable
from datetime import date

import httpx
from pydantic import TypeAdapter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from aclimate_sdk.aclimate_api_error import AClimateAPIError
from aclimate_sdk.aclimate_auth_error import AClimateAuthError
from aclimate_sdk.aclimate_models import (
    Admin1,
    ClimateHistoricalClimatology,
    ClimateHistoricalDaily,
    ClimateHistoricalIndicatorRecord,
    ClimateHistoricalMonthly,
    Country,
    Indicator,
    IndicatorCategory,
    IndicatorFeature,
    IndicatorWithFeatures,
    Location,
    LocationWithData,
    MinMaxClimatologyRecord,
    MinMaxDailyRecord,
    MinMaxIndicatorRecord,
    MinMaxMonthlyRecord,
    TokenResponse,
)
from aclimate_sdk.utils import csv, date_str, ensure_list

logger = logging.getLogger(__name__)


class AClimateClient:
    """Async client for the AClimate v3 API.

    Use as an async context manager::

        async with AClimateClient(client_id="...", client_secret="...") as client:
            countries = await client.get_countries()
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        *,
        base_url: str = "https://api.aclimate.org",
        access_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._token = access_token
        self._token_expires_at = 0.0 if access_token is None else time.monotonic() + 86400
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AClimateClient":
        self._http = httpx.AsyncClient(timeout=self._timeout, headers={"Content-Type": "application/json"})
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def login(self, username: str, password: str) -> dict[str, Any]:
        data = await self._post_public("/auth/login", {"username": username, "password": password})
        self._set_token_from_response(data)
        return data

    async def get_client_token(self, client_id: str | None = None, client_secret: str | None = None) -> TokenResponse:
        data = await self._post_public(
            "/auth/get-client-token",
            {"client_id": client_id or self._client_id, "client_secret": client_secret or self._client_secret},
        )
        self._set_token_from_response(data)
        return TokenResponse.model_validate(data)

    async def validate_token(self) -> dict[str, Any]:
        return await self.get("/auth/token/validate")

    async def _fetch_token(self) -> None:
        if not self._client_id or not self._client_secret:
            raise AClimateAuthError("client_id/client_secret are required to fetch a token")
        await self.get_client_token(self._client_id, self._client_secret)

    def _set_token_from_response(self, data: dict[str, Any]) -> None:
        token = data.get("access_token") or data.get("token")
        if not token:
            raise AClimateAuthError(f"No access token found in response: {data}")
        self._token = token
        expires_in = int(data.get("expires_in") or 300)
        self._token_expires_at = time.monotonic() + max(expires_in - 60, 1)

    async def _ensure_token(self) -> str:
        if not self._token or time.monotonic() >= self._token_expires_at:
            await self._fetch_token()
        assert self._token
        return self._token

    async def _post_public(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        assert self._http, "Client not initialized; use 'async with AClimateClient(...)'"
        response = await self._http.post(f"{self.base_url}{path}", json={k: v for k, v in json_body.items() if v is not None})
        if response.status_code >= 400:
            raise AClimateAuthError(f"Auth request failed ({response.status_code}): {response.text[:500]}")
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), retry=retry_if_exception_type(httpx.TransportError), reraise=True)
    async def get(self, path: str, **params: Any) -> Any:
        assert self._http, "Client not initialized; use 'async with AClimateClient(...)'"
        token = await self._ensure_token()
        clean_params = {k: v for k, v in params.items() if v is not None}
        response = await self._http.get(f"{self.base_url}{path}", params=clean_params, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 401:
            self._token = None
            token = await self._ensure_token()
            response = await self._http.get(f"{self.base_url}{path}", params=clean_params, headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise AClimateAPIError(response.status_code, response.text[:500])
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), retry=retry_if_exception_type(httpx.TransportError), reraise=True)
    async def post(self, path: str, json_body: dict[str, Any]) -> Any:
        assert self._http, "Client not initialized; use 'async with AClimateClient(...)'"
        token = await self._ensure_token()
        response = await self._http.post(f"{self.base_url}{path}", json=json_body, headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 401:
            self._token = None
            token = await self._ensure_token()
            response = await self._http.post(f"{self.base_url}{path}", json=json_body, headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise AClimateAPIError(response.status_code, response.text[:500])
        return response.json()

    # Admin levels
    async def get_countries(self) -> list[Country]:
        return TypeAdapter(list[Country]).validate_python(await self.get("/countries"))

    async def get_countries_by_name(self, name: str = "Colombia") -> list[Country]:
        return TypeAdapter(list[Country]).validate_python(await self.get("/countries/by-name", name=name))

    async def get_admin1_by_country_ids(self, country_ids: str | int | Iterable[int]) -> list[Admin1]:
        return TypeAdapter(list[Admin1]).validate_python(await self.get("/admin1/by-country-ids", country_ids=csv(country_ids)))

    # Locations
    async def get_locations_by_machine_name(self, machine_name: str) -> list[Location]:
        return TypeAdapter(list[Location]).validate_python(await self.get("/locations/by-machine-name", machine_name=machine_name))

    async def get_locations_by_id(self, id: int) -> list[Location]:
        return TypeAdapter(list[Location]).validate_python(await self.get("/locations/by-id", id=id))

    async def get_locations_by_country_ids_with_data(self, country_ids: str | int | Iterable[int], days: int = 0) -> list[LocationWithData]:
        return TypeAdapter(list[LocationWithData]).validate_python(await self.get("/locations/by-country-ids-with-data", country_ids=csv(country_ids), days=days))

    # Historical daily/monthly
    async def get_historical_daily_minmax_by_location(self, location_id: int) -> list[MinMaxDailyRecord]:
        return TypeAdapter(list[MinMaxDailyRecord]).validate_python(await self.get("/historical-daily/minmax-by-location", location_id=location_id))

    async def get_historical_daily_by_date_range_all_measures(self, location_ids: str | int | Iterable[int], start_date: str | date | None = None, end_date: str | date | None = None) -> list[ClimateHistoricalDaily]:
        return TypeAdapter(list[ClimateHistoricalDaily]).validate_python(await self.get("/historical-daily/by-date-range-all-measures", location_ids=csv(location_ids), start_date=date_str(start_date), end_date=date_str(end_date)))

    async def get_historical_monthly_by_date_range_all_measures(self, location_ids: str | int | Iterable[int], start_date: str | date | None = None, end_date: str | date | None = None) -> list[ClimateHistoricalMonthly]:
        return TypeAdapter(list[ClimateHistoricalMonthly]).validate_python(await self.get("/historical-monthly/by-date-range-all-measures", location_ids=csv(location_ids), start_date=date_str(start_date), end_date=date_str(end_date)))

    async def get_historical_monthly_minmax_by_location(self, location_id: int) -> list[MinMaxMonthlyRecord]:
        return TypeAdapter(list[MinMaxMonthlyRecord]).validate_python(await self.get("/historical-monthly/minmax-by-location", location_id=location_id))

    # Climatology
    async def get_climatology_minmax_by_location(self, location_id: int) -> list[MinMaxClimatologyRecord]:
        return TypeAdapter(list[MinMaxClimatologyRecord]).validate_python(await self.get("/climatology/minmax-by-location", location_id=location_id))

    async def get_climatology_by_month_range_location_ids_all_measures(self, location_ids: str | int | Iterable[int], start_month: int, end_month: int) -> list[ClimateHistoricalClimatology]:
        return TypeAdapter(list[ClimateHistoricalClimatology]).validate_python(await self.get("/climatology/by-month-range-location-ids-all-measures", location_ids=csv(location_ids), start_month=start_month, end_month=end_month))

    # Indicators
    async def get_indicator_by_location_id(self, location_id: int) -> list[ClimateHistoricalIndicatorRecord]:
        return TypeAdapter(list[ClimateHistoricalIndicatorRecord]).validate_python(ensure_list(await self.get("/indicator/by-location-id", location_id=location_id)))

    async def get_indicator_by_location_date_period(self, location_id: int, start_date: str | date, end_date: str | date, period: str) -> list[ClimateHistoricalIndicatorRecord]:
        return TypeAdapter(list[ClimateHistoricalIndicatorRecord]).validate_python(ensure_list(await self.get("/indicator/by-location-date-period", location_id=location_id, start_date=date_str(start_date), end_date=date_str(end_date), period=period)))

    async def get_indicator_minmax_by_location(self, location_id: int) -> list[MinMaxIndicatorRecord]:
        return TypeAdapter(list[MinMaxIndicatorRecord]).validate_python(await self.get("/indicator/minmax-by-location", location_id=location_id))

    async def get_indicators_by_category_id(self, category_id: int) -> list[Indicator]:
        return TypeAdapter(list[Indicator]).validate_python(await self.get("/indicator-mng/by-category-id", category_id=category_id))

    async def get_indicators_by_country(self, country_id: int, temporality: str | None = None, category_id: int | None = None, type: str = "CLIMATE") -> list[IndicatorWithFeatures]:
        return TypeAdapter(list[IndicatorWithFeatures]).validate_python(await self.get("/indicator-mng/by-country", country_id=country_id, temporality=temporality, category_id=category_id, type=type))

    async def get_indicator_categories_by_category(self, category_id: int) -> IndicatorCategory:
        return IndicatorCategory.model_validate(await self.get("/indicator-category-mng/by-category", category_id=category_id))

    async def get_indicator_categories_by_country(self, country_id: int) -> list[IndicatorCategory]:
        return TypeAdapter(list[IndicatorCategory]).validate_python(await self.get("/indicator-category-mng/by-country", country_id=country_id))

    async def get_indicator_features_by_indicator_and_country(self, indicator_id: int, country_id: int, type: str | None = None) -> list[IndicatorFeature]:
        return TypeAdapter(list[IndicatorFeature]).validate_python(await self.get("/indicator-features/by-indicator-and-country", indicator_id=indicator_id, country_id=country_id, type=type))

    # Geoserver and periods
    async def get_geoserver_point_data(self, latitude: float, longitude: float, **extra: Any) -> dict[str, Any]:
        return await self.post("/geoserver/point-data", {"latitude": latitude, "longitude": longitude, **extra})

    async def get_available_periods(self, **params: Any) -> Any:
        return await self.get("/periods/available", **params)


_client: AClimateClient | None = None
_client_lock = asyncio.Lock()
_client_started = False


async def get_client(base_url: str = "https://api.aclimate.org", client_id: str | None = None, client_secret: str | None = None, timeout: float = 30.0) -> AClimateClient:
    global _client, _client_started
    if _client is not None and _client_started:
        return _client
    async with _client_lock:
        if _client is not None and _client_started:
            return _client
        client = AClimateClient(client_id=client_id, client_secret=client_secret, base_url=base_url, timeout=timeout)
        await client.__aenter__()
        _client = client
        _client_started = True
        return _client


async def close_client() -> None:
    global _client, _client_started
    if _client is not None and _client_started:
        await _client.__aexit__(None, None, None)
        _client = None
        _client_started = False


def _close_client_at_exit() -> None:
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.run_until_complete(close_client())
    except Exception:
        pass


atexit.register(_close_client_at_exit)
