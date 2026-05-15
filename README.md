# AClimate SDK

## 🏷️ Version and Tags

**Current version:** `v0.1.0`  
**Tags:** `aclimate`, `climate`, `agriculture`, `python`, `sdk`, `api`

---

## 📌 Introduction

AClimate SDK is an asynchronous Python client for consuming endpoints from the AClimate v3 API. It provides typed methods for authentication, countries, administrative regions, locations, historical climate data, climatology, agroclimatic indicators, GeoServer point data, and available periods.

The SDK is designed to be installed directly from GitHub and used by applications, APIs, notebooks, and LLM/RAG workflows that need structured access to AClimate climate and agroclimatic data.

This project is configured to work with [`uv`](https://docs.astral.sh/uv/) for dependency management, virtual environments, locking, testing, and package installation.

---

## ✅ Prerequisites

Before installing the SDK, make sure you have:

- Python `3.10` or higher.
- `uv` installed.
- A valid AClimate API client ID and client secret, or an access token.

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 📦 Installation

Install directly from GitHub with `uv`:

```bash
uv pip install git+https://github.com/CIAT-DAPA/aclimatesdkpy.git
```

Inside another `uv` project, add it as a dependency:

```bash
uv add git+https://github.com/CIAT-DAPA/aclimatesdkpy.git
```

For local development:

```bash
git clone https://github.com/CIAT-DAPA/aclimatesdkpy.git
cd aclimatesdkpy
uv sync --all-extras --dev
```

Run commands inside the managed environment:

```bash
uv run python examples/basic_usage.py

uv run pytest
uv run pytest tests/test_client.py

uv run ruff check .
```

---

## ⚙️ Basic Usage

```python
import asyncio
from aclimate_sdk import AClimateClient

async def main():
    async with AClimateClient(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
    ) as client:
        countries = await client.get_countries()
        for country in countries:
            print(country.id, country.name, country.iso2)

asyncio.run(main())
```

You can also use an existing bearer token:

```python
async with AClimateClient(access_token="YOUR_ACCESS_TOKEN") as client:
    countries = await client.get_countries()
```

---

## 🔐 Authentication Methods

```python
await client.login(username="user@example.com", password="password")
await client.get_client_token()
await client.validate_token()
```

The SDK automatically obtains and refreshes a client-credentials token when `client_id` and `client_secret` are configured.

---

## 🌎 Supported Interfaces

Endpoints are included:

| SDK method | API endpoint |
|---|---|
| `login` | `/auth/login` |
| `validate_token` | `/auth/token/validate` |
| `get_client_token` | `/auth/get-client-token` |
| `get_countries` | `/countries` |
| `get_countries_by_name` | `/countries/by-name` |
| `get_admin1_by_country_ids` | `/admin1/by-country-ids` |
| `get_locations_by_machine_name` | `/locations/by-machine-name` |
| `get_locations_by_id` | `/locations/by-id` |
| `get_locations_by_country_ids_with_data` | `/locations/by-country-ids-with-data` |
| `get_historical_daily_minmax_by_location` | `/historical-daily/minmax-by-location` |
| `get_historical_daily_by_date_range_all_measures` | `/historical-daily/by-date-range-all-measures` |
| `get_historical_monthly_by_date_range_all_measures` | `/historical-monthly/by-date-range-all-measures` |
| `get_historical_monthly_minmax_by_location` | `/historical-monthly/minmax-by-location` |
| `get_climatology_minmax_by_location` | `/climatology/minmax-by-location` |
| `get_climatology_by_month_range_location_ids_all_measures` | `/climatology/by-month-range-location-ids-all-measures` |
| `get_indicator_by_location_id` | `/indicator/by-location-id` |
| `get_indicator_by_location_date_period` | `/indicator/by-location-date-period` |
| `get_indicator_minmax_by_location` | `/indicator/minmax-by-location` |
| `get_indicators_by_category_id` | `/indicator-mng/by-category-id` |
| `get_indicators_by_country` | `/indicator-mng/by-country` |
| `get_indicator_categories_by_category` | `/indicator-category-mng/by-category` |
| `get_indicator_categories_by_country` | `/indicator-category-mng/by-country` |
| `get_indicator_features_by_indicator_and_country` | `/indicator-features/by-indicator-and-country` |
| `get_geoserver_point_data` | `/geoserver/point-data` |
| `get_available_periods` | `/periods/available` |

---

## Parameter conventions

- Endpoints documented with `location_id` accept a single integer.
- Endpoints documented with `location_ids` or `country_ids` accept either a comma-separated string or a Python list such as `[1, 2, 3]`.
- Date parameters accept `YYYY-MM-DD` strings or `datetime.date` objects.

---

## 🧪 Examples

### Search countries by name

```python
countries = await client.get_countries_by_name("Colombia")
```

### Get Admin1 regions for countries

```python
admin1 = await client.get_admin1_by_country_ids([1, 2, 3])
```

### Get locations with latest data

```python
locations = await client.get_locations_by_country_ids_with_data(country_ids=[1], days=7)
```

### Get daily historical climate data

```python
records = await client.get_historical_daily_by_date_range_all_measures(
    location_ids=[101, 102],
    start_date="2025-05-01",
    end_date="2025-05-26",
)
```

### Build multilingual LLM-readable context

The `ContextBuilder` can generate narrative context in English or Spanish. English is the default.

```python
from aclimate_sdk import ContextBuilder

# English output
builder = ContextBuilder(language="en")
text = builder.daily_climate_summary(records)
print(text)

# Spanish output
builder_es = ContextBuilder(language="es")
text_es = builder_es.daily_climate_summary(records)
print(text_es)
```

You can also switch the language in place:

```python
builder.set_language("es")
```

Currently supported languages are:

| Code | Language |
|---|---|
| `en` | English |
| `es` | Spanish |

---

## 🧱 Project Structure

```text
aclimatesdkpy/
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
├── src/
│   └── aclimate_sdk/
│       ├── __init__.py
│       ├── aclimate_api_error.py
│       ├── aclimate_auth_error.py
│       ├── aclimate_client.py
│       ├── aclimate_models.py
│       ├── context_builder.py
│       └── utils.py
├── examples/
│   └── basic_usage.py
└── tests/
    └── test_client.py
```

---

## 🧰 Development with uv

Create or update the virtual environment from the lockfile:

```bash
uv sync --all-extras --dev
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run static typing:

```bash
uv run mypy src
```

Build the package:

```bash
uv build
```

Update the lockfile after dependency changes:

```bash
uv lock
```

---

## 📄 License

MIT License.
