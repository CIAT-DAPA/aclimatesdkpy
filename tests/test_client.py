from  aclimatesdkpy.utils import csv, date_str


def test_csv_from_iterable() -> None:
    assert csv([1, 2, 3]) == "1,2,3"


def test_csv_from_scalar() -> None:
    assert csv(1) == "1"
    assert csv("1,2") == "1,2"


def test_date_str_from_none() -> None:
    assert date_str(None) is None

from datetime import date
import pytest
from aclimatesdkpy.aclimate_models import ClimateHistoricalDaily, Country
from aclimatesdkpy.context_builder import ContextBuilder


def test_context_builder_default_language_is_english() -> None:
    builder = ContextBuilder()
    result = builder.countries_summary([Country(id=1, name="Colombia", iso2="CO")])
    assert result.startswith("Countries available in AClimate")


def test_context_builder_spanish_language() -> None:
    builder = ContextBuilder(language="es")
    result = builder.countries_summary([Country(id=1, name="Colombia", iso2="CO")])
    assert result.startswith("Paises disponibles en AClimate")


def test_context_builder_rejects_unsupported_language() -> None:
    with pytest.raises(ValueError):
        ContextBuilder(language="fr")  # type: ignore[arg-type]


def test_daily_summary_uses_selected_language() -> None:
    records = [
        ClimateHistoricalDaily(
            id=1,
            location_id=10,
            location_name="Palmira",
            measure_id=1,
            measure_name="precipitation",
            measure_short_name="prec",
            measure_unit="mm",
            date=date(2025, 5, 1),
            value=10.0,
        ),
        ClimateHistoricalDaily(
            id=2,
            location_id=10,
            location_name="Palmira",
            measure_id=1,
            measure_name="precipitation",
            measure_short_name="prec",
            measure_unit="mm",
            date=date(2025, 5, 2),
            value=30.0,
        ),
    ]
    assert "Daily historical data" in ContextBuilder("en").daily_climate_summary(records)
    assert "Datos historicos diarios" in ContextBuilder("es").daily_climate_summary(records)
