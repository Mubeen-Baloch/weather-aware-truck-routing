from dataclasses import dataclass
from enum import IntEnum
from math import isfinite
from typing import Iterable

from .weather import WeatherObservation


class RiskLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4
    NO_TRAVEL = 5


@dataclass(frozen=True)
class CheckpointRisk:
    level: RiskLevel | None
    available: bool


@dataclass(frozen=True)
class RouteSummary:
    route_index: int
    low_miles: float
    moderate_miles: float
    high_miles: float
    severe_miles: float
    no_travel_miles: float
    unavailable_miles: float
    average_risk: float | None
    duration_seconds: float

    @property
    def eligible(self) -> bool:
        return self.no_travel_miles == 0 and self.unavailable_miles == 0


def _classify(value: float, thresholds: tuple[float, float, float, float]) -> RiskLevel:
    if value < thresholds[0]:
        return RiskLevel.LOW
    if value <= thresholds[1]:
        return RiskLevel.MODERATE
    if value <= thresholds[2]:
        return RiskLevel.HIGH
    if value <= thresholds[3]:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_weather_risk(weather: WeatherObservation, load_weight_lbs: float) -> CheckpointRisk:
    if not isinstance(load_weight_lbs, (int, float)) or isinstance(load_weight_lbs, bool) or not isfinite(load_weight_lbs) or load_weight_lbs < 0:
        raise ValueError('Load weight must be a finite non-negative value.')
    if not weather.available or None in (
        weather.wind_mph,
        weather.rain_inches_per_hour,
        weather.snow_inches_per_hour,
    ):
        return CheckpointRisk(None, False)
    values = (weather.wind_mph, weather.rain_inches_per_hour, weather.snow_inches_per_hour)
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value < 0 for value in values):
        return CheckpointRisk(None, False)
    wind = _classify(weather.wind_mph, (25, 34, 44, 54))
    rain = _classify(weather.rain_inches_per_hour, (0.10, 0.25, 0.50, 1.00))
    snow = _classify(weather.snow_inches_per_hour, (0.5, 1.0, 2.0, 3.0))
    level = max(wind, rain, snow)
    if weather.wind_mph >= 55 or (45 <= weather.wind_mph <= 54 and load_weight_lbs > 30_000):
        level = RiskLevel.NO_TRAVEL
    elif 35 <= weather.wind_mph <= 44 and load_weight_lbs > 40_000:
        level = max(level, RiskLevel.SEVERE)
    return CheckpointRisk(level, True)


def summarize_route(
    route_index: int,
    checkpoint_risks: Iterable[tuple[CheckpointRisk, float]],
    duration_seconds: float,
) -> RouteSummary:
    mile_totals = {level: 0.0 for level in RiskLevel}
    unavailable_miles = 0.0
    weighted_risk = 0.0
    classified_miles = 0.0
    for checkpoint_risk, meters in checkpoint_risks:
        miles = meters / 1609.344
        if not checkpoint_risk.available or checkpoint_risk.level is None:
            unavailable_miles += miles
            continue
        mile_totals[checkpoint_risk.level] += miles
        weighted_risk += miles * checkpoint_risk.level.value
        classified_miles += miles
    return RouteSummary(
        route_index,
        mile_totals[RiskLevel.LOW],
        mile_totals[RiskLevel.MODERATE],
        mile_totals[RiskLevel.HIGH],
        mile_totals[RiskLevel.SEVERE],
        mile_totals[RiskLevel.NO_TRAVEL],
        unavailable_miles,
        weighted_risk / classified_miles if classified_miles else None,
        duration_seconds,
    )


def recommend_route(routes: Iterable[RouteSummary]) -> RouteSummary | None:
    eligible = [route for route in routes if route.eligible]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda route: (
            route.severe_miles,
            route.high_miles,
            route.average_risk,
            route.duration_seconds,
            route.route_index,
        ),
    )
