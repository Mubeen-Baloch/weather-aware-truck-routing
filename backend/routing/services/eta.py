from dataclasses import dataclass
from math import isclose, isfinite
from typing import Any


DISTANCE_TOLERANCE_METERS = 0.01
ROUTE_DISTANCE_COVERAGE_TOLERANCE_METERS = 0.05
ROUTE_DISTANCE_COVERAGE_RELATIVE_TOLERANCE = 3e-7

@dataclass(frozen=True)
class DurationSegment:
    distance_meters: float
    duration_seconds: float


def route_duration_segments(route: dict[str, Any]) -> list[DurationSegment]:
    """Use annotation durations per leg, falling back to that leg's steps."""
    duration_segments: list[DurationSegment] = []
    legs = route.get('legs', [])
    if not legs:
        raise ValueError('Route does not contain legs with duration data.')

    for leg_index, leg in enumerate(legs):
        annotation = leg.get('annotation', {})
        distances = annotation.get('distance', [])
        durations = annotation.get('duration', [])
        if len(distances) == len(durations) and distances:
            duration_segments.extend(
                DurationSegment(float(distance), float(duration))
                for distance, duration in zip(distances, durations)
            )
            continue

        steps = [
            DurationSegment(float(step['distance']), float(step['duration']))
            for step in leg.get('steps', [])
            if 'distance' in step and 'duration' in step
        ]
        if not steps:
            raise ValueError(f'Route leg {leg_index} does not contain annotation or step duration data.')
        duration_segments.extend(steps)
    return duration_segments


def eta_seconds_at_distance(distance_meters: float, duration_segments: list[DurationSegment]) -> float:
    """Interpolate ETA within the Mapbox segment containing the travelled distance."""
    if not isfinite(distance_meters) or distance_meters < 0:
        raise ValueError('Distance must be a finite non-negative value.')
    if not duration_segments:
        raise ValueError('Route does not contain duration segments.')
    cumulative_distance = 0.0
    cumulative_duration = 0.0
    for segment in duration_segments:
        if (
            not isfinite(segment.distance_meters)
            or not isfinite(segment.duration_seconds)
            or segment.distance_meters < 0
            or segment.duration_seconds < 0
        ):
            raise ValueError('Route segment values must be finite and non-negative.')
        if distance_meters <= cumulative_distance + segment.distance_meters + DISTANCE_TOLERANCE_METERS:
            if segment.distance_meters == 0:
                return cumulative_duration
            fraction = min(1.0, max(0.0, (distance_meters - cumulative_distance) / segment.distance_meters))
            return cumulative_duration + (segment.duration_seconds * fraction)
        cumulative_distance += segment.distance_meters
        cumulative_duration += segment.duration_seconds
    raise ValueError('Distance exceeds available route duration segments.')


def duration_distance_at_geometry_distance(
    geometry_distance_meters: float,
    geometry_total_meters: float,
    route_distance_meters: float,
    duration_segments: list[DurationSegment],
) -> float:
    """Map a geometry checkpoint into Mapbox's route-distance duration domain.

    Geometry length is not assumed to equal Mapbox road distance. The duration
    annotations must, however, cover the Mapbox route distance before a
    progress-based mapping is allowed.
    """
    values = (geometry_distance_meters, geometry_total_meters, route_distance_meters)
    if (
        any(not isfinite(value) or value < 0 for value in values)
        or geometry_total_meters <= 0
        or route_distance_meters <= 0
    ):
        raise ValueError('Geometry and route distances must be finite positive values.')
    if geometry_distance_meters > geometry_total_meters + DISTANCE_TOLERANCE_METERS:
        raise ValueError('Checkpoint distance exceeds route geometry distance.')
    if not duration_segments:
        raise ValueError('Route does not contain duration segments.')

    duration_total_meters = 0.0
    for segment in duration_segments:
        if not isfinite(segment.distance_meters) or segment.distance_meters < 0:
            raise ValueError('Route segment distances must be finite and non-negative.')
        duration_total_meters += segment.distance_meters
    if not isclose(
        duration_total_meters,
        route_distance_meters,
        rel_tol=ROUTE_DISTANCE_COVERAGE_RELATIVE_TOLERANCE,
        abs_tol=ROUTE_DISTANCE_COVERAGE_TOLERANCE_METERS,
    ):
        raise ValueError('Duration segments do not cover the reported route distance.')

    progress = min(1.0, max(0.0, geometry_distance_meters / geometry_total_meters))
    return progress * duration_total_meters
