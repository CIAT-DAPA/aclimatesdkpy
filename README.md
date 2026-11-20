# AClimate SDK PY

## 🏷️ Version and Tags

**Current version:** `v0.2.0`  
**Tags:** `aclimate`, `climate`, `agriculture`, `python`, `sdk`, `api`

---

## 📌 Introduction

AClimate SDK PY is an asynchronous Python client for consuming endpoints from the AClimate v3 API. It provides typed methods for authentication, countries, administrative regions, locations, historical climate data, climatology, agroclimatic indicators, GeoServer data (point values, raster export and rasters clipped by a polygon), and available periods.

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
pip install uv
```

---

## 📦 Installation

Inside another `uv` project, add it as a dependency:

```bash
uv add git+https://github.com/CIAT-DAPA/aclimatesdkpy.git
```

Install directly from GitHub with `uv`:

```bash
uv pip install git+https://github.com/CIAT-DAPA/aclimatesdkpy.git
```

## 📦 Uninstall

If you use uv add:

```bash
uv remove aclimatesdkpy
```

If you use uv pip install:

```bash
uv pip uninstall aclimatesdkpy
```

---

## ⚙️ Basic Usage

```python
import asyncio
from aclimatesdkpy.aclimate_client import get_client

api_base_url = "https://api.aclimate.org/"
client_id = ""
client_secret = ""

client = await get_client(
        base_url=api_base_url,
        client_id=client_id,
        client_secret=client_secret,
    )
```

You can also use an existing bearer token:

```python
import asyncio
from aclimatesdkpy import AClimateClient

async with AClimateClient(access_token="YOUR_ACCESS_TOKEN") as client:
    countries = await client.get_countries()
```

---

## 🔐 Authentication Methods

```python
await client.get_client_token()
await client.validate_token()
```

The SDK automatically obtains and refreshes a client-credentials token when `client_id` and `client_secret` are configured.

---

## 🌎 Supported Interfaces

Endpoints are included:

| SDK method | API endpoint |
|---|---|
| `get_client_token` | `/auth/get-client-token` |
| `validate_token` | `/auth/token/validate` |
| `get_countries` | `/countries` |
| `get_countries_by_name` | `/countries/by-name` |
| `get_admin1_by_country_ids` | `/admin1/by-country-ids` |
| `get_admin1_by_name` | `/admin1/by-name` |
| `get_admin2_by_country_ids` | `/admin2/by-country-ids` |
| `get_admin2_by_name` | `/admin2/by-name` |
| `get_locations_by_machine_name` | `/locations/by-machine-name` |
| `get_locations_by_name` | `/locations/by-name` |
| `get_locations_by_search` | `/locations/search` |
| `get_locations_by_id` | `/locations/by-id` |
| `get_locations_by_country_ids_with_data` | `/locations/by-country-ids-with-data` |
| `get_climate_measures_by_country` | `/countries/{country_id}/climate-measures` |
| `get_climate_measures_configuration_by_country` | `/countries/{country_id}/climate-measures/configuration` |
| `get_historical_daily_minmax_by_location` | `/historical-daily/minmax-by-location` |
| `get_historical_daily_by_date_range_all_measures` | `/historical-daily/by-date-range-all-measures` |
| `get_historical_monthly_by_date_range_all_measures` | `/historical-monthly/by-date-range-all-measures` |
| `get_historical_monthly_minmax_by_location` | `/historical-monthly/minmax-by-location` |
| `get_climatology_minmax_by_location` | `/climatology/minmax-by-location` |
| `get_climatology_by_month_range_location_ids_all_measures` | `/climatology/by-month-range-location-ids-all-measures` |
| `get_indicator_by_location_id` | `/indicator/by-location-id` |
| `get_indicator_by_location_date_period` | `/indicator/by-location-date-period` |
| `get_indicator_minmax_by_location` | `/indicator/minmax-by-location` |
| `get_all_indicator_categories` | `/indicator-mng/all-categories` |
| `get_indicators_by_category_id` | `/indicator-mng/by-category-id` |
| `get_indicators_by_country` | `/indicator-mng/by-country` |
| `get_indicator_categories_by_category` | `/indicator-category-mng/by-category` |
| `get_indicator_categories_by_country` | `/indicator-category-mng/by-country` |
| `get_indicator_features_by_indicator_and_country` | `/indicator-features/by-indicator-and-country` |
| `post_geoserver_point_data` | `/geoserver/point-data` |
| `post_geoserver_raster_export` | `/geoserver/raster-export` |
| `post_geoserver_polygon_data` | `/geoserver/polygon-data` |
| `get_geoserver_admin_layers` | `/geoserver/admin-areas/layers` |
| `get_geoserver_admin_area_polygon` | `/geoserver/admin-areas/polygon` |
| `get_available_periods` | `/periods/available` |

---

## Parameter conventions

- Endpoints documented with `location_id` accept a single integer.
- Endpoints documented with `location_ids` or `country_ids` accept either a comma-separated string or a Python list such as `[1, 2, 3]`.
- Date parameters accept `YYYY-MM-DD` strings or `datetime.date` objects.

---

## 🧪 Examples

### Get countries with their climate and indicator configuration

`get_countries` returns every enabled country with two lists: `conf_climate` (climate measures
configured for the country) and `conf_indicator` (indicators configured for the country, including
their category). Only enabled measures and indicators are included.

```python
countries = await client.get_countries()

