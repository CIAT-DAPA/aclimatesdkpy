"""
AClimate SDK ContextBuilder.

Transforms raw AClimate API responses into LLM-readable narrative context.
The builder supports multiple output languages through lightweight templates.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from aclimatesdkpy.aclimate_models import (
    ClimateHistoricalIndicatorRecord,
    Country,
    IndicatorFeature,
    Location,
)

SupportedLanguage = Literal["en", "es"]

MONTH_NAMES: dict[str, dict[int, str]] = {
    "es": {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    },
    "en": {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    },
}

TEXT: dict[str, dict[str, str]] = {
    "es": {
        "no_countries": "No se encontraron paises en AClimate.",
        "countries_title": "Paises disponibles en AClimate:",
        "no_locations": "No se encontraron ubicaciones con ese nombre.",
        "locations_found": "Se encontraron {count} ubicacion(es):",
        "municipality": "Municipio",
        "region": "Region",
        "country": "Pais",
        "coordinates": "Coordenadas",
        "altitude": "Altitud",
        "no_current_data": "No se encontraron datos de monitoreo recientes.",
        "current_conditions": "Condiciones actuales ({count} ubicaciones):",
        "no_recent_data": "Sin datos recientes",
        "unknown_date": "fecha desconocida",
        "latest_measurement": "Ultima medicion",
        "no_data": "sin dato",
        "no_daily": "No se encontraron datos historicos diarios para el periodo.",
        "daily_title": "Datos historicos diarios - {location}:",
        "location_fallback": "ubicacion {id}",
        "period": "Periodo",
        "days": "dias",
        "average": "Promedio",
        "minimum": "Minimo",
        "maximum": "Maximo",
        "on": "el",
        "no_monthly": "No se encontraron datos historicos mensuales.",
        "monthly_title": "Datos historicos mensuales - {location}:",
        "monthly_average": "Promedio mensual",
        "lowest_month": "Mes mas bajo",
        "highest_month": "Mes mas alto",
        "no_climatology": "No se encontraron datos de climatologia para esta ubicacion.",
        "climatology_title": "Climatologia historica (normales climaticas) - {location}:",
        "variable": "variable",
        "peak": "Pico",
        "no_extremes": "No se encontraron extremos historicos.",
        "daily_extremes_title": "Extremos historicos (diarios) - {location}:",
        "no_clim_extremes": "No se encontraron extremos de climatologia.",
        "clim_extremes_title": "Extremos climatologicos - {location}:",
        "in_month": "en",
        "indicator_default": "el indicador",
        "indicator": "indicador",
        "no_indicator_records": "No se encontraron registros historicos para {name}.",
        "indicator_title": "Indicador agro-climatico: {name} [{unit}]",
        "location": "Ubicacion",
        "records": "Registros",
        "stat_summary": "Resumen estadistico:",
        "max_value": "Valor maximo",
        "min_value": "Valor minimo",
        "historical_series": "Serie historica:",
        "period_label": "periodo",
        "no_indicator_extremes": "No se encontraron extremos historicos de indicadores.",
        "indicator_extremes_title": "Extremos historicos de indicadores - {location}:",
        "no_recommendations": "No se encontraron recomendaciones para este indicador en este pais.",
        "recommendations": "Recomendaciones agronomicas:",
        "features": "Caracteristicas del indicador:",
        "no_extra_info": "Sin informacion adicional.",
        "no_indicators": "No se encontraron indicadores para este pais.",
        "indicators_catalog": "Indicadores agro-climaticos disponibles ({count}):",
    },
    "en": {
        "no_countries": "No countries were found in AClimate.",
        "countries_title": "Countries available in AClimate:",
        "no_locations": "No locations were found with that name.",
        "locations_found": "Found {count} location(s):",
        "municipality": "Municipality",
        "region": "Region",
        "country": "Country",
        "coordinates": "Coordinates",
        "altitude": "Altitude",
        "no_current_data": "No recent monitoring data was found.",
        "current_conditions": "Current conditions ({count} locations):",
        "no_recent_data": "No recent data",
        "unknown_date": "unknown date",
        "latest_measurement": "Latest measurement",
        "no_data": "no data",
        "no_daily": "No daily historical data was found for the period.",
        "daily_title": "Daily historical data - {location}:",
        "location_fallback": "location {id}",
        "period": "Period",
        "days": "days",
        "average": "Average",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "on": "on",
        "no_monthly": "No monthly historical data was found.",
        "monthly_title": "Monthly historical data - {location}:",
        "monthly_average": "Monthly average",
        "lowest_month": "Lowest month",
        "highest_month": "Highest month",
        "no_climatology": "No climatology data was found for this location.",
        "climatology_title": "Historical climatology (climate normals) - {location}:",
        "variable": "variable",
        "peak": "Peak",
        "no_extremes": "No historical extremes were found.",
        "daily_extremes_title": "Historical extremes (daily) - {location}:",
        "no_clim_extremes": "No climatology extremes were found.",
        "clim_extremes_title": "Climatological extremes - {location}:",
        "in_month": "in",
        "indicator_default": "the indicator",
        "indicator": "indicator",
        "no_indicator_records": "No historical records were found for {name}.",
        "indicator_title": "Agroclimatic indicator: {name} [{unit}]",
        "location": "Location",
        "records": "Records",
        "stat_summary": "Statistical summary:",
        "max_value": "Maximum value",
        "min_value": "Minimum value",
        "historical_series": "Historical series:",
        "period_label": "period",
        "no_indicator_extremes": "No historical indicator extremes were found.",
        "indicator_extremes_title": "Historical indicator extremes - {location}:",
        "no_recommendations": "No recommendations were found for this indicator in this country.",
        "recommendations": "Agronomic recommendations:",
        "features": "Indicator features:",
        "no_extra_info": "No additional information.",
        "no_indicators": "No indicators were found for this country.",
        "indicators_catalog": "Available agroclimatic indicators ({count}):",
    },
}


class ContextBuilder:
    """Convert AClimate API responses into LLM-readable text.

    Parameters
    ----------
    language:
        Output language code. Supported values are ``"en"`` and ``"es"``.
    """

    def __init__(self, language: SupportedLanguage = "en") -> None:
        self.language = self._normalize_language(language)

    @staticmethod
    def _normalize_language(language: str) -> SupportedLanguage:
        normalized = language.lower().split("-")[0]
        if normalized not in TEXT:
            supported = ", ".join(sorted(TEXT))
            raise ValueError(f"Unsupported language '{language}'. Supported languages: {supported}")
        return normalized  # type: ignore[return-value]

    def with_language(self, language: SupportedLanguage) -> "ContextBuilder":
        """Return a new builder with the requested language."""
        return ContextBuilder(language=language)

    def set_language(self, language: SupportedLanguage) -> None:
        """Update the builder output language in place."""
        self.language = self._normalize_language(language)

    @property
    def months(self) -> dict[int, str]:
        return MONTH_NAMES[self.language]

    def t(self, key: str, **kwargs: Any) -> str:
        return TEXT[self.language][key].format(**kwargs)

    def _location_name(self, location_name: str | None, location_id: int) -> str:
        return location_name or self.t("location_fallback", id=location_id)

    # Geo

    def countries_summary(self, countries: list[Country]) -> str:
        if not countries:
            return self.t("no_countries")
        lines = [self.t("countries_title")]
        for c in countries:
            lines.append(f"  - {c.name} (id={c.id}, iso2={c.iso2})")
        return "\n".join(lines)

    def locations_summary(self, locations: list[Location]) -> str:
        if not locations:
            return self.t("no_locations")

        lines = [self.t("locations_found", count=len(locations))]
        for loc in locations:
            parts = [f"  - [{loc.id}] {loc.name}"]
            if loc.admin2_name:
                parts.append(f"    {self.t('municipality')}: {loc.admin2_name}")
            if loc.admin1_name:
                parts.append(f"    {self.t('region')}: {loc.admin1_name}")
            if loc.country_name:
                parts.append(f"    {self.t('country')}: {loc.country_name}")
            if loc.latitude is not None and loc.longitude is not None:
                parts.append(f"    {self.t('coordinates')}: {loc.latitude:.4f}, {loc.longitude:.4f}")
            if loc.altitude is not None:
                parts.append(f"    {self.t('altitude')}: {loc.altitude:.0f} msnm")
            lines.extend(parts)
        return "\n".join(lines)

    def current_conditions_summary(self, locations_data: list[dict[str, Any]]) -> str:
        if not locations_data:
            return self.t("no_current_data")

        lines = [self.t("current_conditions", count=len(locations_data))]
        for item in locations_data:
            name = item.get("name", "?")
            admin1 = item.get("admin1_name", "")
            country = item.get("country_name", "")
            loc_id = item.get("id", "?")
            header = f"\n  {name}"
            if admin1:
                header += f", {admin1}"
            if country:
                header += f" ({country}) - id={loc_id}"
            lines.append(header)

            latest = item.get("latest_data")
            if not latest:
                lines.append(f"    {self.t('no_recent_data')}")
                continue

            d = latest.get("date", self.t("unknown_date"))
            lines.append(f"    {self.t('latest_measurement')}: {d}")

            for measure in latest.get("measures", []):
                value = measure.get("value")
                unit = measure.get("measure_unit", "")
                name = measure.get("measure_name", measure.get("measure_short_name", "?"))
                if value is not None:
                    lines.append(f"    - {name}: {value:.1f} {unit}")
                else:
                    lines.append(f"    - {name}: {self.t('no_data')}")

        return "\n".join(lines)

    # Historical climate

    def daily_climate_summary(self, records: list[ClimateHistoricalDaily]) -> str:
        if not records:
            return self.t("no_daily")

        by_measure: dict[str, list[ClimateHistoricalDaily]] = defaultdict(list)
        for record in records:
            key = f"{record.measure_name or record.measure_short_name} ({record.measure_unit or ''})"
            by_measure[key].append(record)

        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("daily_title", location=location)]

        for measure, grouped_records in by_measure.items():
            sorted_records = sorted(grouped_records, key=lambda x: x.date)
            values = [record.value for record in sorted_records]
            average = sum(values) / len(values)
            min_record = min(sorted_records, key=lambda x: x.value)
            max_record = max(sorted_records, key=lambda x: x.value)
            lines.append(f"\n  {measure.strip()}:")
            lines.append(
                f"    {self.t('period')}: {sorted_records[0].date} -> {sorted_records[-1].date} "
                f"({len(sorted_records)} {self.t('days')})"
            )
            lines.append(f"    {self.t('average')}: {average:.2f}")
            lines.append(f"    {self.t('minimum')}: {min_record.value:.2f} {self.t('on')} {min_record.date}")
            lines.append(f"    {self.t('maximum')}: {max_record.value:.2f} {self.t('on')} {max_record.date}")

        return "\n".join(lines)

    def monthly_climate_summary(self, records: list[ClimateHistoricalMonthly]) -> str:
        if not records:
            return self.t("no_monthly")

        by_measure: dict[str, list[ClimateHistoricalMonthly]] = defaultdict(list)
        for record in records:
            key = f"{record.measure_name or record.measure_short_name} ({record.measure_unit or ''})"
            by_measure[key].append(record)

        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("monthly_title", location=location)]

        for measure, grouped_records in by_measure.items():
            sorted_records = sorted(grouped_records, key=lambda x: x.date)
            values = [record.value for record in sorted_records]
            average = sum(values) / len(values)
            min_record = min(sorted_records, key=lambda x: x.value)
            max_record = max(sorted_records, key=lambda x: x.value)
            lines.append(f"\n  {measure.strip()}:")
            lines.append(f"    {self.t('period')}: {sorted_records[0].date} -> {sorted_records[-1].date}")
            lines.append(f"    {self.t('monthly_average')}: {average:.2f}")
            lines.append(f"    {self.t('lowest_month')}: {min_record.value:.2f} ({min_record.date})")
            lines.append(f"    {self.t('highest_month')}: {max_record.value:.2f} ({max_record.date})")

        return "\n".join(lines)

    def climatology_narrative(self, records: list[ClimateHistoricalClimatology]) -> str:
        if not records:
            return self.t("no_climatology")

        by_measure: dict[str, list[ClimateHistoricalClimatology]] = defaultdict(list)
        for record in records:
            key = record.measure_name or record.measure_short_name or self.t("variable")
            by_measure[key].append(record)

        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("climatology_title", location=location)]

        for measure, grouped_records in by_measure.items():
            sorted_records = sorted(grouped_records, key=lambda x: x.month)
            unit = sorted_records[0].measure_unit or ""
            peak = max(sorted_records, key=lambda x: x.value)
            trough = min(sorted_records, key=lambda x: x.value)

            lines.append(f"\n  {measure} [{unit}]:")
            for record in sorted_records:
                bar = "#" * int(record.value / (peak.value or 1) * 20)
                month_name = self.months.get(record.month, str(record.month))
                lines.append(f"    {month_name:>10}: {record.value:>8.1f}  {bar}")
            lines.append(f"    -> {self.t('peak')}: {self.months.get(peak.month, str(peak.month))} ({peak.value:.1f} {unit})")
            lines.append(
                f"    -> {self.t('minimum')}: {self.months.get(trough.month, str(trough.month))} "
                f"({trough.value:.1f} {unit})"
            )

        return "\n".join(lines)

    def minmax_daily_summary(self, records: list[MinMaxDailyRecord]) -> str:
        if not records:
            return self.t("no_extremes")
        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("daily_extremes_title", location=location)]
        for record in records:
            name = record.measure_name or str(record.measure_id)
            lines.append(
                f"  - {name}: min={record.min_value:.2f} ({record.min_date or '?'})"
                f" | max={record.max_value:.2f} ({record.max_date or '?'})"
            )
        return "\n".join(lines)

    def minmax_climatology_summary(self, records: list[MinMaxClimatologyRecord]) -> str:
        if not records:
            return self.t("no_clim_extremes")
        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("clim_extremes_title", location=location)]
        for record in records:
            name = record.measure_name or str(record.measure_id)
            min_month = self.months.get(record.min_month or 0, str(record.min_month))
            max_month = self.months.get(record.max_month or 0, str(record.max_month))
            lines.append(
                f"  - {name}: min={record.min_value:.2f} {self.t('in_month')} {min_month}"
                f" | max={record.max_value:.2f} {self.t('in_month')} {max_month}"
            )
        return "\n".join(lines)

    # Indicators

    def indicator_narrative(
        self,
        records: list[ClimateHistoricalIndicatorRecord],
        indicator_name: str | None = None,
    ) -> str:
        if not records:
            name = indicator_name or self.t("indicator_default")
            return self.t("no_indicator_records", name=name)

        location = self._location_name(records[0].location_name, records[0].location_id)
        indicator_name_value = records[0].indicator_name or indicator_name or self.t("indicator")
        unit = records[0].indicator_unit or ""
        period = records[0].period or self.t("period_label")

        values = [record.value for record in records]
        average = sum(values) / len(values)
        max_record = max(records, key=lambda x: x.value)
        min_record = min(records, key=lambda x: x.value)

        lines = [
            self.t("indicator_title", name=indicator_name_value, unit=unit),
            f"{self.t('location')}: {location}",
            f"{self.t('records')}: {len(records)} ({period})",
            "",
            self.t("stat_summary"),
            f"  {self.t('average')}: {average:.2f} {unit}",
            f"  {self.t('max_value')}: {max_record.value:.2f} {unit}"
            + (f" ({self.t('period_label')}: {max_record.start_date})" if max_record.start_date else ""),
            f"  {self.t('min_value')}: {min_record.value:.2f} {unit}"
            + (f" ({self.t('period_label')}: {min_record.start_date})" if min_record.start_date else ""),
        ]

        if len(records) <= 24:
            lines.append(f"\n{self.t('historical_series')}")
            for record in sorted(records, key=lambda x: x.start_date or ""):
                date_value = record.start_date[:10] if record.start_date else "?"
                lines.append(f"  {date_value}: {record.value:.2f} {unit}")

        return "\n".join(lines)

    def indicator_extremes_narrative(self, records: list[MinMaxIndicatorRecord]) -> str:
        if not records:
            return self.t("no_indicator_extremes")
        location = self._location_name(records[0].location_name, records[0].location_id)
        lines = [self.t("indicator_extremes_title", location=location)]
        for record in records:
            name = record.indicator_name or str(record.indicator_id)
            lines.append(
                f"  - {name}: min={record.min_value:.2f} ({record.min_date or '?'})"
                f" | max={record.max_value:.2f} ({record.max_date or '?'})"
            )
        return "\n".join(lines)

    def recommendations_narrative(self, features: list[IndicatorFeature]) -> str:
        if not features:
            return self.t("no_recommendations")

        recommendations = [feature for feature in features if feature.type == "recommendation"]
        indicator_features = [feature for feature in features if feature.type == "feature"]

        lines = []
        if recommendations:
            lines.append(self.t("recommendations"))
            for feature in recommendations:
                lines.append(f"  - {feature.title}")
                if feature.description:
                    lines.append(f"    {feature.description}")

        if indicator_features:
            lines.append(f"\n{self.t('features')}")
            for feature in indicator_features:
                lines.append(f"  - {feature.title}")
                if feature.description:
                    lines.append(f"    {feature.description}")

        return "\n".join(lines) if lines else self.t("no_extra_info")

    def indicators_catalog_summary(self, indicators: list[dict[str, Any]]) -> str:
        if not indicators:
            return self.t("no_indicators")
        lines = [self.t("indicators_catalog", count=len(indicators))]
        for indicator in indicators:
            name = indicator.get("name", "?")
            short = indicator.get("short_name", "?")
            unit = indicator.get("unit", "?")
            temporality = indicator.get("temporality", "?")
            indicator_type = indicator.get("type", "?")
            lines.append(f"  - [{short}] {name} - {unit} ({temporality}, {indicator_type})")
        return "\n".join(lines)
