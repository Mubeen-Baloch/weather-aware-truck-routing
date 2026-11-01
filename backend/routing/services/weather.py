from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any


MAX_FORECAST_MATCH_SECONDS = 30 * 60


@dataclass(frozen=True)
class WeatherObservation:
    available: bool
    timestamp_utc: datetime | None
    wind_mph: float | None
    rain_inches_per_hour: float | None
    snow_inches_per_hour: float | None


def _to_utc(timestamp: str) -> datetime:
    parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _convert(value: float, unit: str, conversions: dict[str, float]) -> float:
    if unit not in conversions:
        raise ValueError(f'Unsupported weather unit: {unit}')
    converted = float(value) * conversions[unit]
    if not isfinite(converted) or converted < 0:
        raise ValueError('Weather values must be finite and non-negative.')
    return converted


def hourly_observation_at_eta(payload: dict[str, Any], eta_utc: datetime) -> WeatherObservation:
    """Match nearest UTC hourly weather within 30 minutes, requiring all risk metrics."""
    hourly = payload.get('hourly', {})
    units = payload.get('hourly_units', {})
    required = ('time', 'wind_speed_10m', 'rain', 'snowfall')
    if eta_utc.tzinfo is None or payload.get('timezone') != 'UTC' or any(field not in hourly for field in required):
        return WeatherObservation(False, None, None, None, None)

    times = hourly['time']
    try:
        match_index = min(range(len(times)), key=lambda index: abs((_to_utc(times[index]) - eta_utc.astimezone(timezone.utc)).total_seconds()))
        match_time = _to_utc(times[match_index])
        if abs((match_time - eta_utc.astimezone(timezone.utc)).total_seconds()) > MAX_FORECAST_MATCH_SECONDS:
            return WeatherObservation(False, None, None, None, None)
        values = {field: hourly[field][match_index] for field in required[1:]}
        if any(value is None for value in values.values()):
            return WeatherObservation(False, None, None, None, None)
        return WeatherObservation(
            True,
            match_time,
            _convert(values['wind_speed_10m'], units.get('wind_speed_10m', ''), {'mph': 1, 'km/h': 0.621371, 'm/s': 2.23694, 'kn': 1.15078}),
            _convert(values['rain'], units.get('rain', ''), {'inch': 1, 'mm': 0.0393701}),
            _convert(values['snowfall'], units.get('snowfall', ''), {'inch': 1, 'cm': 0.393701, 'mm': 0.0393701}),
        )
    except (IndexError, TypeError, ValueError):
        return WeatherObservation(False, None, None, None, None)