for country in countries:
    print(country.id, country.name, country.iso2)

    # Climate measures configured for the country
    for measure in country.conf_climate:
        print(measure.short_name, measure.unit, measure.location_climate_conf)
        # Store/workspace to request the rasters of each temporality
        for conf in measure.spatial_climate_conf or []:
            print(conf.temporality, conf.workspace, conf.store)

    # Indicators configured for the country
    for indicator in country.conf_indicator:
        print(indicator.short_name, indicator.type, indicator.temporality, indicator.category_name)
```

> `get_countries_by_name` returns the same `Country` model, but with `conf_climate` and
> `conf_indicator` empty.

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

### Get point values from GeoServer rasters

```python
from aclimatesdkpy.aclimate_models import PointDataRequest

request = PointDataRequest(
    coordinates=[[-86.25, 12.13], [-85.5, 13.1]],  # [lon, lat]
    start_date="2024-01-01",
    end_date="2024-01-03",
    workspace="climate_historical_daily",
    store="climate_historical_daily_ni_prec",
    temporality="daily",
)
response = await client.post_geoserver_point_data(request)
for item in response.data:
    print(item.date, item.coordinate, item.value)
```

### Get rasters clipped by a polygon

`post_geoserver_polygon_data` returns the bytes of a ZIP file with one GeoTIFF per date
(`{date}.tif`), each one clipped to the polygon.

- `polygon` is a GeoJSON object in EPSG:4326: a `Polygon` or `MultiPolygon` geometry, a `Feature`
  or a `FeatureCollection`.
- `temporality` can be `"daily"` (default), `"monthly"` or `"annual"`. `end_date` is optional and
  defaults to `start_date`.
- Every pixel touched by the polygon is included; pixels outside the polygon are set to nodata.
- Dates without raster are skipped. The API answers `404` when no date has data (or the polygon is
  outside the raster) and `400` when the polygon is not valid; both raise `AClimateAPIError`.

```python
import io
import zipfile

from aclimatesdkpy import AClimateAPIError, PolygonDataRequest

request = PolygonDataRequest(
    polygon={
        "type": "Polygon",
        "coordinates": [[
            [-86.6, 12.9], [-86.1, 12.9], [-86.1, 13.4], [-86.6, 13.4], [-86.6, 12.9]
        ]],
    },
    start_date="2024-01-01",
    end_date="2024-01-03",
    workspace="climate_historical_daily",
    store="climate_historical_daily_ni_prec",
    temporality="daily",
)

try:
    zip_bytes = await client.post_geoserver_polygon_data(request)
except AClimateAPIError as error:
    print(error.status_code, error)
else:
    # Save the ZIP file as is...
    with open("polygon_rasters.zip", "wb") as file:
        file.write(zip_bytes)

    # ...or read the GeoTIFF of each date in memory
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        for name in zip_file.namelist():  # e.g. "2024-01-01.tif"
            tiff_bytes = zip_file.read(name)
```

The `workspace` and `store` of each climate measure and temporality are available in
`country.conf_climate[].spatial_climate_conf` (see `get_countries` above).

### Get the polygon of an administrative area

`get_geoserver_admin_layers` lists the layers with administrative areas available in GeoServer.
`level` is the administrative level (`0` = country, `1` = admin 1, `2` = admin 2, ...) and `prefix`
identifies the country or region; both are `None` for layers that do not follow the
`{prefix}_adm{level}` naming convention.

```python
layers = await client.get_geoserver_admin_layers()
for item in layers:
    print(item.layer, item.prefix, item.level)   # e.g. colombia_adm1 colombia 1
```

`get_geoserver_admin_area_polygon` returns a GeoJSON `FeatureCollection` (EPSG:4326) with the
polygons of a layer that match a description.

- The description is searched in every text attribute of the layer (partial match,
  case-insensitive), because each layer has its own attribute names.
- All the polygons that match are returned, with the original attributes of the layer in
  `properties`. Use them to pick the right one when there are several.
- The API answers `404` when the layer does not exist or nothing matches (`AClimateAPIError`).

```python
area = await client.get_geoserver_admin_area_polygon("colombia_adm1", "Valle del Cauca")
for feature in area["features"]:
    print(feature["properties"])
```

The result can be used directly as the `polygon` of `post_geoserver_polygon_data` to get the
rasters clipped by that administrative area:

```python
from aclimatesdkpy import PolygonDataRequest

request = PolygonDataRequest(
    polygon=area,
    start_date="2024-01-01",
    end_date="2024-01-03",
    workspace="climate_historical_daily",
    store="climate_historical_daily_co_prec",
)
zip_bytes = await client.post_geoserver_polygon_data(request)
```

### Export full rasters

```python
from aclimatesdkpy.aclimate_models import RasterExportRequest

request = RasterExportRequest(
    workspace="climate_historical_daily",
    store="climate_historical_daily_ni_prec",
    start_date="2024-01-01",
    end_date="2024-01-03",
)
content = await client.post_geoserver_raster_export(request)  # GeoTIFF or ZIP bytes
```

### Build multilingual LLM-readable context

The `ContextBuilder` can generate narrative context in English or Spanish. English is the default.

```python
from aclimatesdkpy import ContextBuilder

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
│   └── aclimatesdkpy/
│       ├── __init__.py
│       ├── aclimate_api_error.py
│       ├── aclimate_auth_error.py
│       ├── aclimate_client.py
│       ├── aclimate_models.py
│       ├── context_builder.py
│       └── utils.py
└── tests/
    └── test_client.py
```

---

## 🧰 Development with uv

For local development:

```bash
git clone https://github.com/CIAT-DAPA/aclimatesdkpy.git
cd aclimatesdkpy
uv venv
```

Create or update the virtual environment from the lockfile:

```bash
uv sync --all-extras --dev
```

Run commands inside the managed environment:

```bash
uv run python examples/basic_usage.py
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
