from __future__ import annotations

from datetime import date
from typing import Iterable, Any


def csv(value: str | int | Iterable[str | int]) -> str:
    """Convert scalar/list values into the comma-separated format expected by AClimate."""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return ",".join(str(v) for v in value)


def date_str(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return value


def ensure_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]
